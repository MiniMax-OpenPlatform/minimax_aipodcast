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
                                session_id: str,
                                api_key: str) -> Iterator[Dict[str, Any]]:
        """
        流式生成播客

        Args:
            content: 解析后的内容
            speaker1_voice_id: Speaker1 音色 ID
            speaker2_voice_id: Speaker2 音色 ID
            session_id: 会话 ID
            api_key: 用户提供的 MiniMax API Key

        Yields:
            包含各种事件的字典
        """
        # 语音 ID 映射（支持多种格式：Speaker1/Speaker2 和 Mini/Max）
        voice_mapping = {
            "Speaker1": speaker1_voice_id,
            "Speaker2": speaker2_voice_id,
            # LLM 有时会直接使用主持人名称而非 Speaker1/Speaker2
            "Mini": speaker1_voice_id,
            "Max": speaker2_voice_id,
            "mini": speaker1_voice_id,
            "max": speaker2_voice_id,
        }

        # 存储所有音频 chunk
        all_audio_chunks = []
        all_script_lines = []
        trace_ids = {}

        # 渐进式音频文件路径和内存中的 AudioSegment 对象
        progressive_filename = f"progressive_{session_id}.mp3"
        progressive_path = os.path.join(OUTPUT_DIR, progressive_filename)
        progressive_audio_in_memory = None  # 在内存中累积,避免多次 MP3 编码/解码

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
        for tts_event in minimax_client.synthesize_speech_stream(self.welcome_text, self.welcome_voice_id, api_key=api_key):
            if tts_event["type"] == "audio_chunk":
                welcome_audio_chunks.append(tts_event["audio"])
                # 不发送 audio chunk 到前端（数据太大，前端不需要）
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

        # 合并 BGM1 + 欢迎语 + BGM2 作为开场音频
        logger.info("开始生成开场音频（BGM1 + 欢迎语 + BGM2）")
        logger.info(f"欢迎语音频 chunks 数量: {len(welcome_audio_chunks)}")
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize

            logger.info(f"加载 BGM01: {self.bgm01_path}")
            bgm01 = AudioSegment.from_file(self.bgm01_path)
            logger.info(f"BGM01 时长: {len(bgm01)}ms")

            logger.info(f"加载 BGM02: {self.bgm02_path}")
            bgm02 = AudioSegment.from_file(self.bgm02_path).fade_out(1000)
            logger.info(f"BGM02 时长: {len(bgm02)}ms")

            # 转换欢迎语音频
            from audio_utils import hex_to_audio_segment
            welcome_audio = AudioSegment.empty()
            for i, chunk_hex in enumerate(welcome_audio_chunks):
                logger.info(f"处理欢迎语 chunk {i + 1}/{len(welcome_audio_chunks)}")
                chunk = hex_to_audio_segment(chunk_hex)
                if chunk:
                    welcome_audio += chunk
                    logger.info(f"欢迎语累计时长: {len(welcome_audio)}ms")

            logger.info(f"欢迎语总时长: {len(welcome_audio)}ms")

            # 对欢迎语音频进行 normalize 并调整到 -18 dB
            if len(welcome_audio) > 0:
                welcome_audio = normalize(welcome_audio)
                logger.info(f"欢迎语音频已标准化，音量: {welcome_audio.dBFS:.2f} dBFS")
                target_dBFS = -18.0
                change_in_dBFS = target_dBFS - welcome_audio.dBFS
                welcome_audio = welcome_audio.apply_gain(change_in_dBFS)
                logger.info(f"欢迎语音量已调整到 -18 dB，实际: {welcome_audio.dBFS:.2f} dBFS")

            # 对 BGM 也调整到 -18 dB
            bgm01_adjusted = bgm01.apply_gain(-18.0 - bgm01.dBFS)
            bgm02_adjusted = bgm02.apply_gain(-18.0 - bgm02.dBFS)

            # 合并：BGM1 + 欢迎语 + BGM2（所有部分都已经是 -18 dB）
            intro_audio = bgm01_adjusted + welcome_audio + bgm02_adjusted
            logger.info(f"开场音频总时长: {len(intro_audio)}ms，音量: {intro_audio.dBFS:.2f} dBFS")

            # 保存到内存
            progressive_audio_in_memory = intro_audio

            # 导出到文件（仅用于前端播放）
            logger.info(f"开始导出开场音频到渐进式文件: {progressive_path}")
            progressive_audio_in_memory.export(progressive_path, format="mp3")
            logger.info(f"开场音频已保存到: {progressive_path}")

            # 发送渐进式音频 URL
            yield {
                "type": "progressive_audio",
                "audio_url": f"/download/audio/{progressive_filename}?t={int(time.time())}",
                "duration_ms": len(intro_audio),
                "message": "开场音频已生成（BGM1 + 欢迎语 + BGM2）"
            }
            logger.info("开场音频 URL 已发送到前端")
        except Exception as e:
            logger.error(f"生成开场音频失败: {str(e)}")
            logger.exception("详细错误:")

        # Step 2: 并发开始脚本生成和封面生成
        yield {
            "type": "progress",
            "step": "script_generation",
            "message": "正在生成播客脚本和封面..."
        }

        script_buffer = ""
        current_speaker = None
        current_text = ""
        sentence_queue = Queue()  # 待合成的句子队列
        cover_result = {"success": False}  # 封面生成结果

        # 封面生成线程（并发）
        def cover_generation_thread():
            nonlocal cover_result
            try:
                logger.info("🎨 [封面线程] 开始执行封面生成任务（并发）")
                # 提取内容摘要（取前500字符）
                content_summary = content[:500] if len(content) > 500 else content

                cover_result = minimax_client.generate_cover_image(content_summary, api_key=api_key)

                # 发送 Trace IDs
                if cover_result.get("text_trace_id"):
                    trace_ids["cover_prompt_generation"] = cover_result.get("text_trace_id")

                if cover_result.get("image_trace_id"):
                    trace_ids["cover_image_generation"] = cover_result.get("image_trace_id")

                logger.info(f"🎨 [封面线程] 封面生成完成，成功={cover_result['success']}")
            except Exception as e:
                logger.error(f"🎨 [封面线程] 封面生成线程异常: {str(e)}")
                logger.exception("详细错误:")

        # 脚本生成线程
        def script_generation_thread():
            nonlocal script_buffer
            try:
                logger.info("📝 [脚本线程] 开始执行脚本生成任务")
                for script_event in minimax_client.generate_script_stream(
                    content,
                    PODCAST_CONFIG["target_duration_min"],
                    PODCAST_CONFIG["target_duration_max"],
                    api_key=api_key
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
                                    logger.info(f"入队句子: {speaker}: {text[:30]}...")

                    elif script_event["type"] == "script_complete":
                        # 处理剩余buffer
                        if script_buffer.strip():
                            speaker, text = self._parse_speaker_line(script_buffer)
                            if speaker and text:
                                sentence_queue.put(("sentence", speaker, text))

                        trace_ids["script_generation"] = script_event.get("trace_id")
                        logger.info("脚本生成完成，发送完成信号")
                        sentence_queue.put(("complete", None, None))

                    elif script_event["type"] == "error":
                        logger.error(f"脚本生成错误: {script_event.get('message')}")
                        # 发送错误后仍需要发送完成信号
                        sentence_queue.put(("complete", None, None))

            except Exception as e:
                logger.error(f"脚本生成线程异常: {str(e)}")
                logger.exception("详细错误:")
                # 确保发送完成信号，避免主线程永久阻塞
                sentence_queue.put(("complete", None, None))

        # 启动脚本生成线程和封面生成线程（并发）
        script_thread = threading.Thread(target=script_generation_thread)
        cover_thread = threading.Thread(target=cover_generation_thread)

        logger.info("🚀 准备启动两个并发线程：脚本生成 + 封面生成")
        script_thread.start()
        logger.info("📝 [主线程] 脚本生成线程已启动")
        cover_thread.start()
        logger.info("🎨 [主线程] 封面生成线程已启动")

        # 主线程：消费句子队列，进行语音合成
        tts_sentence_count = 0  # 总句子数
        update_counter = 0  # 累积计数器（用于判断是否需要发送更新）
        import math

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
            for tts_event in minimax_client.synthesize_speech_stream(text, voice_id, api_key=api_key):
                if tts_event["type"] == "audio_chunk":
                    audio_chunk = tts_event["audio"]
                    sentence_audio_chunks.append(audio_chunk)
                    all_audio_chunks.append(audio_chunk)

                    # 不发送 audio_chunk 到前端（数据太大，前端也不需要）
                    # 前端只需要 complete 事件中的最终音频 URL

                elif tts_event["type"] == "tts_complete":
                    trace_id = tts_event.get("trace_id")
                    trace_ids[f"tts_sentence_{tts_sentence_count}"] = trace_id
                    yield {
                        "type": "trace_id",
                        "api": f"{speaker} 第 {tts_sentence_count} 句合成",
                        "trace_id": trace_id
                    }

                    # 立即追加到渐进式音频文件
                    if sentence_audio_chunks:
                        try:
                            from pydub import AudioSegment
                            from pydub.effects import normalize
                            from audio_utils import hex_to_audio_segment

                            # 转换句子音频
                            sentence_audio = AudioSegment.empty()
                            for chunk_hex in sentence_audio_chunks:
                                chunk = hex_to_audio_segment(chunk_hex)
                                if chunk is not None:
                                    sentence_audio += chunk

                            # 对单句进行 normalize，然后调整到目标音量
                            if len(sentence_audio) > 0:
                                sentence_audio = normalize(sentence_audio)
                                logger.info(f"句子 {tts_sentence_count} 音频已标准化，音量: {sentence_audio.dBFS:.2f} dBFS")

                                # 将单句调整到目标音量 -18 dB
                                target_dBFS = -18.0
                                change_in_dBFS = target_dBFS - sentence_audio.dBFS
                                sentence_audio = sentence_audio.apply_gain(change_in_dBFS)
                                logger.info(f"句子 {tts_sentence_count} 音量已调整到 -18 dB，实际: {sentence_audio.dBFS:.2f} dBFS")

                            # 在内存中追加（避免多次 MP3 编码/解码）
                            progressive_audio_in_memory = progressive_audio_in_memory + sentence_audio
                            logger.info(f"句子 {tts_sentence_count} 已追加到内存，当前总时长: {len(progressive_audio_in_memory)}ms，音量: {progressive_audio_in_memory.dBFS:.2f} dBFS")

                            # 渐进式累积策略：控制何时发送 progressive_audio 事件
                            update_counter += 1
                            should_send_update = False

                            if tts_sentence_count == 1:
                                # 第一句：立即发送（用户需要尽快听到内容）
                                should_send_update = True
                                logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，立即发送更新")
                            elif tts_sentence_count <= 3:
                                # 第 2-3 句：每 2 句发送一次
                                if update_counter >= 2:
                                    should_send_update = True
                                    update_counter = 0
                                    logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，累积 2 句，发送更新")
                                else:
                                    logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，累积 {update_counter} 句，暂不发送")
                            elif tts_sentence_count <= 8:
                                # 第 4-8 句：每 3 句发送一次
                                if update_counter >= 3:
                                    should_send_update = True
                                    update_counter = 0
                                    logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，累积 3 句，发送更新")
                                else:
                                    logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，累积 {update_counter} 句，暂不发送")
                            else:
                                # 第 9 句之后：每 4 句发送一次
                                if update_counter >= 4:
                                    should_send_update = True
                                    update_counter = 0
                                    logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，累积 4 句，发送更新")
                                else:
                                    logger.info(f"[后端渐进式] 第 {tts_sentence_count} 句，累积 {update_counter} 句，暂不发送")

                            # 只有在需要发送时才导出到文件并发送事件
                            if should_send_update:
                                # 导出当前内存中的音频到文件
                                progressive_audio_in_memory.export(progressive_path, format="mp3")
                                logger.info(f"第 {tts_sentence_count} 句：导出到渐进式文件，时长: {len(progressive_audio_in_memory)}ms")

                                yield {
                                    "type": "progressive_audio",
                                    "audio_url": f"/download/audio/{progressive_filename}?t={int(time.time())}",
                                    "duration_ms": len(progressive_audio_in_memory),
                                    "sentence_number": tts_sentence_count,
                                    "message": f"第 {tts_sentence_count} 句已添加到播客，播客时长: {math.ceil(len(progressive_audio_in_memory) / 1000)}秒"
                                }
                        except Exception as e:
                            logger.error(f"追加句子 {tts_sentence_count} 到渐进式音频失败: {str(e)}")

                elif tts_event["type"] == "error":
                    # TTS 错误，也记录 Trace ID
                    if tts_event.get("trace_id"):
                        trace_ids[f"tts_sentence_{tts_sentence_count}_error"] = tts_event.get("trace_id")
                        yield {
                            "type": "trace_id",
                            "api": f"{speaker} 第 {tts_sentence_count} 句合成（失败）",
                            "trace_id": tts_event.get("trace_id")
                        }
                    # 转发错误事件
                    yield tts_event

        # 等待脚本生成线程完成
        logger.info("📝 [主线程] 等待脚本生成线程完成...")
        script_thread.join()
        logger.info("📝 [主线程] 脚本生成线程已完成")

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

        # Step 3: 立即添加结尾 BGM 到渐进式音频（所有对话合成完毕后）
        logger.info("🎵 [主线程] 开始添加结尾 BGM（立即执行，不等封面）")
        yield {
            "type": "progress",
            "step": "adding_ending_bgm",
            "message": "正在添加结尾音乐..."
        }

        try:
            from pydub import AudioSegment

            # 加载 BGM 并调整到 -18 dB
            bgm01 = AudioSegment.from_file(self.bgm01_path)
            bgm02 = AudioSegment.from_file(self.bgm02_path).fade_out(1000)

            bgm01_adjusted = bgm01.apply_gain(-18.0 - bgm01.dBFS)
            bgm02_adjusted = bgm02.apply_gain(-18.0 - bgm02.dBFS)
            logger.info(f"🎵 BGM1 音量: {bgm01_adjusted.dBFS:.2f} dBFS, BGM2 音量: {bgm02_adjusted.dBFS:.2f} dBFS")

            # 在内存中追加结尾 BGM
            progressive_audio_in_memory = progressive_audio_in_memory + bgm01_adjusted + bgm02_adjusted
            logger.info(f"🎵 [主线程] 结尾 BGM 已追加到内存，最终播客时长: {len(progressive_audio_in_memory)}ms，音量: {progressive_audio_in_memory.dBFS:.2f} dBFS")

            # 导出最终版本到文件
            progressive_audio_in_memory.export(progressive_path, format="mp3")
            logger.info(f"🎵 最终播客已导出到文件: {progressive_path}")

            # 发送最终音频更新
            yield {
                "type": "progressive_audio",
                "audio_url": f"/download/audio/{progressive_filename}?t={int(time.time())}",
                "duration_ms": len(progressive_audio_in_memory),
                "message": "结尾音乐已添加"
            }
        except Exception as e:
            logger.error(f"🎵 [主线程] 添加结尾 BGM 失败: {str(e)}")

        # Step 4: 等待封面生成完成（封面在后台并发生成）
        # 检查封面线程是否还在运行
        logger.info("🎨 [主线程] 检查封面线程状态...")
        if cover_thread.is_alive():
            yield {
                "type": "progress",
                "step": "waiting_cover",
                "message": "正在等待封面生成完成..."
            }
            logger.info("🎨 [主线程] 封面线程仍在运行，等待完成...")
        else:
            logger.info("🎨 [主线程] 封面线程已完成")

        # 等待封面生成线程完成
        cover_thread.join()
        logger.info("🎨 [主线程] 封面线程已 join 完成")

        # 发送封面相关的 Trace ID
        if cover_result.get("text_trace_id"):
            yield {
                "type": "trace_id",
                "api": "封面 Prompt 生成",
                "trace_id": cover_result.get("text_trace_id")
            }

        if cover_result.get("image_trace_id"):
            yield {
                "type": "trace_id",
                "api": "封面图生成",
                "trace_id": cover_result.get("image_trace_id")
            }

        # 发送封面生成结果
        if cover_result.get("success"):
            yield {
                "type": "cover_image",
                "image_url": cover_result["image_url"],
                "prompt": cover_result.get("prompt", "")
            }
            yield {
                "type": "progress",
                "step": "cover_complete",
                "message": "封面生成完成"
            }
            logger.info("封面已发送到前端")
        else:
            yield {
                "type": "progress",
                "step": "cover_failed",
                "message": f"封面生成失败: {cover_result.get('message', '未知错误')}"
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
            logger.info(f"脚本已保存到: {script_path}")

            # 发送完成事件
            logger.info(f"发送 complete 事件: audio_url=/download/audio/{output_filename}, script_url=/download/script/{script_filename}")
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
            logger.info("complete 事件已发送")

        except Exception as e:
            logger.error(f"音频合并或脚本保存失败: {str(e)}")
            logger.exception("详细错误:")
            yield {
                "type": "error",
                "message": f"音频处理失败: {str(e)}"
            }


# 单例实例
podcast_generator = PodcastGenerator()
