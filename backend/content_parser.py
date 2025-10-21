"""
内容解析模块
支持网页解析（BeautifulSoup）和 PDF 解析（PyPDF2）
"""

import logging
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from typing import Dict, Any
from config import TIMEOUTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentParser:
    """内容解析器"""

    def parse_url(self, url: str) -> Dict[str, Any]:
        """
        解析网页内容

        Args:
            url: 网页 URL

        Returns:
            包含解析文本和日志的字典
        """
        logs = []
        logs.append(f"开始解析网址: {url}")

        try:
            # 发送 HTTP 请求，使用更真实的浏览器请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            response = requests.get(url, headers=headers, timeout=TIMEOUTS["url_parsing"], allow_redirects=True)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            logs.append(f"成功获取网页内容，状态码: {response.status_code}")

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 移除 script 和 style 标签
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()

            # 提取文本内容
            text = soup.get_text(separator='\n', strip=True)

            # 清理多余的空行
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            content = '\n'.join(lines)

            # 限制长度（防止内容过长）
            max_length = 10000
            if len(content) > max_length:
                content = content[:max_length] + "\n...(内容过长，已截断)"
                logs.append(f"内容过长，已截断至 {max_length} 字符")

            logs.append(f"成功提取文本，共 {len(content)} 字符")

            return {
                "success": True,
                "content": content,
                "logs": logs,
                "source": "url",
                "url": url
            }

        except requests.Timeout:
            error_msg = f"网页解析超时（{TIMEOUTS['url_parsing']}秒）"
            logs.append(f"错误: {error_msg}")
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "logs": logs,
                "source": "url"
            }

        except requests.RequestException as e:
            error_msg = f"网页请求失败: {str(e)}"
            logs.append(f"错误: {error_msg}")
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "logs": logs,
                "source": "url"
            }

        except Exception as e:
            error_msg = f"网页解析失败: {str(e)}"
            logs.append(f"错误: {error_msg}")
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "logs": logs,
                "source": "url"
            }

    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        解析 PDF 文件

        Args:
            pdf_path: PDF 文件路径

        Returns:
            包含解析文本和日志的字典
        """
        logs = []
        logs.append(f"开始解析 PDF: {pdf_path}")

        try:
            # 使用 PyPDF2 读取 PDF
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)

            logs.append(f"PDF 共 {num_pages} 页")

            # 提取所有页面的文本
            all_text = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text.strip():
                        all_text.append(text)
                        logs.append(f"成功提取第 {i + 1} 页内容")
                    else:
                        logs.append(f"警告: 第 {i + 1} 页无法提取文本（可能是扫描版）")
                except Exception as e:
                    logs.append(f"警告: 第 {i + 1} 页提取失败: {str(e)}")

            if not all_text:
                error_msg = "PDF 无法提取文本，可能是扫描版 PDF，不支持此格式"
                logs.append(f"错误: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "logs": logs,
                    "source": "pdf"
                }

            content = '\n'.join(all_text)

            # 限制长度
            max_length = 10000
            if len(content) > max_length:
                content = content[:max_length] + "\n...(内容过长，已截断)"
                logs.append(f"内容过长，已截断至 {max_length} 字符")

            logs.append(f"成功提取文本，共 {len(content)} 字符")

            return {
                "success": True,
                "content": content,
                "logs": logs,
                "source": "pdf",
                "num_pages": num_pages
            }

        except Exception as e:
            error_msg = f"PDF 解析失败: {str(e)}"
            logs.append(f"错误: {error_msg}")
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "logs": logs,
                "source": "pdf"
            }

    def merge_contents(self, text_input: str = "", url_content: str = "", pdf_content: str = "") -> str:
        """
        合并多种来源的内容

        Args:
            text_input: 用户输入的文本
            url_content: 网页解析的内容
            pdf_content: PDF 解析的内容

        Returns:
            合并后的文本
        """
        contents = []

        if text_input and text_input.strip():
            contents.append(f"【用户输入】\n{text_input.strip()}")

        if url_content and url_content.strip():
            contents.append(f"【网页内容】\n{url_content.strip()}")

        if pdf_content and pdf_content.strip():
            contents.append(f"【PDF 内容】\n{pdf_content.strip()}")

        if not contents:
            return "没有可用的内容"

        merged = "\n\n==========\n\n".join(contents)
        logger.info(f"成功合并 {len(contents)} 个来源的内容，总长度: {len(merged)}")

        return merged


# 单例实例
content_parser = ContentParser()
