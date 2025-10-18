"""
配置管理模块
管理 API Key、默认音色、BGM 路径等配置常量
"""

import os

# ========== API Keys ==========
# 统一 API Key（文本、TTS、音色克隆、图像生成都使用同一个）
MINIMAX_API_KEY = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJHcm91cE5hbWUiOiIvIiwiVXNlck5hbWUiOiLlhq_pm68iLCJBY2NvdW50IjoiIiwiU3ViamVjdElEIjoiMTY4NjgzMzY3NzA0Njc4MCIsIlBob25lIjoiMTg4MTE0NDU3MjgiLCJHcm91cElEIjoiMTY4NjgzMzY3NzM2NTQ1OSIsIlBhZ2VOYW1lIjoiIiwiTWFpbCI6IjE3ODk5ODExMTNAcXEuY29tIiwiQ3JlYXRlVGltZSI6IjIwMjUtMDItMjEgMTg6MjA6MTciLCJUb2tlblR5cGUiOjEsImlzcyI6Im1pbmltYXgifQ.fxmF-4CPd3efpqdJImkuwHC4c6Ig91PJ-HI0Hn_U1gL80mA5Ku_uLXP7xwflpp5DtCf8C1tj48Itdbi_bLoh9gQ0ZHnNpDe_vEQqXBwpVe9CKnqkNeeneVa3lKCRW2iCzAS4CoucTBBq9pDpLZKI7bsXVOq6ONxjaOa4LPkMv7EjLZVzyQcDlKuVKU8_fdiPiWEa0cztILtkTBqYeUJ1sZnh4j0ncuve17ky0-q4m-MyVahLJPJIektp_Rnd95xZYqS2fn0874BSfihMKlT2xaZUhJ_hpYcVw-fSEKzR7T5nOmUDTTKXYHlqn0sLzcetz4AtdJ8zGicVoALqnpVLtA"

# 保留旧的变量名以兼容现有代码
MINIMAX_TEXT_API_KEY = MINIMAX_API_KEY
MINIMAX_OTHER_API_KEY = MINIMAX_API_KEY

# ========== 默认音色配置 ==========
DEFAULT_VOICES = {
    "mini": {
        "name": "Mini",
        "gender": "female",
        "voice_id": "moss_audio_aaa1346a-7ce7-11f0-8e61-2e6e3c7ee85d",
        "description": "女声 - 活泼亲切"
    },
    "max": {
        "name": "Max",
        "gender": "male",
        "voice_id": "moss_audio_ce44fc67-7ce3-11f0-8de5-96e35d26fb85",
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
WELCOME_VOICE_ID = DEFAULT_VOICES["mini"]["voice_id"]  # 使用 Mini 音色

# ========== MiniMax API 端点配置 ==========
MINIMAX_API_BASE = "https://api.minimaxi.com"
MINIMAX_API_ENDPOINTS = {
    "text_completion": "https://api.minimaxi.com/v1/text/chatcompletion_v2",
    "tts": "https://api.minimaxi.com/v1/t2a_v2",
    "voice_clone": "https://api.minimax.chat/v1/voice_clone",
    "file_upload": "https://api.minimax.chat/v1/files/upload",
    "image_generation": "https://api.minimaxi.com/v1/image_generation"
}

# ========== 模型配置 ==========
MODELS = {
    "text": "MiniMax-M1",
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
    "image_generation": 60
}

# ========== 文件路径配置 ==========
UPLOAD_DIR = os.path.join(BASE_DIR, "backend", "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "backend", "outputs")

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
