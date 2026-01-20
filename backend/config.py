"""
配置管理模块
管理 API Key、默认音色、BGM 路径等配置常量
"""

import os
import dotenv

dotenv.load_dotenv()

# ========== API Keys ==========
# 统一 API Key（文本、TTS、音色克隆、图像生成都使用同一个）
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")

# 保留旧的变量名以兼容现有代码
MINIMAX_TEXT_API_KEY = MINIMAX_API_KEY
MINIMAX_OTHER_API_KEY = MINIMAX_API_KEY

# ========== 默认音色配置 ==========
DEFAULT_VOICES = {
    "mini": {
        "name": "Mini",
        "gender": "female",
        "voice_id": "Chinese (Mandarin)_Gentle_Senior",
        "description": "女声 - 活泼亲切"
    },
    "max": {
        "name": "Max",
        "gender": "male",
        "voice_id": "Boyan_new_platform",
        "description": "男声 - 稳重专业"
    }
}

# ========== BGM 配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BGM_DIR = os.path.join(BASE_DIR, "assets")

BGM_FILES = {
    "bgm01": os.path.join(BGM_DIR, "bgm01.wav"),
    "bgm02": os.path.join(BGM_DIR, "bgm02.wav")
}

# 欢迎语音配置
WELCOME_TEXT = "欢迎收听MiniMax AI播客节目"
# WELCOME_VOICE_ID = DEFAULT_VOICES["mini"]["voice_id"]  # 直接使用设定的speak1音色

# ========== MiniMax API 端点配置 ==========
MINIMAX_API_BASE = "https://api.minimax.io"
MINIMAX_API_ENDPOINTS = {
    "text_completion": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    "tts": "https://api.minimaxi.com/v1/t2a_v2",
    "voice_clone": "https://api.minimax.chat/v1/voice_clone",
    "file_upload": "https://api.minimax.chat/v1/files/upload",
    "image_generation": "https://api.minimaxi.com/v1/image_generation",
    "get_voice": "https://api.minimaxi.com/v1/get_voice"  # 查询可用音色列表
}

# ========== OpenAI 兼容客户端配置 ==========
# MiniMax 的 OpenAI API 兼容端点基础 URL
OPENAI_BASE_URL = "https://api.minimaxi.com/v1"

# ========== 模型配置 ==========
MODELS = {
    "text": "MiniMax-M2.1",
    "tts": "speech-2.5-hd-preview",
    "voice_clone": "speech-02-turbo",
    "image": "image-01-live"
}

# ========== 播客生成配置 ==========
PODCAST_CONFIG = {
    "target_duration_min": 3,  # 目标最短时长（分钟）
    "target_duration_max": 5,  # 目标最长时长（分钟）
    "style": "轻松幽默",
    "speakers": ["Speaker1", "Speaker2"]
}

# ========== 超时配置（秒）==========
TIMEOUTS = {
    "url_parsing": 30,
    "pdf_parsing": 30,
    "voice_clone": 60,
    "script_generation": 120,
    "tts_per_sentence": 30,
    "cover_prompt_generation": 60,  # 封面 Prompt 生成超时
    "image_generation": 90  # 图像生成超时（增加到90秒）
}

# ========== 文件路径配置 ==========
# BASE_DIR 已经是 backend 目录，无需再加 backend
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# 确保目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========== Voice ID 生成配置 ==========
VOICE_ID_CONFIG = {
    "prefix": "customVoice",
    "min_length": 8,
    "max_length": 256,
    "allowed_chars": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
}

# ========== TTS 音频配置 ==========
TTS_AUDIO_SETTINGS = {
    "sample_rate": 32000,
    "bitrate": 128000,
    "format": "mp3",
    "channel": 1
}

# ========== 图像生成配置 ==========
IMAGE_GENERATION_CONFIG = {
    "style_type": "漫画",
    "style_weight": 1,
    "aspect_ratio": "1:1",
    "prompt_optimizer": True,
    "n": 1
}

# ========== 日志配置 ==========
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
