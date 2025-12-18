"""
애플리케이션 설정 관리
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 기본 디렉토리
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "output")
JOBS_DIR = BASE_DIR / os.getenv("JOBS_DIR", "jobs")

# 디렉토리 생성
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
JOBS_DIR.mkdir(exist_ok=True)

# 파일 업로드 설정
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE", "100"))  # MB
MAX_PHOTOS = int(os.getenv("MAX_PHOTOS", "50"))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# 릴스 기본 설정
DEFAULT_REELS_CONFIG = {
    "duration_per_photo": 3,  # 초
    "target_size": (1920, 1080),  # 9:16 비율 (FHD)
    "fps": 30,
    "codec": "libx264",
    "audio_codec": "aac",
    "enable_transitions": True,
    "enable_ken_burns": True,
    "enable_text_overlay": True,
}

# 작업 설정
JOB_CLEANUP_HOURS = int(os.getenv("JOB_CLEANUP_HOURS", "24"))  # 완료 후 파일 보관 시간
