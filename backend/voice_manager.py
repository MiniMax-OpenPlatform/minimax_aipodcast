"""
音色管理模块
负责 Voice ID 生成、校验和音色克隆管理
"""

import random
import string
import logging
from typing import Dict, Any
from pydub import AudioSegment
from config import VOICE_ID_CONFIG, DEFAULT_VOICES
from minimax_client import minimax_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceManager:
    """音色管理器"""

    def __init__(self):
        self.default_voices = DEFAULT_VOICES
        self.config = VOICE_ID_CONFIG

    def generate_voice_id(self, prefix: str = None) -> str:
        """
        生成符合规范的 Voice ID

        Voice ID 规则：
        - 长度范围 [8, 256]
        - 首字符必须为英文字母
        - 允许数字、字母、-、_
        - 末位字符不可为 -、_

        Args:
            prefix: Voice ID 前缀，默认使用配置中的前缀

        Returns:
            生成的 Voice ID
        """
        if prefix is None:
            prefix = self.config["prefix"]

        # 确保前缀以字母开头
        if not prefix[0].isalpha():
            prefix = "v" + prefix

        # 生成随机字符串（小写字母+数字）
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        # 生成随机数字后缀
        random_num = random.randint(100000, 999999)

        # 组合 Voice ID
        voice_id = f"{prefix}_{random_str}_{random_num}"

        # 确保末位不是 - 或 _（通过数字结尾保证）
        # 校验长度
        if len(voice_id) < self.config["min_length"]:
            # 补充随机字符
            voice_id += ''.join(random.choices(string.ascii_lowercase + string.digits,
                                              k=self.config["min_length"] - len(voice_id)))
        elif len(voice_id) > self.config["max_length"]:
            voice_id = voice_id[:self.config["max_length"]]

        logger.info(f"生成 Voice ID: {voice_id}")
        return voice_id

    def validate_voice_id(self, voice_id: str) -> Dict[str, Any]:
        """
        校验 Voice ID 是否符合规范

        Args:
            voice_id: 要校验的 Voice ID

        Returns:
            校验结果字典
        """
        errors = []

        # 检查长度
        if len(voice_id) < self.config["min_length"]:
            errors.append(f"长度不足 {self.config['min_length']} 字符")
        if len(voice_id) > self.config["max_length"]:
            errors.append(f"长度超过 {self.config['max_length']} 字符")

        # 检查首字符
        if not voice_id[0].isalpha():
            errors.append("首字符必须为英文字母")

        # 检查末位字符
        if voice_id[-1] in ['-', '_']:
            errors.append("末位字符不可为 - 或 _")

        # 检查允许的字符
        allowed = set(self.config["allowed_chars"])
        for char in voice_id:
            if char not in allowed:
                errors.append(f"包含非法字符: {char}")
                break

        if errors:
            return {
                "valid": False,
                "errors": errors
            }
        else:
            return {
                "valid": True,
                "message": "Voice ID 校验通过"
            }

    def clone_custom_voice(self, audio_file_path: str, voice_id: str = None, api_key: str = None) -> Dict[str, Any]:
        """
        克隆自定义音色

        Args:
            audio_file_path: 音频文件路径
            voice_id: 指定的 Voice ID，如果为 None 则自动生成

        Returns:
            包含 voice_id 和 trace_id 的结果字典
        """
        # 检查音频文件时长（必须 >= 10 秒）
        try:
            audio = AudioSegment.from_file(audio_file_path)
            duration_seconds = len(audio) / 1000.0

            logger.info(f"音频文件时长: {duration_seconds:.2f} 秒")

            if duration_seconds < 10:
                error_msg = f"音频时长不足 10 秒（当前 {duration_seconds:.2f} 秒），音色克隆需要至少 10 秒的音频"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "message": error_msg,
                    "duration": duration_seconds
                }

        except Exception as e:
            error_msg = f"无法读取音频文件: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "message": error_msg
            }

        # 生成或校验 Voice ID
        if voice_id is None:
            voice_id = self.generate_voice_id()
        else:
            validation = self.validate_voice_id(voice_id)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Voice ID 校验失败: {', '.join(validation['errors'])}"
                }

        logger.info(f"开始克隆音色，Voice ID: {voice_id}")

        # 调用 MiniMax API 进行音色克隆
        result = minimax_client.clone_voice(
            audio_file_path=audio_file_path,
            voice_id=voice_id,
            api_key=api_key
        )

        return result

    def get_default_voice(self, speaker_name: str) -> Dict[str, Any]:
        """
        获取默认音色信息

        Args:
            speaker_name: "mini" 或 "max"

        Returns:
            音色信息字典
        """
        voice = self.default_voices.get(speaker_name.lower())
        if voice:
            return {
                "success": True,
                "voice": voice
            }
        else:
            return {
                "success": False,
                "error": f"未找到默认音色: {speaker_name}"
            }

    def prepare_voices(self, speaker1_config: Dict[str, Any], speaker2_config: Dict[str, Any], api_key: str = None) -> Dict[str, Any]:
        """
        准备两个 Speaker 的音色

        Args:
            speaker1_config: Speaker1 配置
                {
                    "type": "default" | "custom",
                    "voice_name": "mini" | "max" (default 时使用),
                    "audio_file": "path/to/audio.wav" (custom 时使用)
                }
            speaker2_config: Speaker2 配置（格式同上）

        Returns:
            包含两个 Speaker voice_id 的字典
        """
        results = {
            "speaker1": None,
            "speaker2": None,
            "logs": [],
            "trace_ids": {}
        }

        # 准备 Speaker1 音色
        if speaker1_config["type"] == "default":
            voice_name = speaker1_config.get("voice_name", "mini")
            voice_info = self.get_default_voice(voice_name)
            if voice_info["success"]:
                results["speaker1"] = voice_info["voice"]["voice_id"]
                results["logs"].append(f"Speaker1 使用默认音色: {voice_info['voice']['name']}")
            else:
                results["logs"].append(f"错误: {voice_info['error']}")
                return {"success": False, "error": voice_info['error']}

        elif speaker1_config["type"] == "custom":
            audio_file = speaker1_config.get("audio_file")
            if not audio_file:
                return {"success": False, "error": "Speaker1 未提供音频文件", "logs": results["logs"]}

            clone_result = self.clone_custom_voice(audio_file, api_key=api_key)
            if clone_result["success"]:
                results["speaker1"] = clone_result["voice_id"]
                results["trace_ids"]["speaker1_upload"] = clone_result.get("upload_trace_id")
                results["trace_ids"]["speaker1_clone"] = clone_result.get("clone_trace_id")
                results["logs"].append(f"✅ Speaker1 音色克隆成功: {clone_result['voice_id']}")
            else:
                # 音色克隆失败，记录详细错误，并使用默认音色作为降级方案
                error_detail = clone_result.get('error', '未知错误')
                results["logs"].append(f"❌ Speaker1 音色克隆失败: {error_detail}")

                # 如果是时长不足的错误，提供更明确的提示
                if 'duration' in clone_result:
                    results["logs"].append(f"⚠️  音频时长仅 {clone_result['duration']:.2f} 秒，需要至少 10 秒")

                results["logs"].append(f"⚠️  降级使用默认音色 Mini（女声）")

                # 降级到默认音色
                voice_info = self.get_default_voice("mini")
                if voice_info["success"]:
                    results["speaker1"] = voice_info["voice"]["voice_id"]
                else:
                    return {"success": False, "error": "无法使用默认音色作为降级方案", "logs": results["logs"]}

        # 准备 Speaker2 音色
        if speaker2_config["type"] == "default":
            voice_name = speaker2_config.get("voice_name", "max")
            voice_info = self.get_default_voice(voice_name)
            if voice_info["success"]:
                results["speaker2"] = voice_info["voice"]["voice_id"]
                results["logs"].append(f"Speaker2 使用默认音色: {voice_info['voice']['name']}")
            else:
                results["logs"].append(f"错误: {voice_info['error']}")
                return {"success": False, "error": voice_info['error']}

        elif speaker2_config["type"] == "custom":
            audio_file = speaker2_config.get("audio_file")
            if not audio_file:
                return {"success": False, "error": "Speaker2 未提供音频文件", "logs": results["logs"]}

            clone_result = self.clone_custom_voice(audio_file, api_key=api_key)
            if clone_result["success"]:
                results["speaker2"] = clone_result["voice_id"]
                results["trace_ids"]["speaker2_upload"] = clone_result.get("upload_trace_id")
                results["trace_ids"]["speaker2_clone"] = clone_result.get("clone_trace_id")
                results["logs"].append(f"✅ Speaker2 音色克隆成功: {clone_result['voice_id']}")
            else:
                # 音色克隆失败，记录详细错误，并使用默认音色作为降级方案
                error_detail = clone_result.get('error', '未知错误')
                results["logs"].append(f"❌ Speaker2 音色克隆失败: {error_detail}")

                # 如果是时长不足的错误，提供更明确的提示
                if 'duration' in clone_result:
                    results["logs"].append(f"⚠️  音频时长仅 {clone_result['duration']:.2f} 秒，需要至少 10 秒")

                results["logs"].append(f"⚠️  降级使用默认音色 Max（男声）")

                # 降级到默认音色
                voice_info = self.get_default_voice("max")
                if voice_info["success"]:
                    results["speaker2"] = voice_info["voice"]["voice_id"]
                else:
                    return {"success": False, "error": "无法使用默认音色作为降级方案", "logs": results["logs"]}

        results["success"] = True
        return results


# 单例实例
voice_manager = VoiceManager()
