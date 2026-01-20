"""
播客生成核心逻辑
协调并行任务、批量脚本生成与语音合成同步
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Iterator, List
from queue import Queue, Empty
from config import (
    BGM_FILES,
    WELCOME_TEXT,
    PODCAST_CONFIG,
    OUTPUT_DIR,
    DEFAULT_VOICES
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
        self.max_retries = 3
        self.retry_delay = 2
        self.batch_size = 3  # 每批处理的句子数，可调整

    def _parse_speaker_line(self, line: str) -> tuple:
        """
        解析脚本行，提取 Speaker 和文本

        Args:
            line: 脚本行，格式如 "Speaker1: 文本内容"

        Returns:
            (speaker, text) 元组，如果解析失败返回 (None, None)
        """
        if not line or ':' not in line:
            return None, None

        # 支持多种分隔符：": "（英文）、":"（无空格）、"："（中文）
        for separator in [': ', ':', '：']:
            if separator in line:
                parts = line.split(separator, 1)
                speaker = parts[0].strip()
                text = parts[1].strip() if len(parts) > 1 else ""

                # 标准化 Speaker 名称
                speaker = self._normalize_speaker(speaker)

                # 验证格式
                if speaker and text:
                    return speaker, text
                break

        return None, None

    def _normalize_speaker(self, speaker: str) -> str:
        """
        标准化 Speaker 名称

        Args:
            speaker: 原始 speaker 字符串

        Returns:
            标准化的 speaker 名称
        """
        # 映射多种格式到标准格式
        speaker_map = {
            "Speaker1": "Speaker1",
            "Speaker2": "Speaker2",
            "Mini": "Speaker1",
            "Max": "Speaker2",
            "mini": "Speaker1",
            "max": "Speaker2",
            "1": "Speaker1",
            "2": "Speaker2",
            "小": "Speaker1",
            "大": "Speaker2",
        }

        # 尝试精确匹配
        if speaker in speaker_map:
            return speaker_map[speaker]

        # 尝试模糊匹配
        speaker_lower = speaker.lower()
        if speaker_lower in ['mini', 'speaker1', '1', '小']:
            return "Speaker1"
        elif speaker_lower in ['max', 'speaker2', '2', '大']:
            return "Speaker2"

        # 如果不匹配，返回原值（可能需要调试）
        return speaker

    def _extract_lines_from_buffer(self, buffer: str) -> tuple:
        """
        从 buffer 中提取所有完整行（简化版）

        核心改进：不再做复杂的句子完整性判断，只提取完整行

        Args:
            buffer: 累积的文本缓冲

        Returns:
            (lines, remaining_buffer) - 提取的行列表和剩余缓冲
        """
        if not buffer:
            return [], buffer

        lines = []
        remaining = buffer

        # 按行分割
        while '\n' in remaining:
            line, remaining = remaining.split('\n', 1)
            line = line.strip()
            if line:
                lines.append(line)

        return lines, remaining

    def _is_valid_sentence(self, speaker: str, text: str) -> bool:
        """
        验证句子是否有效（简化版）

        Args:
            speaker: 说话人
            text: 文本内容

        Returns:
            是否有效
        """
        if not speaker or not text:
            return False

        # 必须是有效的 speaker
        if speaker not in ["Speaker1", "Speaker2"]:
            return False

        # 文本不能太短（至少 5 个字符）
        if len(text) < 5:
            return False

        # 文本不能包含明显的格式问题
        if text.startswith(':') or text.endswith(':'):
            return False

        return True

    def _synthesize_with_retry(self, text: str, voice_id: str, api_key: str,
                                is_custom_voice: bool = False,
                                fallback_voice_id: str = None,
                                speaker_name: str = "Speaker",
                                sentence_num: int = 0) -> tuple:
        """
        带重试机制的语音合成（保持原有实现）
        """
        # ... 保持原有实现不变 ...
        audio_chunks = []
        used_fallback = False
        trace_ids = {}
        last_error = None

        voice_ids_to_try = []
        if is_custom_voice and voice_id:
            voice_ids_to_try.append((voice_id, False, f"自定义音色 ({voice_id[:20]}...)"))
        if fallback_voice_id:
            voice_ids_to_try.append((fallback_voice_id, True, f"默认音色 ({fallback_voice_id[:20]}...)"))

        if not voice_ids_to_try:
            voice_ids_to_try = [(voice_id, False, "首选音色")]

        for current_voice_id, is_fallback, voice_desc in voice_ids_to_try:
            for retry_count in range(self.max_retries):
                error_occurred = None

                try:
                    logger.info(f"🎙️ [{speaker_name}] 第{sentence_num}句 尝试 ({retry_count + 1}/{self.max_retries}): {voice_desc}")

                    for tts_event in minimax_client.synthesize_speech_stream(text, current_voice_id, api_key=api_key):
                        if tts_event["type"] == "audio_chunk":
                            audio_chunks.append(tts_event["audio"])
                        elif tts_event["type"] == "tts_complete":
                            trace_id_key = f"tts_{speaker_name}_{sentence_num}"
                            if is_fallback:
                                trace_id_key += "_fallback"
                            trace_ids[trace_id_key] = tts_event.get("trace_id")
                            logger.info(f"🎙️ [{speaker_name}] 第{sentence_num}句 成功，使用 {voice_desc}")
                        elif tts_event["type"] == "error":
                            error_occurred = tts_event.get("message", "未知错误")
                            logger.warning(f"🎙️ [{speaker_name}] 第{sentence_num}句 收到错误事件: {error_occurred}")

                    if audio_chunks:
                        PodcastGenerator._rpm_error_count = 0
                        return audio_chunks, is_fallback, trace_ids

                    if error_occurred:
                        raise Exception(error_occurred)

                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    logger.warning(f"🎙️ [{speaker_name}] 第{sentence_num}句 第{retry_count + 1}次尝试失败: {error_msg}")

                    is_rpm_error = ("rate" in error_msg.lower() or "rpm" in error_msg.lower()
                                   or "限流" in error_msg.lower() or "rate limit" in error_msg.lower())

                    if is_rpm_error:
                        PodcastGenerator._rpm_error_count += 1
                        PodcastGenerator._last_rpm_error_time = time.time()

                        if PodcastGenerator._rpm_error_count >= 3:
                            logger.warning(f"⚠️ 连续 {PodcastGenerator._rpm_error_count} 次遇到 RPM 限制，建议稍后重试")

                        base_wait = 10
                        wait_time = base_wait * (retry_count + 1)

                        if PodcastGenerator._rpm_error_count > 3:
                            wait_time += 30

                        logger.info(f"🎙️ [{speaker_name}] 第{sentence_num}句 检测到 RPM 限制（连续第 {PodcastGenerator._rpm_error_count} 次），"
                                   f"等待 {wait_time} 秒后重试...")
                        logger.info(f"💡 提示: RPM 限制通常在 1-2 分钟内解除，请耐心等待")

                        time.sleep(wait_time)

                        if retry_count < self.max_retries - 1:
                            continue
                    else:
                        break

        PodcastGenerator._rpm_error_count = 0
        logger.error(f"🎙️ [{speaker_name}] 第{sentence_num}句 所有尝试都失败: {last_error}")
        return audio_chunks, used_fallback, trace_ids

    def generate_podcast_stream(self,
                                content: str,
                                speaker1_voice_id: str,
                                speaker2_voice_id: str,
                                session_id: str,
                                api_key: str,
                                speaker1_is_custom_voice_id: bool = False,
                                speaker2_is_custom_voice_id: bool = False) -> Iterator[Dict[str, Any]]:
        """
        流式生成播客（批量处理版本）

        核心改进：
        1. 简化句子提取逻辑
        2. 批量 TTS 合成（每批 N 句）
        3. 降低复杂性，提高稳定性

        Args:
            content: 解析后的内容
            speaker1_voice_id: Speaker1 音色 ID
            speaker2_voice_id: Speaker2 音色 ID
            session_id: 会话 ID
            api_key: 用户提供的 MiniMax API Key
            speaker1_is_custom_voice_id: Speaker1 是否使用自定义 voice_id
            speaker2_is_custom_voice_id: Speaker2 是否使用自定义 voice_id

        Yields:
            包含各种事件的字典
        """
        # 语音 ID 映射
        voice_mapping = {
            "Speaker1": speaker1_voice_id,
            "Speaker2": speaker2_voice_id,
            "Mini": speaker1_voice_id,
            "Max": speaker2_voice_id,
            "mini": speaker1_voice_id,
            "max": speaker2_voice_id,
            "1": speaker1_voice_id,
            "2": speaker2_voice_id
        }

        all_audio_chunks = []
        all_script_lines = []
        trace_ids = {}

        progressive_filename = f"progressive_{session_id}.mp3"
        progressive_path = os.path.join(OUTPUT_DIR, progressive_filename)
        progressive_audio_in_memory = None

        # Step 1: 生成并播放欢迎音频
        yield {
            "type": "progress",
            "step": "welcome_audio",
            "message": "正在播放欢迎音频..."
        }

        yield {
            "type": "bgm",
            "bgm_type": "bgm01",
            "path": self.bgm01_path
        }

        default_speaker1_voice_id = DEFAULT_VOICES["mini"]["voice_id"]
        default_speaker2_voice_id = DEFAULT_VOICES["max"]["voice_id"]

        logger.info(f"🎙️ [开场白] 用户选择的 Speaker1 音色: {speaker1_voice_id}")
        welcome_audio_chunks, welcome_used_fallback, welcome_trace_ids = self._synthesize_with_retry(
            text=self.welcome_text,
            voice_id=speaker1_voice_id,
            api_key=api_key,
            is_custom_voice=speaker1_is_custom_voice_id,
            fallback_voice_id=default_speaker1_voice_id,
            speaker_name="开场白",
            sentence_num=0
        )

        trace_ids.update(welcome_trace_ids)

        for key, trace_id in welcome_trace_ids.items():
            yield {
                "type": "trace_id",
                "api": f"欢迎语合成{'（回退到默认音色）' if welcome_used_fallback else ''}",
                "trace_id": trace_id
            }

        if not welcome_audio_chunks:
            logger.warning("🎙️ [开场白] 所有尝试都失败")
            yield {
                "type": "log",
                "message": "⚠️  开场语生成失败，可能是音色不可用或网络问题"
            }

        yield {
            "type": "bgm",
            "bgm_type": "bgm02_fadeout",
            "path": self.bgm02_path
        }

        # 生成开场音频
        logger.info("开始生成开场音频（BGM1 + 欢迎语 + BGM2）")
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize
            from audio_utils import hex_to_audio_segment

            logger.info(f"加载 BGM01: {self.bgm01_path}")
            bgm01 = AudioSegment.from_file(self.bgm01_path)
            logger.info(f"BGM01 时长: {len(bgm01)}ms")

            logger.info(f"加载 BGM02: {self.bgm02_path}")
            bgm02 = AudioSegment.from_file(self.bgm02_path).fade_out(1000)
            logger.info(f"BGM02 时长: {len(bgm02)}ms")

            welcome_audio = AudioSegment.empty()
            for i, chunk_hex in enumerate(welcome_audio_chunks):
                logger.info(f"处理欢迎语 chunk {i + 1}/{len(welcome_audio_chunks)}")
                chunk = hex_to_audio_segment(chunk_hex)
                if chunk:
                    welcome_audio += chunk

            logger.info(f"欢迎语总时长: {len(welcome_audio)}ms")

            if len(welcome_audio) > 0:
                welcome_audio = normalize(welcome_audio)
                logger.info(f"欢迎语音频已标准化，音量: {welcome_audio.dBFS:.2f} dBFS")
                target_dBFS = -18.0
                change_in_dBFS = target_dBFS - welcome_audio.dBFS
                welcome_audio = welcome_audio.apply_gain(change_in_dBFS)
                logger.info(f"欢迎语音量已调整到 -18 dB，实际: {welcome_audio.dBFS:.2f} dBFS")

            bgm01_adjusted = bgm01.apply_gain(-18.0 - bgm01.dBFS)
            bgm02_adjusted = bgm02.apply_gain(-18.0 - bgm02.dBFS)

            intro_audio = bgm01_adjusted + welcome_audio + bgm02_adjusted
            logger.info(f"开场音频总时长: {len(intro_audio)}ms，音量: {intro_audio.dBFS:.2f} dBFS")

            progressive_audio_in_memory = intro_audio

            logger.info(f"开始导出开场音频到渐进式文件: {progressive_path}")
            progressive_audio_in_memory.export(progressive_path, format="mp3")
            logger.info(f"开场音频已保存到: {progressive_path}")

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

        # Step 2: 批量流式生成脚本
        yield {
            "type": "progress",
            "step": "script_generation",
            "message": "正在生成播客脚本..."
        }

        script_buffer = ""
        batch_queue = Queue()  # 批量队列
        batch_counter = 0  # 当前批次句子计数
        current_batch = []  # 当前批次的句子

        # 脚本生成线程（简化版）
        def script_generation_thread():
            nonlocal script_buffer, batch_counter, current_batch
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

                        # 简化逻辑：提取所有完整行
                        lines, script_buffer = self._extract_lines_from_buffer(script_buffer)

                        for line in lines:
                            speaker, text = self._parse_speaker_line(line)

                            if speaker and text and self._is_valid_sentence(speaker, text):
                                # 添加到当前批次
                                current_batch.append((speaker, text))
                                batch_counter += 1
                                logger.info(f"📝 批次 {len(all_script_lines) // self.batch_size + 1} - "
                                           f"第 {batch_counter} 句: {speaker}: {text[:30]}...")

                                # 如果达到批次大小，放入队列
                                if len(current_batch) >= self.batch_size:
                                    batch_queue.put(("batch", list(current_batch)))
                                    logger.info(f"📝 批次 {len(all_script_lines) // self.batch_size + 1} 已满（{len(current_batch)} 句），放入队列")
                                    current_batch = []
                                    batch_counter = 0

                    elif script_event["type"] == "script_complete":
                        # 处理剩余的 buffer
                        if script_buffer.strip():
                            lines, _ = self._extract_lines_from_buffer(script_buffer)
                            for line in lines:
                                speaker, text = self._parse_speaker_line(line)
                                if speaker and text and self._is_valid_sentence(speaker, text):
                                    current_batch.append((speaker, text))
                                    batch_counter += 1

                        # 处理剩余的批次
                        if current_batch:
                            batch_queue.put(("batch", list(current_batch)))
                            logger.info(f"📝 最后批次，包含 {len(current_batch)} 句，放入队列")
                            current_batch = []

                        trace_ids["script_generation"] = script_event.get("trace_id")
                        logger.info("脚本生成完成，发送完成信号")
                        batch_queue.put(("complete", None, None))

                    elif script_event["type"] == "error":
                        logger.error(f"脚本生成错误: {script_event.get('message')}")
                        # 即使出错也处理剩余内容
                        if current_batch:
                            batch_queue.put(("batch", list(current_batch)))
                        batch_queue.put(("complete", None, None))

            except Exception as e:
                logger.error(f"脚本生成线程异常: {str(e)}")
                logger.exception("详细错误:")
                # 确保发送完成信号
                if current_batch:
                    batch_queue.put(("batch", list(current_batch)))
                batch_queue.put(("complete", None, None))

        # 启动脚本生成线程
        script_thread = threading.Thread(target=script_generation_thread)
        logger.info("🚀 启动脚本生成线程")
        script_thread.start()

        # 主线程：批量消费队列，进行 TTS 合成
        tts_sentence_count = 0
        total_batch_count = 0
        import math

        while True:
            try:
                item = batch_queue.get(timeout=300)  # 5分钟超时
                if item[0] == "complete":
                    break

                _, batch_sentences = item
                total_batch_count += 1
                logger.info(f"\n{'='*60}")
                logger.info(f"📦 开始处理第 {total_batch_count} 批次，共 {len(batch_sentences)} 句")
                logger.info(f"{'='*60}\n")

                # 批量 TTS 合成
                batch_audio_chunks = []
                batch_failed_count = 0

                for speaker, text in batch_sentences:
                    tts_sentence_count += 1

                    # 发送脚本内容到前端
                    full_line = f"{speaker}: {text}"
                    all_script_lines.append(full_line)
                    yield {
                        "type": "script_chunk",
                        "speaker": speaker,
                        "text": text,
                        "full_line": full_line,
                        "batch_number": total_batch_count,
                        "sentence_number": tts_sentence_count
                    }

                    # 获取对应音色
                    voice_id = voice_mapping.get(speaker, speaker1_voice_id)

                    is_custom_voice_id = ((speaker == "Speaker1" or speaker == "Mini") and speaker1_is_custom_voice_id) or \
                                         ((speaker == "Speaker2" or speaker == "Max") and speaker2_is_custom_voice_id)

                    logger.info(f"🎙️ [{speaker}] 使用 voice_id: {voice_id} (is_custom={is_custom_voice_id})")

                    fallback_voice_id = default_speaker1_voice_id if speaker == "Speaker1" else default_speaker2_voice_id
                    fallback_speaker_name = "Mini" if speaker == "Speaker1" else "Max"

                    # TTS 合成
                    sentence_audio_chunks, used_fallback, sentence_trace_ids = self._synthesize_with_retry(
                        text=text,
                        voice_id=voice_id,
                        api_key=api_key,
                        is_custom_voice=is_custom_voice_id,
                        fallback_voice_id=fallback_voice_id,
                        speaker_name=f"{speaker}",
                        sentence_num=tts_sentence_count
                    )

                    trace_ids.update(sentence_trace_ids)

                    for key, trace_id in sentence_trace_ids.items():
                        api_name = f"{speaker} 第 {tts_sentence_count} 句合成"
                        if used_fallback and is_custom_voice_id:
                            api_name += '（回退到默认音色）'
                        yield {
                            "type": "trace_id",
                            "api": api_name,
                            "trace_id": trace_id
                        }

                    if used_fallback and is_custom_voice_id:
                        logger.warning(f"⚠️ [{speaker}] 第 {tts_sentence_count} 句回退到默认音色")
                        yield {
                            "type": "log",
                            "message": f"⚠️  {speaker} 第 {tts_sentence_count} 句使用自定义音色失败，已回退到{fallback_speaker_name}的默认音色"
                        }

                    if not sentence_audio_chunks:
                        logger.error(f"❌ [{speaker}] 第 {tts_sentence_count} 句所有尝试都失败，跳过此句")
                        yield {
                            "type": "log",
                            "message": f"⚠️  第 {tts_sentence_count} 句语音合成失败，可能是网络问题或音色不可用"
                        }
                        batch_failed_count += 1
                        continue

                    # 收集音频
                    batch_audio_chunks.extend(sentence_audio_chunks)
                    all_audio_chunks.extend(sentence_audio_chunks)

                # 批量处理完成后，追加到渐进式音频
                if batch_audio_chunks:
                    try:
                        from pydub import AudioSegment
                        from pydub.effects import normalize
                        from audio_utils import hex_to_audio_segment

                        # 转换批次音频
                        batch_audio = AudioSegment.empty()
                        for chunk_hex in batch_audio_chunks:
                            chunk = hex_to_audio_segment(chunk_hex)
                            if chunk is not None:
                                batch_audio += chunk

                        # 标准化并调整音量
                        if len(batch_audio) > 0:
                            batch_audio = normalize(batch_audio)
                            batch_audio = batch_audio.apply_gain(-18.0 - batch_audio.dBFS)

                        # 在内存中追加
                        progressive_audio_in_memory = progressive_audio_in_memory + batch_audio
                        logger.info(f"📦 批次 {total_batch_count} 已追加，当前总时长: {len(progressive_audio_in_memory)}ms")

                        # 导出到文件
                        progressive_audio_in_memory.export(progressive_path, format="mp3")

                        # 发送渐进式更新
                        failed_info = f"（{batch_failed_count} 句失败）" if batch_failed_count > 0 else ""
                        yield {
                            "type": "progressive_audio",
                            "audio_url": f"/download/audio/{progressive_filename}?t={int(time.time())}",
                            "duration_ms": len(progressive_audio_in_memory),
                            "batch_number": total_batch_count,
                            "sentence_number": tts_sentence_count,
                            "message": f"第 {total_batch_count} 批次完成{failed_info}，播客时长: {math.ceil(len(progressive_audio_in_memory) / 1000)}秒"
                        }

                        logger.info(f"📦 批次 {total_batch_count} 更新已发送到前端")

                    except Exception as e:
                        logger.error(f"📦 批次 {total_batch_count} 追加到渐进式音频失败: {str(e)}")

                batch_queue.task_done()

            except Empty:
                logger.error("⏰ 批量队列等待超时（5分钟）")
                break

        # 等待脚本生成线程完成
        logger.info("📝 [主线程] 等待脚本生成线程完成...")
        script_thread.join()
        logger.info("📝 [主线程] 脚本生成线程已完成")

        # 检查是否生成了有效的脚本内容
        if tts_sentence_count == 0:
            logger.error("脚本生成结果为空，无法继续生成播客")
            yield {
                "type": "error",
                "message": "脚本生成失败：LLM 返回了空内容。这可能是因为输入内容太少或格式不正确。请尝试提供更丰富的内容（至少 50 字符以上）。"
            }
            return

        yield {
            "type": "progress",
            "step": "script_complete",
            "message": f"脚本生成完成，共 {tts_sentence_count} 句对话，分为 {total_batch_count} 批次"
        }

        yield {
            "type": "trace_id",
            "api": "脚本生成",
            "trace_id": trace_ids.get("script_generation")
        }

        # Step 3: 添加结尾 BGM
        logger.info("🎵 [主线程] 开始添加结尾 BGM")
        yield {
            "type": "progress",
            "step": "adding_ending_bgm",
            "message": "正在添加结尾音乐..."
        }

        try:
            from pydub import AudioSegment

            if progressive_audio_in_memory is None:
                logger.warning("开场音频为空，创建空白音频作为基础")
                progressive_audio_in_memory = AudioSegment.empty()

            bgm01 = AudioSegment.from_file(self.bgm01_path)
            bgm02 = AudioSegment.from_file(self.bgm02_path).fade_out(1000)

            bgm01_adjusted = bgm01.apply_gain(-18.0 - bgm01.dBFS)
            bgm02_adjusted = bgm02.apply_gain(-18.0 - bgm02.dBFS)

            progressive_audio_in_memory = progressive_audio_in_memory + bgm01_adjusted + bgm02_adjusted
            logger.info(f"🎵 结尾 BGM 已追加，最终播客时长: {len(progressive_audio_in_memory)}ms")

            progressive_audio_in_memory.export(progressive_path, format="mp3")

            yield {
                "type": "progressive_audio",
                "audio_url": f"/download/audio/{progressive_filename}?t={int(time.time())}",
                "duration_ms": len(progressive_audio_in_memory),
                "message": "结尾音乐已添加"
            }
        except Exception as e:
            logger.error(f"🎵 添加结尾 BGM 失败: {str(e)}")
            logger.exception("详细错误:")

        # Step 4: 合并完整播客并生成封面
        yield {
            "type": "progress",
            "step": "audio_merging",
            "message": "正在合并完整播客音频..."
        }

        output_filename = f"podcast_{session_id}_{int(time.time())}.mp3"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        try:
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

            # 生成封面
            logger.info("🎨 [封面生成] 开始使用播客脚本生成封面...")
            cover_result = self.generate_cover_from_script(all_script_lines, api_key)

            if cover_result.get("text_trace_id"):
                trace_ids["cover_prompt_generation"] = cover_result.get("text_trace_id")
                yield {
                    "type": "trace_id",
                    "api": "封面 Prompt 生成",
                    "trace_id": cover_result.get("text_trace_id")
                }

            if cover_result.get("image_trace_id"):
                trace_ids["cover_image_generation"] = cover_result.get("image_trace_id")
                yield {
                    "type": "trace_id",
                    "api": "封面图生成",
                    "trace_id": cover_result.get("image_trace_id")
                }

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
                logger.info("🎨 封面已发送到前端")
            else:
                logger.warning(f"🎨 封面生成失败: {cover_result.get('message', '未知错误')}")

            # 发送完成事件
            logger.info(f"发送 complete 事件: audio_url=/download/audio/{output_filename}, "
                       f"script_url=/download/script/{script_filename}, "
                       f"共 {tts_sentence_count} 句，{total_batch_count} 批次")
            yield {
                "type": "complete",
                "audio_path": output_path,
                "audio_url": f"/download/audio/{output_filename}",
                "script_path": script_path,
                "script_url": f"/download/script/{script_filename}",
                "cover_url": cover_result.get("image_url", ""),
                "trace_ids": trace_ids,
                "total_sentences": tts_sentence_count,
                "total_batches": total_batch_count,
                "message": f"播客生成完成！共 {tts_sentence_count} 句对话，分为 {total_batch_count} 批次处理"
            }
            logger.info("complete 事件已发送")

        except Exception as e:
            logger.error(f"音频合并或脚本保存失败: {str(e)}")
            logger.exception("详细错误:")
            yield {
                "type": "error",
                "message": f"音频处理失败: {str(e)}"
            }

    def extract_core_elements(self, script_lines: List[str]) -> Dict[str, Any]:
        """
        从播客脚本中提取封面生成所需的核心元素
        """
        try:
            full_script = '\n'.join(script_lines)

            topics = []
            for line in script_lines[:10]:
                if ': ' in line:
                    content = line.split(': ', 1)[1].strip()
                    words = content.split()
                    for word in words:
                        if len(word) > 3 and not word in ['这个', '那个', '什么', '如何', '怎么', '为什么']:
                            topics.append(word)

            unique_topics = list(dict.fromkeys(topics))[:5]

            summary = full_script[:300] if len(full_script) > 300 else full_script

            speakers = set()
            for line in script_lines:
                if ': ' in line:
                    speaker = line.split(': ', 1)[0].strip()
                    speakers.add(speaker)

            return {
                "summary": summary,
                "keywords": unique_topics,
                "speaker_count": len(speakers),
                "full_script": full_script,
                "title": unique_topics[0] if unique_topics else "播客节目"
            }

        except Exception as e:
            logger.error(f"提取核心元素失败: {str(e)}")
            return {
                "summary": '',
                "keywords": [],
                "speaker_count": 2,
                "full_script": '\n'.join(script_lines) if script_lines else '',
                "title": "播客节目"
            }

    def generate_cover_from_script(self, script_lines: List[str], api_key: str) -> Dict[str, Any]:
        """
        使用播客脚本内容生成封面
        """
        try:
            core_elements = self.extract_core_elements(script_lines)

            cover_content = f"""
播客主题：{core_elements['title']}
关键词：{', '.join(core_elements['keywords'])}
内容摘要：{core_elements['summary']}

这是一个关于{core_elements['title']}的播客节目，请根据以上信息生成一张吸引人的封面图。
"""

            logger.info(f"🎨 [封面生成] 提取的核心元素: keywords={core_elements['keywords']}")

            cover_result = minimax_client.generate_cover_image(cover_content, api_key=api_key)

            if cover_result.get("success"):
                logger.info(f"🎨 [封面生成] 成功，image_url: {cover_result.get('image_url', '')}")
            else:
                logger.error(f"🎨 [封面生成] 失败: {cover_result.get('message', '未知错误')}")

            return cover_result

        except Exception as e:
            logger.error(f"🎨 [封面生成] 异常: {str(e)}")
            logger.exception("详细错误:")
            return {
                "success": False,
                "message": str(e)
            }


# 单例实例
podcast_generator = PodcastGenerator()
