"""
Pydantic 모델 정의
"""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class JobStatus(str, Enum):
    """작업 상태"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReelsConfig(BaseModel):
    """릴스 생성 설정"""
    duration_per_photo: int = Field(default=3, ge=1, le=10, description="사진당 지속 시간 (초)")
    enable_transitions: bool = Field(default=True, description="전환 효과 활성화")
    enable_ken_burns: bool = Field(default=True, description="Ken Burns 효과 활성화")
    enable_text_overlay: bool = Field(default=True, description="텍스트 오버레이 활성화")
    sort_by_time: bool = Field(default=True, description="촬영 시간순 정렬")
    
    # 동적 효과 설정
    effect_intensity: str = Field(default="medium", description="효과 강도 (low/medium/high)")
    enable_rotation: bool = Field(default=False, description="회전 효과 활성화")
    transition_style: str = Field(default="fade", description="전환 효과 스타일 (fade/slide/zoom/random/morph/glitch/circular/page_curl)")
    ken_burns_style: str = Field(default="random", description="Ken Burns 스타일 (zoom_in/zoom_out/pan/diagonal/random)")
    
    # 이징 함수 설정
    easing_function: str = Field(default="ease_in_out_cubic", description="이징 함수 (linear/ease_in_out_cubic/ease_in_out_sine/ease_out_back 등)")
    
    # 스마트 하이라이트 설정
    enable_smart_crop: bool = Field(default=False, description="얼굴 감지 기반 스마트 크롭 활성화")
    enable_adaptive_duration: bool = Field(default=False, description="중요도 기반 지속 시간 자동 조정")
    
    # 2.5D Parallax 설정
    enable_parallax: bool = Field(default=False, description="2.5D Parallax 효과 활성화")
    parallax_intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="Parallax 강도 (0.0 ~ 1.0)")
    
    # 색상 그레이딩 설정
    enable_color_grading: bool = Field(default=False, description="AI 기반 색상 그레이딩 활성화")
    
    # AI 기능 설정
    enable_ai_analysis: bool = Field(default=False, description="AI 이미지 분석 활성화")
    enable_ai_captions: bool = Field(default=False, description="AI 캡션 생성 활성화")
    enable_ai_subtitles: bool = Field(default=False, description="AI 스토리 자막 활성화")
    enable_ai_text_overlay: bool = Field(default=False, description="AI 생성 텍스트 오버레이 활성화")
    ai_text_style: str = Field(default="descriptive", description="AI 텍스트 스타일 (descriptive/poetic/simple)")
    enable_narration: bool = Field(default=False, description="음성 나레이션 활성화")
    narration_voice: str = Field(default="nova", description="나레이션 음성 (alloy/echo/fable/onyx/nova/shimmer)")
    
    # 오디오 설정
    background_music_path: Optional[str] = Field(None, description="배경음악 파일 경로")
    enable_beat_sync: bool = Field(default=False, description="비트 싱크 활성화")
    
    # OpenAI Sora 설정
    # OpenAI Sora 설정 - 제거됨
    
    # Stable Video Diffusion 설정
    enable_svd: bool = Field(default=False, description="Stable Video Diffusion 영상 생성 활성화 (무료)")
    svd_num_frames: int = Field(default=25, ge=14, le=25, description="SVD 프레임 수")
    svd_fps: int = Field(default=6, ge=4, le=30, description="SVD FPS")
    svd_motion_bucket_id: int = Field(default=127, ge=1, le=255, description="SVD 움직임 강도")
    
    # 고급 카메라 효과
    camera_style: str = Field(default="dynamic", description="카메라 스타일 (basic/dynamic/cinematic)")
    enable_3d_rotation: bool = Field(default=False, description="3D 회전 효과")
    enable_circular_motion: bool = Field(default=False, description="원형 움직임")
    enable_zoom_pan_combo: bool = Field(default=False, description="줌+팬 조합")
    enable_handheld: bool = Field(default=False, description="핸드헬드 흔들림")
    
    # 고급 전환 효과
    transition_variety: bool = Field(default=False, description="다양한 전환 효과 사용")
    enable_glitch: bool = Field(default=False, description="글리치 효과")
    
    # 시각 효과
    enable_vignette: bool = Field(default=False, description="비네팅 효과")
    color_grading: str = Field(default="none", description="색상 그레이딩 (none/cinematic/warm/cool/vintage)")
    enable_particles: bool = Field(default=False, description="파티클 효과")
    particle_type: str = Field(default="none", description="파티클 타입 (none/snow/rain/dust)")
    
    # 자동 하이라이트
    enable_auto_highlight: bool = Field(default=False, description="AI 자동 하이라이트")
    auto_speed_adjust: bool = Field(default=False, description="자동 속도 조절")



class JobResponse(BaseModel):
    """작업 생성 응답"""
    job_id: str = Field(..., description="작업 ID")
    status: JobStatus = Field(..., description="작업 상태")
    message: str = Field(..., description="응답 메시지")
    photo_count: int = Field(..., description="업로드된 사진 개수")


class JobStatusResponse(BaseModel):
    """작업 상태 조회 응답"""
    job_id: str = Field(..., description="작업 ID")
    status: JobStatus = Field(..., description="작업 상태")
    progress: int = Field(default=0, ge=0, le=100, description="진행률 (%)")
    message: str = Field(default="", description="상태 메시지")
    created_at: datetime = Field(..., description="작업 생성 시간")
    updated_at: datetime = Field(..., description="마지막 업데이트 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")
    error: Optional[str] = Field(None, description="에러 메시지")
    output_file: Optional[str] = Field(None, description="출력 파일 경로")
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")


class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
