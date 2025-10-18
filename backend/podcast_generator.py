"""
播客生成核心逻辑
协调并行任务、流式脚本生成与语音合成同步
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Iterator
from queue import Queue
from config import (
    BGM_FILES,
    WELCOME_TEXT,
    WELCOME_VOICE_ID,
    PODCAST_CONFIG,
    OUTPUT_DIR
)
from minimax_client import minimax_client
from content_parser import content_parser
from voice_manager import voice_manager
from audio_utils import create_podcast_with_bgm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PodcastGenerator:
    """播客生成器"""

    def __init__(self):
        self.bgm01_path = BGM_FILES["bgm01"]
        self.bgm02_path = BGM_FILES["bgm02"]
        self.welcome_text = WELCOME_TEXT
        self.welcome_voice_id = WELCOME_VOICE_ID

    def _parse_speaker_line(self, line: str) -> tuple:
        """
        解析脚本行，提取 Speaker 和文本

        Args:
            line: 脚本行，格式如 "Speaker1: 文本内容"

        Returns:
            (speaker, text) 元组
        """
        if ":" in line:
            parts = line.split(":", 1)
            speaker = parts[0].strip()
            text = parts[1].strip()
            return speaker, text
        return None, line.strip()

    def _is_complete_sentence(self, buffer: str) -> bool:
        """
        判断是否为完整句子

        Args:
            buffer: 累积的文本缓冲

        Returns:
            是否完整句子
        """
        # 检查是否以换行符或句子结束标点符号结尾
        if buffer.endswith('\n') or buffer.endswith('。') or buffer.endswith('！') or buffer.endswith('？'):
            return True
        # 检查是否包含 Speaker 切换
        if '\nSpeaker' in buffer:
            return True
        return False

    def generate_podcast_stream(self,
                                content: str,
                                speaker1_voice_id: str,
                                speaker2_voice_id: str,
                                session_id: str) -> Iterator[Dict[str, Any]]:
        """
        流式生成播客

        Args:
            content: 解析后的内容
            speaker1_voice_id: Speaker1 音色 ID
            speaker2_voice_id: Speaker2 音色 ID
            session_id: 会话 ID

        Yields:
            包含各种事件的字典
        """
        # 语音 ID 映射
        voice_mapping = {
            "Speaker1": speaker1_voice_id,
            "Speaker2": speaker2_voice_id
        }

        # 存储所有音频 chunk
        all_audio_chunks = []
        all_script_lines = []
        trace_ids = {}

        # Step 1: 生成并播放欢迎音频
        yield {
            "type": "progress",
            "step": "welcome_audio",
            "message": "正在播放欢迎音频..."
        }

        # 播放 BGM01
        yield {
            "type": "bgm",
            "bgm_type": "bgm01",
            "path": self.bgm01_path
        }

        # 合成欢迎语
        welcome_audio_chunks = []
        for tts_event in minimax_client.synthesize_speech_stream(self.welcome_text, self.welcome_voice_id):
            if tts_event["type"] == "audio_chunk":
                welcome_audio_chunks.append(tts_event["audio"])
                yield {
                    "type": "welcome_audio_chunk",
                    "audio": tts_event["audio"]
                }
            elif tts_event["type"] == "tts_complete":
                trace_ids["welcome_tts"] = tts_event.get("trace_id")
                yield {
                    "type": "trace_id",
                    "api": "欢迎语合成",
                    "trace_id": tts_event.get("trace_id")
                }

        # 播放 BGM02（淡出）
        yield {
            "type": "bgm",
            "bgm_type": "bgm02_fadeout",
            "path": self.bgm02_path
        }

        # Step 2: 流式生成脚本和语音
        yield {
            "type": "progress",
            "step": "script_generation",
            "message": "正在生成播客脚本..."
        }

        script_buffer = ""
        current_speaker = None
        current_text = ""
        sentence_queue = Queue()  # 待合成的句子队列

        # 脚本生成线程
        def script_generation_thread():
            nonlocal script_buffer
            for script_event in minimax_client.generate_script_stream(
                content,
                PODCAST_CONFIG["target_duration_min"],
                PODCAST_CONFIG["target_duration_max"]
            ):
                if script_event["type"] == "script_chunk":
                    chunk = script_event["content"]
                    script_buffer += chunk

                    # 检查是否形成完整句子
                    while self._is_complete_sentence(script_buffer):
                        # 提取完整句子
                        if '\n' in script_buffer:
                            line, script_buffer = script_buffer.split('\n', 1)
                        else:
                            line = script_buffer
                            script_buffer = ""

                        if line.strip():
                            speaker, text = self._parse_speaker_line(line)
                            if speaker and text:
                                sentence_queue.put(("sentence", speaker, text))

                elif script_event["type"] == "script_complete":
                    # 处理剩余buffer
                    if script_buffer.strip():
                        speaker, text = self._parse_speaker_line(script_buffer)
                        if speaker and text:
                            sentence_queue.put(("sentence", speaker, text))

                    trace_ids["script_generation"] = script_event.get("trace_id")
                    sentence_queue.put(("complete", None, None))

        # 启动脚本生成线程
        script_thread = threading.Thread(target=script_generation_thread)
        script_thread.start()

        # 主线程：消费句子队列，进行语音合成
        tts_sentence_count = 0
        while True:
            item = sentence_queue.get()
            if item[0] == "complete":
                break

            _, speaker, text = item
            tts_sentence_count += 1

            # 发送脚本内容到前端
            full_line = f"{speaker}: {text}"
            all_script_lines.append(full_line)
            yield {
                "type": "script_chunk",
                "speaker": speaker,
                "text": text,
                "full_line": full_line
            }

            # 获取对应音色
            voice_id = voice_mapping.get(speaker, speaker1_voice_id)

            # 流式语音合成
            sentence_audio_chunks = []
            for tts_event in minimax_client.synthesize_speech_stream(text, voice_id):
                if tts_event["type"] == "audio_chunk":
                    audio_chunk = tts_event["audio"]
                    sentence_audio_chunks.append(audio_chunk)
                    all_audio_chunks.append(audio_chunk)

                    # 实时推送音频 chunk 到前端
                    yield {
                        "type": "audio_chunk",
                        "speaker": speaker,
                        "audio": audio_chunk
                    }

                elif tts_event["type"] == "tts_complete":
                    trace_id = tts_event.get("trace_id")
                    trace_ids[f"tts_sentence_{tts_sentence_count}"] = trace_id
                    yield {
                        "type": "trace_id",
                        "api": f"{speaker} 第 {tts_sentence_count} 句合成",
                        "trace_id": trace_id
                    }

        # 等待脚本生成线程完成
        script_thread.join()

        yield {
            "type": "progress",
            "step": "script_complete",
            "message": "脚本生成完成"
        }

        yield {
            "type": "trace_id",
            "api": "脚本生成",
            "trace_id": trace_ids.get("script_generation")
        }

        # Step 3: 生成封面
        yield {
            "type": "progress",
            "step": "cover_generation",
            "message": "正在生成播客封面..."
        }

        # 提取内容摘要（取前500字符）
        content_summary = content[:500] if len(content) > 500 else content

        cover_result = minimax_client.generate_cover_image(content_summary)

        if cover_result["success"]:
            yield {
                "type": "cover_image",
                "image_url": cover_result["image_url"],
                "prompt": cover_result["prompt"]
            }
            trace_ids["cover_prompt_generation"] = cover_result.get("text_trace_id")
            trace_ids["cover_image_generation"] = cover_result.get("image_trace_id")
            yield {
                "type": "trace_id",
                "api": "封面 Prompt 生成",
                "trace_id": cover_result.get("text_trace_id")
            }
            yield {
                "type": "trace_id",
                "api": "封面图生成",
                "trace_id": cover_result.get("image_trace_id")
            }
        else:
            yield {
                "type": "error",
                "message": f"封面生成失败: {cover_result.get('message')}"
            }

        # Step 4: 添加结尾 BGM
        yield {
            "type": "bgm",
            "bgm_type": "bgm01",
            "path": self.bgm01_path
        }

        yield {
            "type": "bgm",
            "bgm_type": "bgm02_fadeout",
            "path": self.bgm02_path
        }

        # Step 5: 合并完整播客音频
        yield {
            "type": "progress",
            "step": "audio_merging",
            "message": "正在合并完整播客音频..."
        }

        output_filename = f"podcast_{session_id}_{int(time.time())}.mp3"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        try:
            # 合并音频（BGM + 欢迎语 + 对话内容 + BGM）
            welcome_audio_hex = ''.join(welcome_audio_chunks)
            create_podcast_with_bgm(
                bgm01_path=self.bgm01_path,
                bgm02_path=self.bgm02_path,
                welcome_audio_hex=welcome_audio_hex,
                dialogue_audio_chunks=all_audio_chunks,
                output_path=output_path
            )

            # 保存脚本
            script_filename = f"script_{session_id}_{int(time.time())}.txt"
            script_path = os.path.join(OUTPUT_DIR, script_filename)
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(all_script_lines))

            yield {
                "type": "complete",
                "audio_path": output_path,
                "audio_url": f"/download/audio/{output_filename}",
                "script_path": script_path,
                "script_url": f"/download/script/{script_filename}",
                "cover_url": cover_result.get("image_url", ""),
                "trace_ids": trace_ids,
                "message": "播客生成完成！"
            }

        except Exception as e:
            logger.error(f"音频合并失败: {str(e)}")
            yield {
                "type": "error",
                "message": f"音频合并失败: {str(e)}"
            }


# 单例实例
podcast_generator = PodcastGenerator()
