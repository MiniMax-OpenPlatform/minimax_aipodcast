"""
AI 播客生成工具 - Flask 后端服务
支持 SSE 流式响应、并行任务处理
"""

import os
import sys
import uuid
import json
import logging
import threading
from flask import Flask, request, jsonify, Response, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import UPLOAD_DIR, OUTPUT_DIR, BGM_FILES
from content_parser import content_parser
from voice_manager import voice_manager
from podcast_generator import podcast_generator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask 应用
app = Flask(__name__)
CORS(app)

# 允许的文件扩展名
ALLOWED_AUDIO_EXTENSIONS = {'wav', 'mp3', 'flac', 'm4a', 'ogg'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}


def allowed_file(filename, allowed_extensions):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({"status": "ok", "message": "AI 播客生成服务运行中"})


@app.route('/api/default-voices', methods=['GET'])
def get_default_voices():
    """获取默认音色列表"""
    from config import DEFAULT_VOICES
    return jsonify({
        "success": True,
        "voices": DEFAULT_VOICES
    })


@app.route('/api/generate_podcast', methods=['POST'])
def generate_podcast():
    """
    生成播客接口（SSE 流式响应）

    请求参数:
    - text_input: 文本输入（可选）
    - url: 网址输入（可选）
    - pdf_file: PDF 文件（可选）
    - speaker1_type: "default" 或 "custom"
    - speaker1_voice_name: "mini" 或 "max"（default 时）
    - speaker1_audio: 音频文件（custom 时）
    - speaker2_type: "default" 或 "custom"
    - speaker2_voice_name: "mini" 或 "max"（default 时）
    - speaker2_audio: 音频文件（custom 时）
    """
    # 在请求上下文中提取所有数据
    session_id = str(uuid.uuid4())
    logger.info(f"开始生成播客，Session ID: {session_id}")

    # 提取 API Key
    user_api_key = request.form.get('api_key', '').strip()
    if not user_api_key:
        def error_gen():
            yield "data: " + json.dumps({
                "type": "error",
                "message": "未提供 API Key"
            }) + "\n\n"
        return Response(error_gen(), mimetype='text/event-stream')

    # 提取表单数据
    text_input = request.form.get('text_input', '').strip()
    url_input = request.form.get('url', '').strip()

    # 提取 PDF 文件
    pdf_file = None
    pdf_path = None
    if 'pdf_file' in request.files:
        pdf_file_obj = request.files['pdf_file']
        if pdf_file_obj and allowed_file(pdf_file_obj.filename, ALLOWED_PDF_EXTENSIONS):
            filename = secure_filename(pdf_file_obj.filename)
            pdf_path = os.path.join(UPLOAD_DIR, f"{session_id}_{filename}")
            pdf_file_obj.save(pdf_path)
            pdf_file = filename

    # 提取音色配置
    speaker1_type = request.form.get('speaker1_type', 'default')
    speaker1_voice_name = request.form.get('speaker1_voice_name', 'mini')
    speaker1_audio_path = None
    if speaker1_type == 'custom' and 'speaker1_audio' in request.files:
        audio_file = request.files['speaker1_audio']
        if audio_file and allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            filename = secure_filename(audio_file.filename)
            speaker1_audio_path = os.path.join(UPLOAD_DIR, f"{session_id}_speaker1_{filename}")
            audio_file.save(speaker1_audio_path)

    speaker2_type = request.form.get('speaker2_type', 'default')
    speaker2_voice_name = request.form.get('speaker2_voice_name', 'max')
    speaker2_audio_path = None
    if speaker2_type == 'custom' and 'speaker2_audio' in request.files:
        audio_file = request.files['speaker2_audio']
        if audio_file and allowed_file(audio_file.filename, ALLOWED_AUDIO_EXTENSIONS):
            filename = secure_filename(audio_file.filename)
            speaker2_audio_path = os.path.join(UPLOAD_DIR, f"{session_id}_speaker2_{filename}")
            audio_file.save(speaker2_audio_path)

    def generate():
        """SSE 生成器"""
        try:
            # Step 1: 解析输入内容
            yield f"data: {json.dumps({'type': 'progress', 'step': 'parsing_content', 'message': '正在解析输入内容...'})}\n\n"

            # 处理 PDF 文件
            pdf_content = ""
            if pdf_path:
                yield f"data: {json.dumps({'type': 'log', 'message': f'已上传 PDF: {pdf_file}'})}\n\n"

                pdf_result = content_parser.parse_pdf(pdf_path)
                if pdf_result["success"]:
                    pdf_content = pdf_result["content"]
                    for log in pdf_result["logs"]:
                        yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': pdf_result['error']})}\n\n"
                    return

            # 解析网址（如果提供）
            url_content = ""
            if url_input:
                yield f"data: {json.dumps({'type': 'log', 'message': f'开始解析网址: {url_input}'})}\n\n"

                url_result = content_parser.parse_url(url_input)
                if url_result["success"]:
                    url_content = url_result["content"]
                    for log in url_result["logs"]:
                        yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
                else:
                    # 发送友好的错误提示，但不中断流程
                    error_code = url_result.get('error_code', 'unknown')
                    yield f"data: {json.dumps({'type': 'url_parse_warning', 'message': url_result['error'], 'error_code': error_code})}\n\n"
                    for log in url_result["logs"]:
                        yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"
                    # 不返回，继续处理其他输入内容

            # 合并所有内容
            merged_content = content_parser.merge_contents(text_input, url_content, pdf_content)

            if not merged_content or merged_content == "没有可用的内容":
                yield f"data: {json.dumps({'type': 'error', 'message': '请至少提供一种输入内容（文本/网址/PDF）'})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'log', 'message': f'内容解析完成，共 {len(merged_content)} 字符'})}\n\n"

            # Step 2: 准备音色
            yield f"data: {json.dumps({'type': 'progress', 'step': 'preparing_voices', 'message': '正在准备音色...'})}\n\n"

            # Speaker1 配置
            speaker1_config = {"type": speaker1_type}

            if speaker1_type == 'default':
                speaker1_config["voice_name"] = speaker1_voice_name
            elif speaker1_type == 'custom':
                if speaker1_audio_path:
                    speaker1_config["audio_file"] = speaker1_audio_path
                    yield f"data: {json.dumps({'type': 'log', 'message': 'Speaker1 音频已上传'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Speaker1 选择自定义音色但未上传音频文件'})}\n\n"
                    return

            # Speaker2 配置
            speaker2_config = {"type": speaker2_type}

            if speaker2_type == 'default':
                speaker2_config["voice_name"] = speaker2_voice_name
            elif speaker2_type == 'custom':
                if speaker2_audio_path:
                    speaker2_config["audio_file"] = speaker2_audio_path
                    yield f"data: {json.dumps({'type': 'log', 'message': 'Speaker2 音频已上传'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Speaker2 选择自定义音色但未上传音频文件'})}\n\n"
                    return

            # 准备音色（可能涉及克隆）
            voices_result = voice_manager.prepare_voices(speaker1_config, speaker2_config, api_key=user_api_key)

            if not voices_result["success"]:
                yield f"data: {json.dumps({'type': 'error', 'message': voices_result['error']})}\n\n"
                return

            # 发送音色准备日志
            for log in voices_result["logs"]:
                yield f"data: {json.dumps({'type': 'log', 'message': log})}\n\n"

            # 发送音色克隆的 Trace ID
            for key, trace_id in voices_result.get("trace_ids", {}).items():
                if trace_id:
                    yield f"data: {json.dumps({'type': 'trace_id', 'api': key, 'trace_id': trace_id})}\n\n"

            speaker1_voice_id = voices_result["speaker1"]
            speaker2_voice_id = voices_result["speaker2"]

            # Step 3: 流式生成播客
            for event in podcast_generator.generate_podcast_stream(
                content=merged_content,
                speaker1_voice_id=speaker1_voice_id,
                speaker2_voice_id=speaker2_voice_id,
                session_id=session_id,
                api_key=user_api_key
            ):
                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            logger.error(f"播客生成失败: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': f'播客生成失败: {str(e)}'})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    """
    上传音频文件接口（用于录音功能）
    """
    try:
        if 'audio' not in request.files:
            return jsonify({"success": False, "error": "未提供音频文件"})

        audio_file = request.files['audio']
        if not audio_file:
            return jsonify({"success": False, "error": "音频文件为空"})

        # 生成文件名
        session_id = request.form.get('session_id', str(uuid.uuid4()))
        speaker = request.form.get('speaker', 'unknown')
        filename = f"{session_id}_{speaker}_{int(time.time())}.wav"
        file_path = os.path.join(UPLOAD_DIR, filename)

        audio_file.save(file_path)

        return jsonify({
            "success": True,
            "filename": filename,
            "path": file_path
        })

    except Exception as e:
        logger.error(f"音频上传失败: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/download/audio/<filename>', methods=['GET'])
def download_audio(filename):
    """下载音频文件"""
    try:
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"下载音频失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


@app.route('/download/script/<filename>', methods=['GET'])
def download_script(filename):
    """下载脚本文件"""
    try:
        return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"下载脚本失败: {str(e)}")
        return jsonify({"error": str(e)}), 404


@app.route('/download/cover', methods=['GET'])
def download_cover():
    """下载封面图片（从OSS代理下载）"""
    try:
        import requests
        cover_url = request.args.get('url')
        if not cover_url:
            return jsonify({"error": "未提供封面URL"}), 400

        # 从 OSS 获取图片
        response = requests.get(cover_url, timeout=30)
        response.raise_for_status()

        # 生成文件名
        import time
        filename = f"podcast_cover_{int(time.time())}.jpg"

        # 返回图片数据，设置下载头
        from flask import make_response
        resp = make_response(response.content)
        resp.headers['Content-Type'] = 'image/jpeg'
        resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return resp

    except Exception as e:
        logger.error(f"下载封面失败: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件（BGM等）"""
    # 简化 BGM 访问
    if filename == 'bgm01.wav':
        return send_file(BGM_FILES["bgm01"])
    elif filename == 'bgm02.wav':
        return send_file(BGM_FILES["bgm02"])
    return jsonify({"error": "File not found"}), 404


if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("🎙️  MiniMax AI 播客生成服务启动")
    logger.info(f"📁 上传目录: {UPLOAD_DIR}")
    logger.info(f"📁 输出目录: {OUTPUT_DIR}")
    logger.info("=" * 50)
    # 生产环境关闭 debug 模式，避免自动重启导致 SSE 连接中断
    app.run(debug=False, host='0.0.0.0', port=5001, threaded=True)
