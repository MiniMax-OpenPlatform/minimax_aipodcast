"""
MiniMax API 客户端封装
统一管理所有 MiniMax API 调用，包括 M2 文本模型、TTS、音色克隆、文生图
"""

import requests
import json
import logging
from typing import Iterator, Dict, Any, Optional
from config import (
    MINIMAX_TEXT_API_KEY,
    MINIMAX_OTHER_API_KEY,
    MINIMAX_API_ENDPOINTS,
    MODELS,
    TTS_AUDIO_SETTINGS,
    IMAGE_GENERATION_CONFIG,
    TIMEOUTS
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MinimaxClient:
    """MiniMax API 客户端"""

    def __init__(self):
        self.text_api_key = MINIMAX_TEXT_API_KEY
        self.other_api_key = MINIMAX_OTHER_API_KEY
        self.endpoints = MINIMAX_API_ENDPOINTS
        self.models = MODELS

    def _get_headers(self, api_type: str = "other") -> Dict[str, str]:
        """
        获取请求头

        Args:
            api_type: "text" 或 "other"

        Returns:
            请求头字典
        """
        api_key = self.text_api_key if api_type == "text" else self.other_api_key
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def _extract_trace_id(self, response: requests.Response) -> Optional[str]:
        """
        从响应中提取 Trace ID

        Args:
            response: requests 响应对象

        Returns:
            Trace ID 字符串
        """
        trace_id = response.headers.get("Trace-ID") or response.headers.get("Trace-Id")
        if trace_id:
            logger.info(f"Trace-ID: {trace_id}")
        return trace_id

    def generate_script_stream(self, content: str, duration_min: int = 3, duration_max: int = 5) -> Iterator[Dict[str, Any]]:
        """
        流式生成播客脚本

        Args:
            content: 解析后的内容文本
            duration_min: 目标最短时长（分钟）
            duration_max: 目标最长时长（分钟）

        Yields:
            包含脚本 chunk 和 trace_id 的字典
        """
        url = self.endpoints["text_completion"]
        headers = self._get_headers("text")

        # 构建 prompt
        prompt = f"""你是一个专业的播客脚本编写助手。请基于以下材料，生成一段 {duration_min}-{duration_max} 分钟的双人播客对话脚本。

要求：
1. 对话风格：轻松幽默，自然流畅
2. 说话人：Speaker1（主持人，引导话题）和 Speaker2（嘉宾，深度分析）
3. 文本要自然，包含适当的重复、语气词、停顿等真人对话特征
4. 每句话单独一行，格式为：Speaker1: 内容 或 Speaker2: 内容
5. 开场白要吸引人，结尾要有总结
6. 不要有多余的说明文字，只输出对话内容

材料内容：
{content}

请开始生成播客脚本："""

        payload = {
            "model": self.models["text"],
            "messages": [
                {"role": "system", "name": "MiniMax AI"},
                {"role": "user", "content": prompt}
            ],
            "stream": True
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=TIMEOUTS["script_generation"]
            )
            response.raise_for_status()

            # 提取 Trace ID
            trace_id = self._extract_trace_id(response)

            # 流式读取响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data:'):
                        try:
                            data = json.loads(line[5:].strip())
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content_chunk = delta.get('content', '')
                                if content_chunk:
                                    yield {
                                        "type": "script_chunk",
                                        "content": content_chunk,
                                        "trace_id": trace_id
                                    }
                        except json.JSONDecodeError:
                            continue

            # 完成信号
            yield {
                "type": "script_complete",
                "trace_id": trace_id
            }

        except Exception as e:
            logger.error(f"Script generation error: {str(e)}")
            yield {
                "type": "error",
                "message": f"脚本生成失败: {str(e)}"
            }

    def synthesize_speech_stream(self, text: str, voice_id: str) -> Iterator[Dict[str, Any]]:
        """
        流式语音合成

        Args:
            text: 要合成的文本
            voice_id: 音色 ID

        Yields:
            包含音频 chunk 和 trace_id 的字典
        """
        url = self.endpoints["tts"]
        headers = self._get_headers("other")

        payload = {
            "model": self.models["tts"],
            "text": text,
            "stream": True,
            "voice_setting": {
                "voice_id": voice_id,
                "speed": 1,
                "vol": 1,
                "pitch": 0
            },
            "audio_setting": TTS_AUDIO_SETTINGS,
            "subtitle_enable": False
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=TIMEOUTS["tts_per_sentence"]
            )
            response.raise_for_status()

            # 提取 Trace ID
            trace_id = self._extract_trace_id(response)

            # 流式读取音频 chunk
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data:'):
                        try:
                            data = json.loads(line_str[5:].strip())
                            if "data" in data and "extra_info" not in data:
                                if "audio" in data["data"]:
                                    audio_hex = data["data"]["audio"]
                                    yield {
                                        "type": "audio_chunk",
                                        "audio": audio_hex,
                                        "trace_id": trace_id
                                    }
                        except json.JSONDecodeError:
                            continue

            # 完成信号
            yield {
                "type": "tts_complete",
                "trace_id": trace_id
            }

        except Exception as e:
            logger.error(f"TTS error: {str(e)}")
            yield {
                "type": "error",
                "message": f"语音合成失败: {str(e)}"
            }

    def clone_voice(self, audio_file_path: str, voice_id: str, sample_text: str = "您好，我是客户经理李娜。") -> Dict[str, Any]:
        """
        音色克隆

        Args:
            audio_file_path: 音频文件路径
            voice_id: 自定义音色 ID
            sample_text: 示例文本

        Returns:
            包含 voice_id 和 trace_id 的字典
        """
        # Step 1: 上传音频文件
        upload_url = self.endpoints["file_upload"]
        headers_upload = {
            "Authorization": f"Bearer {self.other_api_key}"
        }

        try:
            with open(audio_file_path, 'rb') as f:
                files = {'file': f}
                data = {'purpose': 'voice_clone'}
                response_upload = requests.post(
                    upload_url,
                    headers=headers_upload,
                    data=data,
                    files=files,
                    timeout=30
                )
                response_upload.raise_for_status()
                upload_trace_id = self._extract_trace_id(response_upload)

                upload_result = response_upload.json()
                file_id = upload_result.get("file", {}).get("file_id")

                if not file_id:
                    raise Exception("文件上传失败，未获取到 file_id")

            # Step 2: 调用音色克隆 API
            clone_url = self.endpoints["voice_clone"]
            headers_clone = self._get_headers("other")

            payload = {
                "file_id": file_id,
                "voice_id": voice_id,
                "text": sample_text,
                "model": self.models["voice_clone"]
            }

            response_clone = requests.post(
                clone_url,
                headers=headers_clone,
                json=payload,
                timeout=TIMEOUTS["voice_clone"]
            )
            response_clone.raise_for_status()
            clone_trace_id = self._extract_trace_id(response_clone)

            result = response_clone.json()

            return {
                "success": True,
                "voice_id": voice_id,
                "upload_trace_id": upload_trace_id,
                "clone_trace_id": clone_trace_id,
                "message": "音色克隆成功"
            }

        except Exception as e:
            logger.error(f"Voice clone error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"音色克隆失败: {str(e)}"
            }

    def generate_cover_image(self, content_summary: str) -> Dict[str, Any]:
        """
        生成播客封面图

        Args:
            content_summary: 内容摘要

        Returns:
            包含图片 URL 和 trace_id 的字典
        """
        # Step 1: 生成图片 prompt
        prompt_generation_prompt = f"""基于以下播客内容摘要，生成一个简洁的图片描述 prompt。

要求：
1. 图片风格：漫画风格
2. 主角：一男一女两个人
3. 场景：播客录音室或相关场景
4. 描述要简洁直观，30字以内

播客内容摘要：
{content_summary}

请直接输出图片描述 prompt（不要有多余说明）："""

        try:
            # 调用 M2 生成 prompt
            url_text = self.endpoints["text_completion"]
            headers_text = self._get_headers("text")

            payload_text = {
                "model": self.models["text"],
                "messages": [
                    {"role": "system", "name": "MiniMax AI"},
                    {"role": "user", "content": prompt_generation_prompt}
                ],
                "stream": False
            }

            response_text = requests.post(
                url_text,
                headers=headers_text,
                json=payload_text,
                timeout=30
            )
            response_text.raise_for_status()
            text_trace_id = self._extract_trace_id(response_text)

            text_result = response_text.json()
            image_prompt = text_result.get("choices", [{}])[0].get("message", {}).get("content", "")

            if not image_prompt:
                image_prompt = "一男一女两个人坐在播客录音室里，漫画风格"

            # Step 2: 调用文生图 API
            url_image = self.endpoints["image_generation"]
            headers_image = self._get_headers("other")

            payload_image = {
                "model": self.models["image"],
                "prompt": image_prompt,
                "style_type": IMAGE_GENERATION_CONFIG["style_type"],
                "style_weight": IMAGE_GENERATION_CONFIG["style_weight"],
                "aspect_ratio": IMAGE_GENERATION_CONFIG["aspect_ratio"],
                "prompt_optimizer": IMAGE_GENERATION_CONFIG["prompt_optimizer"],
                "n": IMAGE_GENERATION_CONFIG["n"],
                "response_format": "url"
            }

            response_image = requests.post(
                url_image,
                headers=headers_image,
                json=payload_image,
                timeout=TIMEOUTS["image_generation"]
            )
            response_image.raise_for_status()
            image_trace_id = self._extract_trace_id(response_image)

            image_result = response_image.json()
            image_url = image_result.get("data", [{}])[0].get("url", "")

            return {
                "success": True,
                "image_url": image_url,
                "prompt": image_prompt,
                "text_trace_id": text_trace_id,
                "image_trace_id": image_trace_id,
                "message": "封面生成成功"
            }

        except Exception as e:
            logger.error(f"Cover image generation error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"封面生成失败: {str(e)}"
            }


# 单例实例
minimax_client = MinimaxClient()
