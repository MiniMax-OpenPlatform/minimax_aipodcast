"""
音频处理工具
支持 BGM 拼接、音频流式拼接、淡入淡出等功能
"""
import os
import logging
import tempfile
from pydub import AudioSegment
from pydub.effects import normalize
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def concatenate_audio_files(audio_files, output_path, fade_out_duration=1000):
    """
    拼接多个音频文件
    
    Args:
        audio_files: 音频文件路径列表
        output_path: 输出文件路径
        fade_out_duration: 最后一段音频淡出时长（毫秒）
    """
    if not audio_files:
        raise ValueError("音频文件列表不能为空")
    
    # 加载第一个音频
    combined = AudioSegment.from_file(audio_files[0])
    
    # 依次拼接其他音频
    for i, audio_file in enumerate(audio_files[1:], 1):
        audio = AudioSegment.from_file(audio_file)
        
        # 如果是最后一个文件且是bgm02，添加淡出效果
        if i == len(audio_files) - 1 and 'bgm02' in audio_file:
            audio = audio.fade_out(fade_out_duration)
        
        combined += audio
    
    # 标准化音量
    combined = normalize(combined)
    
    # 导出
    combined.export(output_path, format="mp3")
    
    return output_path


def adjust_audio_volume(audio_file, output_path, volume_change_db=0):
    """
    调整音频音量
    
    Args:
        audio_file: 输入音频文件路径
        output_path: 输出文件路径
        volume_change_db: 音量变化（分贝）
    """
    audio = AudioSegment.from_file(audio_file)
    adjusted = audio + volume_change_db
    adjusted.export(output_path, format="mp3")
    return output_path


def get_audio_duration(audio_file):
    """
    获取音频时长（秒）
    """
    audio = AudioSegment.from_file(audio_file)
    return len(audio) / 1000.0


def trim_audio(audio_file, output_path, start_ms=0, end_ms=None):
    """
    裁剪音频
    
    Args:
        audio_file: 输入音频文件
        output_path: 输出文件路径
        start_ms: 开始时间（毫秒）
        end_ms: 结束时间（毫秒），None表示到结尾
    """
    audio = AudioSegment.from_file(audio_file)
    
    if end_ms is None:
        trimmed = audio[start_ms:]
    else:
        trimmed = audio[start_ms:end_ms]
    
    trimmed.export(output_path, format="mp3")
    return output_path


def add_fade_effects(audio_file, output_path, fade_in=1000, fade_out=1000):
    """
    添加淡入淡出效果

    Args:
        audio_file: 输入音频文件
        output_path: 输出文件路径
        fade_in: 淡入时长（毫秒）
        fade_out: 淡出时长（毫秒）
    """
    audio = AudioSegment.from_file(audio_file)

    if fade_in > 0:
        audio = audio.fade_in(fade_in)

    if fade_out > 0:
        audio = audio.fade_out(fade_out)

    audio.export(output_path, format="mp3")
    return output_path


def hex_to_audio_segment(audio_hex: str) -> AudioSegment:
    """
    将十六进制字符串转换为 AudioSegment

    Args:
        audio_hex: 十六进制音频数据字符串

    Returns:
        AudioSegment 对象
    """
    try:
        # 将 hex 数据转换为字节
        audio_bytes = bytes.fromhex(audio_hex)
        logger.info(f"转换音频 hex 数据，长度: {len(audio_bytes)} 字节")

        # 创建临时文件（delete=False，稍后手动删除以便调试）
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        try:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            tmp_file.close()  # 关闭文件以便 ffmpeg 可以正常读取

            logger.info(f"临时 MP3 文件已创建: {tmp_file.name}")

            # 从临时文件加载
            audio_segment = AudioSegment.from_file(tmp_file.name, format="mp3")

            # 强制加载完整数据到内存
            raw_data = audio_segment.raw_data
            logger.info(f"音频数据加载成功，时长: {len(audio_segment)}ms")

            return audio_segment

        finally:
            # 清理临时文件
            try:
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
                    logger.debug(f"临时文件已删除: {tmp_file.name}")
            except Exception as cleanup_error:
                logger.warning(f"删除临时文件失败: {cleanup_error}")

    except Exception as e:
        logger.error(f"hex_to_audio_segment 失败: {str(e)}")
        logger.exception("详细错误:")
        raise


def combine_audio_chunks(audio_hex_list: list, output_path: str) -> str:
    """
    合并多个十六进制音频 chunk 为完整音频文件

    Args:
        audio_hex_list: 十六进制音频数据列表
        output_path: 输出文件路径

    Returns:
        输出文件路径
    """
    if not audio_hex_list:
        raise ValueError("音频 chunk 列表不能为空")

    logger.info(f"开始合并 {len(audio_hex_list)} 个音频 chunk")

    # 合并所有 chunk
    combined = AudioSegment.empty()
    for i, audio_hex in enumerate(audio_hex_list):
        try:
            chunk = hex_to_audio_segment(audio_hex)
            combined += chunk
        except Exception as e:
            logger.error(f"合并第 {i + 1} 个 chunk 失败: {str(e)}")

    # 导出
    combined.export(output_path, format="mp3")
    logger.info(f"成功合并音频，输出: {output_path}")

    return output_path


def create_podcast_with_bgm(bgm01_path: str, bgm02_path: str,
                            welcome_audio_hex: str,
                            dialogue_audio_chunks: list,
                            output_path: str) -> str:
    """
    创建完整的播客音频（BGM + 欢迎语 + 对话内容 + BGM）

    Args:
        bgm01_path: BGM01 文件路径
        bgm02_path: BGM02 文件路径
        welcome_audio_hex: 欢迎语音频（十六进制）
        dialogue_audio_chunks: 对话音频 chunk 列表（十六进制）
        output_path: 输出文件路径

    Returns:
        输出文件路径
    """
    logger.info("开始创建完整播客...")

    # 加载 BGM
    bgm01 = AudioSegment.from_file(bgm01_path)
    bgm02 = AudioSegment.from_file(bgm02_path).fade_out(1000)  # BGM02 淡出 1 秒

    # 转换欢迎语音频
    welcome_audio = hex_to_audio_segment(welcome_audio_hex)

    # 合并对话内容
    dialogue_audio = AudioSegment.empty()
    for chunk_hex in dialogue_audio_chunks:
        try:
            chunk = hex_to_audio_segment(chunk_hex)
            dialogue_audio += chunk
        except Exception as e:
            logger.error(f"合并对话 chunk 失败: {str(e)}")

    # 拼接完整播客：BGM01 + 欢迎语 + BGM02 + 对话内容 + BGM01 + BGM02
    podcast = bgm01 + welcome_audio + bgm02 + dialogue_audio + bgm01 + bgm02

    # 标准化音量
    podcast = normalize(podcast)

    # 导出
    podcast.export(output_path, format="mp3")
    logger.info(f"播客创建完成: {output_path}")

    return output_path


def save_audio_chunk_to_file(audio_hex: str, output_path: str) -> str:
    """
    将单个音频 chunk 保存为文件

    Args:
        audio_hex: 十六进制音频数据
        output_path: 输出文件路径

    Returns:
        输出文件路径
    """
    audio_bytes = bytes.fromhex(audio_hex)
    with open(output_path, 'wb') as f:
        f.write(audio_bytes)
    return output_path



