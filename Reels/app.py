"""
FastAPI 메인 애플리케이션 (동기 방식)
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import shutil
from pathlib import Path
import uuid
import tempfile

from models import ReelsConfig
from reels_engine import generate_reels

# FastAPI 앱 생성
app = FastAPI(
    title="여행 릴스 자동 생성 API",
    description="사용자가 업로드한 여행 사진으로 자동으로 Instagram Reels를 생성합니다.",
    version="2.0.0 (동기 방식)"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 설정
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_PHOTOS = 50


def validate_image_file(file: UploadFile) -> bool:
    """이미지 파일 유효성 검사"""
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False
    
    if not file.content_type or not file.content_type.startswith("image/"):
        return False
    
    return True


@app.get("/")
async def root():
    """API 루트"""
    return {
        "message": "여행 릴스 자동 생성 API (동기 방식)",
        "version": "2.0.0",
        "docs": "/docs"
    }


@app.post("/api/reels/create")
async def create_reels(
    photos: List[UploadFile] = File(..., description="업로드할 사진 파일들"),
    duration_per_photo: int = Form(default=3, ge=1, le=10),
    enable_transitions: bool = Form(default=True),
    enable_ken_burns: bool = Form(default=True),
    enable_text_overlay: bool = Form(default=True),
    sort_by_time: bool = Form(default=True),
    # 동적 효과 옵션
    effect_intensity: str = Form(default="medium", description="효과 강도 (low/medium/high)"),
    enable_rotation: bool = Form(default=False, description="회전 효과 활성화"),
    transition_style: str = Form(default="fade", description="전환 효과 스타일 (fade/slide/zoom/random)"),
    ken_burns_style: str = Form(default="random", description="Ken Burns 스타일 (zoom_in/zoom_out/pan/diagonal/random)"),
    # AI 기능 옵션
    enable_ai_analysis: bool = Form(default=False, description="AI 이미지 분석 활성화"),
    enable_ai_captions: bool = Form(default=False, description="AI 캡션 생성 활성화"),
    enable_ai_subtitles: bool = Form(default=False, description="AI 스토리 자막 활성화 (텍스트)"),
    enable_narration: bool = Form(default=False, description="음성 나레이션 활성화 (오디오)"),
    narration_voice: str = Form(default="nova", description="나레이션 음성 (alloy/echo/fable/onyx/nova/shimmer)"),
    # 오디오 옵션
    background_music: Optional[UploadFile] = File(None, description="배경음악 파일"),
    enable_beat_sync: bool = Form(default=False, description="음악 비트에 맞춰 전환"),
    # OpenAI Sora 옵션
    # OpenAI Sora 옵션 - 제거됨
):
    """
    사진 업로드 및 릴스 생성 (동기 방식)
    
    업로드된 사진으로 즉시 릴스를 생성하고 파일을 반환합니다.
    
    - **photos**: 업로드할 사진 파일들 (최대 50장)
    - **duration_per_photo**: 사진당 지속 시간 (1-10초)
    - **enable_transitions**: 전환 효과 활성화
    - **enable_ken_burns**: Ken Burns 효과 활성화
    - **enable_text_overlay**: 텍스트 오버레이 활성화
    - **sort_by_time**: 촬영 시간순 정렬
    - **effect_intensity**: 효과 강도 (low/medium/high)
    - **enable_rotation**: 회전 효과 활성화
    - **transition_style**: 전환 효과 스타일 (fade/slide/zoom/random)
    - **ken_burns_style**: Ken Burns 스타일 (zoom_in/zoom_out/pan/diagonal/random)
    - **enable_ai_analysis**: AI 이미지 분석 활성화 (OpenAI API 키 필요)
    - **enable_ai_captions**: AI 캡션 생성 활성화
    - **enable_ai_subtitles**: AI 스토리 자막 활성화 (화면에 텍스트 표시)
    - **enable_narration**: 음성 나레이션 활성화 (OpenAI TTS, 오디오 추가)
    - **narration_voice**: 나레이션 음성 선택
    """
    
    # 사진 개수 검증
    if len(photos) == 0:
        raise HTTPException(status_code=400, detail="최소 1장 이상의 사진이 필요합니다.")
    
    if len(photos) > MAX_PHOTOS:
        raise HTTPException(
            status_code=400, 
            detail=f"최대 {MAX_PHOTOS}장까지 업로드 가능합니다."
        )
    
    # 파일 유효성 검증
    for photo in photos:
        if not validate_image_file(photo):
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 이미지 파일: {photo.filename}"
            )
    
    # 임시 디렉토리 생성
    temp_id = str(uuid.uuid4())
    temp_input_dir = Path(tempfile.gettempdir()) / "reels_input" / temp_id
    temp_output_dir = Path(tempfile.gettempdir()) / "reels_output" / temp_id
    temp_input_dir.mkdir(parents=True, exist_ok=True)
    temp_output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 파일 저장
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo.file, buffer)
        
        # 배경음악 저장
        bg_music_path = None
        if background_music:
            bg_music_path = temp_input_dir / background_music.filename
            with open(bg_music_path, "wb") as buffer:
                shutil.copyfileobj(background_music.file, buffer)
        
        # 릴스 생성 설정
        config = ReelsConfig(
            duration_per_photo=duration_per_photo,
            enable_transitions=enable_transitions,
            enable_ken_burns=enable_ken_burns,
            enable_text_overlay=enable_text_overlay,
            sort_by_time=sort_by_time,
            # 동적 효과 설정
            effect_intensity=effect_intensity,
            enable_rotation=enable_rotation,
            transition_style=transition_style,
            ken_burns_style=ken_burns_style,
            # AI 기능 설정
            enable_ai_analysis=enable_ai_analysis,
            enable_ai_captions=enable_ai_captions,
            enable_ai_subtitles=enable_ai_subtitles,
            enable_narration=enable_narration,
            narration_voice=narration_voice,
            # 오디오 설정
            background_music_path=str(bg_music_path) if bg_music_path else None,
            enable_beat_sync=enable_beat_sync,
            # OpenAI Sora 설정
            # OpenAI Sora 설정 - 제거됨
        )
        
        # 출력 파일 경로
        output_file = temp_output_dir / "reels.mp4"
        
        # 릴스 생성 (동기 실행)
        success = generate_reels(
            input_dir=temp_input_dir,
            output_path=output_file,
            config=config,
            progress_callback=None  # 동기 방식에서는 진행률 콜백 불필요
        )
        
        if not success or not output_file.exists():
            raise HTTPException(status_code=500, detail="릴스 생성에 실패했습니다.")
        
        # 파일 반환
        return FileResponse(
            path=output_file,
            media_type="video/mp4",
            filename=f"travel_reels_{temp_id[:8]}.mp4",
            background=None  # 파일 전송 후 자동 삭제하지 않음
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"릴스 생성 중 오류 발생: {str(e)}\n\n{error_detail}"
        )
    finally:
        # 임시 파일 정리 (선택적)
        # 실제 프로덕션에서는 백그라운드 작업으로 정리하거나
        # 일정 시간 후 삭제하는 것이 좋습니다
        pass


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "mode": "synchronous"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
