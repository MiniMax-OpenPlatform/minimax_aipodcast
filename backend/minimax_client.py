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

    def _get_headers(self, api_type: str = "other", api_key: Optional[str] = None) -> Dict[str, str]:
        """
        获取请求头

        Args:
            api_type: "text" 或 "other"
            api_key: 可选的自定义 API Key，如果不提供则使用默认配置

        Returns:
            请求头字典
        """
        if api_key:
            # 使用用户提供的 API Key
            key = api_key
        else:
            # 使用配置文件中的默认 API Key
            key = self.text_api_key if api_type == "text" else self.other_api_key

        return {
            "Authorization": f"Bearer {key}",
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

    def generate_script_stream(self, content: str, duration_min: int = 3, duration_max: int = 5, api_key: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """
        流式生成播客脚本

        Args:
            content: 解析后的内容文本
            duration_min: 目标最短时长（分钟）
            duration_max: 目标最长时长（分钟）
            api_key: 可选的自定义 API Key

        Yields:
            包含脚本 chunk 和 trace_id 的字典
        """
        logger.info(f"开始生成播客脚本，内容长度: {len(content)} 字符，目标时长: {duration_min}-{duration_max} 分钟")

        # 文本模型使用用户提供的 API Key
        url = self.endpoints["text_completion"]
        headers = self._get_headers("text", api_key=api_key)

        # 构建 prompt
        prompt = f"""你是一个专业的播客脚本编写助手。请基于以下材料，生成一段 {duration_min}-{duration_max} 分钟的双人播客对话脚本。

要求：
1. 对话风格：轻松幽默，自然流畅
2. 说话人：Speaker1（主持人，引导话题）和 Speaker2（嘉宾，深度分析）
3. 文本要自然，包含适当的重复、语气词、停顿等真人对话特征
4. 每句话单独一行，格式为：Speaker1: 内容 或 Speaker2: 内容
5. 开场白要吸引人，结尾要有总结
6. 不要有多余的说明文字，只输出对话内容
7. 对话内容中不能包含（笑）（停顿）（思考）等动作、心理活动或场景描述，只生成纯对话文本

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

        logger.info(f"发送脚本生成请求到: {url}")
        logger.info(f"请求模型: {self.models['text']}")

        trace_id = None
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=TIMEOUTS["script_generation"]
            )

            # 立即提取 Trace ID（即使失败也要记录）
            trace_id = self._extract_trace_id(response)

            logger.info(f"脚本生成响应状态码: {response.status_code}")

            response.raise_for_status()

            logger.info("开始流式读取脚本内容...")

            # 流式读取响应
            chunk_count = 0
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
                                    chunk_count += 1
                                    if chunk_count % 10 == 0:
                                        logger.info(f"已接收 {chunk_count} 个脚本 chunk")
                                    yield {
                                        "type": "script_chunk",
                                        "content": content_chunk,
                                        "trace_id": trace_id
                                    }
                        except json.JSONDecodeError as je:
                            logger.warning(f"JSON 解析失败: {line[:100]}")
                            continue

            logger.info(f"脚本生成完成，共接收 {chunk_count} 个 chunk")

            # 完成信号
            yield {
                "type": "script_complete",
                "trace_id": trace_id
            }

        except requests.exceptions.Timeout:
            error_msg = f"脚本生成超时（{TIMEOUTS['script_generation']}秒）"
            logger.error(error_msg)
            yield {
                "type": "error",
                "message": error_msg,
                "trace_id": trace_id
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"脚本生成网络请求失败: {str(e)}"
            logger.error(error_msg)
            # 尝试从异常中提取 Trace ID
            if trace_id is None and hasattr(e, 'response') and e.response is not None:
                trace_id = self._extract_trace_id(e.response)
            yield {
                "type": "error",
                "message": error_msg,
                "trace_id": trace_id
            }
        except Exception as e:
            error_msg = f"脚本生成失败: {str(e)}"
            logger.error(error_msg)
            logger.exception("详细错误信息:")
            yield {
                "type": "error",
                "message": error_msg,
                "trace_id": trace_id
            }

    def synthesize_speech_stream(self, text: str, voice_id: str, api_key: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        """
        流式语音合成

        Args:
            text: 要合成的文本
            voice_id: 音色 ID
            api_key: 可选的自定义 API Key

        Yields:
            包含音频 chunk 和 trace_id 的字典
        """
        url = self.endpoints["tts"]
        headers = self._get_headers("other", api_key=api_key)

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

        trace_id = None
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                stream=True,
                timeout=TIMEOUTS["tts_per_sentence"]
            )

            # 立即提取 Trace ID（即使失败也要记录）
            trace_id = self._extract_trace_id(response)

            response.raise_for_status()

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
            # 尝试从异常中提取 Trace ID
            if trace_id is None and hasattr(e, 'response') and e.response is not None:
                trace_id = self._extract_trace_id(e.response)

            yield {
                "type": "error",
                "message": f"语音合成失败: {str(e)}",
                "trace_id": trace_id
            }

    def clone_voice(self, audio_file_path: str, voice_id: str, sample_text: str = "您好，我是客户经理李娜。", api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        音色克隆

        Args:
            audio_file_path: 音频文件路径
            voice_id: 自定义音色 ID
            sample_text: 示例文本
            api_key: 可选的自定义 API Key

        Returns:
            包含 voice_id 和 trace_id 的字典
        """
        # Step 1: 上传音频文件
        upload_url = self.endpoints["file_upload"]
        key_to_use = api_key if api_key else self.other_api_key
        headers_upload = {
            "Authorization": f"Bearer {key_to_use}"
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
            headers_clone = self._get_headers("other", api_key=api_key)

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

    def generate_cover_image(self, content_summary: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        生成播客封面图

        Args:
            content_summary: 内容摘要
            api_key: 可选的自定义 API Key

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

        text_trace_id = None
        try:
            # Step 1: 调用 M2 生成 prompt（文本模型使用用户提供的 API Key）
            logger.info("开始生成封面图 Prompt...")
            url_text = self.endpoints["text_completion"]
            headers_text = self._get_headers("text", api_key=api_key)

            payload_text = {
                "model": self.models["text"],
                "messages": [
                    {"role": "system", "name": "MiniMax AI"},
                    {"role": "user", "content": prompt_generation_prompt}
                ],
                "stream": False
            }

            logger.info(f"发送 Prompt 生成请求到: {url_text}")
            response_text = requests.post(
                url_text,
                headers=headers_text,
                json=payload_text,
                timeout=30
            )

            # 立即提取 Trace ID
            text_trace_id = self._extract_trace_id(response_text)
            logger.info(f"Prompt 生成响应状态码: {response_text.status_code}")

            response_text.raise_for_status()

            text_result = response_text.json()
            image_prompt = text_result.get("choices", [{}])[0].get("message", {}).get("content", "")

            logger.info(f"生成的图片 Prompt: {image_prompt}")

            if not image_prompt:
                image_prompt = "一男一女两个人坐在播客录音室里，漫画风格"
                logger.info(f"使用默认 Prompt: {image_prompt}")

            # Step 2: 调用文生图 API
            logger.info("开始生成封面图...")
            url_image = self.endpoints["image_generation"]
            headers_image = self._get_headers("other", api_key=api_key)

            payload_image = {
                "model": self.models["image"],
                "prompt": image_prompt,
                "aspect_ratio": IMAGE_GENERATION_CONFIG["aspect_ratio"],
                "response_format": "url",
                "n": IMAGE_GENERATION_CONFIG["n"],
                "prompt_optimizer": IMAGE_GENERATION_CONFIG["prompt_optimizer"],
                "style": {
                    "style_type": IMAGE_GENERATION_CONFIG["style_type"],
                    "style_weight": IMAGE_GENERATION_CONFIG["style_weight"]
                }
            }

            logger.info(f"图像生成 API: {url_image}")
            logger.info(f"图像生成请求 payload: {payload_image}")

            response_image = requests.post(
                url_image,
                headers=headers_image,
                json=payload_image,
                timeout=TIMEOUTS["image_generation"]
            )

            # 立即提取 Trace ID（即使请求失败也要记录）
            image_trace_id = self._extract_trace_id(response_image)

            logger.info(f"图像生成响应状态码: {response_image.status_code}")
            logger.info(f"图像生成响应内容前500字符: {response_image.text[:500]}")

            response_image.raise_for_status()
            logger.info("图像生成请求状态检查通过")

            image_result = response_image.json()

            logger.info(f"图像生成完整响应: {image_result}")

            # 检查 base_resp.status_code
            base_resp = image_result.get("base_resp", {})
            if base_resp.get("status_code") != 0:
                error_msg = base_resp.get("status_msg", "未知错误")
                logger.error(f"API 返回错误状态: status_code={base_resp.get('status_code')}, msg={error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "message": f"封面生成失败: {error_msg}",
                    "text_trace_id": text_trace_id,
                    "image_trace_id": image_trace_id
                }

            # 检查是否有 data 字段和 image_urls
            data = image_result.get("data", {})
            if not data or "image_urls" not in data:
                logger.error(f"API 响应缺少 data.image_urls 字段: {image_result}")
                return {
                    "success": False,
                    "error": f"API 响应格式错误，缺少 image_urls",
                    "message": f"封面生成失败: API 响应格式错误",
                    "text_trace_id": text_trace_id,
                    "image_trace_id": image_trace_id
                }

            # 获取第一张图片 URL
            image_urls = data.get("image_urls", [])
            if not image_urls or len(image_urls) == 0:
                logger.error(f"API 返回的 image_urls 为空: {image_result}")
                return {
                    "success": False,
                    "error": "图片生成失败，image_urls 为空",
                    "message": "封面生成失败: 未返回图片 URL",
                    "text_trace_id": text_trace_id,
                    "image_trace_id": image_trace_id
                }

            image_url = image_urls[0]
            logger.info(f"成功获取封面图 URL: {image_url}")

            return {
                "success": True,
                "image_url": image_url,
                "prompt": image_prompt,
                "text_trace_id": text_trace_id,
                "image_trace_id": image_trace_id,
                "message": "封面生成成功"
            }

        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(f"Cover image generation error: {error_msg}")

            # 尝试从异常中提取 response 对象
            image_trace_id = None
            if hasattr(e, 'response') and e.response is not None:
                image_trace_id = self._extract_trace_id(e.response)

            return {
                "success": False,
                "error": error_msg,
                "message": f"封面生成失败: {error_msg}",
                "text_trace_id": text_trace_id if 'text_trace_id' in locals() else None,
                "image_trace_id": image_trace_id
            }
        except Exception as e:
            error_msg = str(e) if str(e) else "未知错误"
            logger.error(f"Cover image generation error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "message": f"封面生成失败: {error_msg}",
                "text_trace_id": text_trace_id if 'text_trace_id' in locals() else None,
                "image_trace_id": None
            }


# 单例实例
minimax_client = MinimaxClient()
