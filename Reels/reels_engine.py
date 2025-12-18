"""
릴스 생성 엔진 (리팩토링 버전)
기존 main.py를 모듈화하여 API에서 호출 가능하도록 변경
"""
import os
from pathlib import Path
from typing import List, Callable, Optional, Dict, Any
from moviepy import *
from PIL import Image
import concurrent.futures

from utils import sort_photos_by_time, validate_image, extract_exif_data, format_datetime_korean
from models import ReelsConfig

# 새로운 기능 모듈
from easing_functions import get_easing_function
from face_detection import FaceDetector, adjust_duration_by_importance
from color_grading import apply_auto_color_grading
from advanced_transitions import (
    apply_morph_transition, 
    apply_glitch_transition, 
    apply_circular_wipe_transition, 
    apply_page_curl_transition
)
from audio_sync import detect_beats, adjust_clips_to_beats

# AI 서비스 (선택적 import)
try:
    from openai_service import OpenAIService
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("[경고] openai_service를 불러올 수 없습니다. AI 기능이 비활성화됩니다.")

def preprocess_image_task(args):
    """
    이미지 전처리 작업 (병렬 처리용)
    """
    img_path, target_size, output_dir = args
    try:
        from PIL import Image, ImageOps
        
        img = Image.open(img_path)
        
        # EXIF 회전 정보 처리
        img = ImageOps.exif_transpose(img)
        
        # 리사이즈 및 크롭 (Aspect Ratio 유지하며 채우기)
        target_w, target_h = target_size
        img_ratio = img.width / img.height
        target_ratio = target_w / target_h
        
        if img_ratio > target_ratio:
            # 이미지가 더 넓음 -> 높이 기준
            new_height = target_h
            new_width = int(new_height * img_ratio)
        else:
            # 이미지가 더 좁음 -> 너비 기준
            new_width = target_w
            new_height = int(new_width / img_ratio)
            
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # 중앙 크롭
        left = (new_width - target_w) // 2
        top = (new_height - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
        
        # 저장
        output_path = output_dir / f"processed_{img_path.name}"
        img.save(output_path, quality=95)
        
        return output_path
    except Exception as e:
        print(f"이미지 전처리 실패 ({img_path.name}): {e}")
        return img_path  # 실패 시 원본 반환



class ReelsEngine:
    """릴스 생성 엔진"""
    
    def __init__(self, config: ReelsConfig):
        """
        Args:
            config: 릴스 생성 설정
        """
        self.config = config
        self.target_size = (1080, 1920)  # 9:16 비율 (FHD)
        self.fps = 30
        self.ai_content = None  # AI 생성 콘텐츠 저장
        self.narration_audio_path = None  # 나레이션 오디오 파일 경로
        
        # 얼굴 감지기 초기화 (스마트 크롭 또는 적응형 지속 시간 사용 시)
        if self.config.enable_smart_crop or self.config.enable_adaptive_duration:
            try:
                self.face_detector = FaceDetector()
                print("[초기화] 얼굴 감지기 준비 완료")
            except Exception as e:
                print(f"[경고] 얼굴 감지기 초기화 실패: {e}")
                self.face_detector = None
        else:
            self.face_detector = None

    
    def generate_reels(
        self,
        input_dir: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        릴스 생성
        
        Args:
            input_dir: 입력 이미지 디렉토리
            output_path: 출력 비디오 파일 경로
            progress_callback: 진행률 콜백 함수 (progress, message)
            
        Returns:
            성공 여부
        """
        try:
            # 진행률 업데이트
            self._update_progress(progress_callback, 10, "이미지 파일 수집 중...")
            
            # 이미지 파일 목록 가져오기
            valid_extensions = ('.jpg', '.jpeg', '.png')
            image_files = [
                f for f in input_dir.iterdir()
                if f.is_file() and f.suffix.lower() in valid_extensions
            ]
            
            if not image_files:
                print(f"'{input_dir}' 폴더에 이미지가 없습니다.")
                return False
            
            # 이미지 유효성 검사
            image_files = [f for f in image_files if validate_image(f)]
            
            if not image_files:
                print("유효한 이미지가 없습니다.")
                return False
            
            # 시간순 정렬 (설정에 따라)
            if self.config.sort_by_time:
                self._update_progress(progress_callback, 20, "사진을 시간순으로 정렬 중...")
                image_files = sort_photos_by_time(image_files)
            else:
                image_files.sort()
            
            print(f"발견된 이미지: {len(image_files)}장")
            
            # 이미지 전처리 (병렬)
            self._update_progress(progress_callback, 22, "이미지 최적화 중 (병렬 처리)...")
            processed_dir = output_path.parent / "processed_images"
            processed_dir.mkdir(parents=True, exist_ok=True)
            
            image_files = self._preprocess_images_parallel(image_files, processed_dir)
            
            # AI 분석 (설정에 따라)
            if self.config.enable_ai_analysis and AI_AVAILABLE:
                self._update_progress(progress_callback, 25, "AI로 이미지 분석 중...")
                self._analyze_with_ai(image_files, output_path.parent)
            elif self.config.enable_ai_analysis and not AI_AVAILABLE:
                print("[경고] AI 기능이 활성화되었지만 openai 패키지가 설치되지 않았습니다.")
            
            # AI 영상 생성 (Sora 또는 SVD)
            elif self.config.enable_svd:
                # Stable Video Diffusion (무료 로컬)
                self._update_progress(progress_callback, 30, "SVD로 비디오 생성 중...")
                clips = self._create_clips_with_svd(image_files, output_path.parent, progress_callback)
            else:
                # 기존 방식: 이미지 클립 생성
                self._update_progress(progress_callback, 30, "비디오 클립 생성 중...")
                clips = []
                
                for idx, img_file in enumerate(image_files):
                    progress = 30 + int((idx / len(image_files)) * 40)
                    self._update_progress(
                        progress_callback, 
                        progress, 
                        f"처리 중: {img_file.name} ({idx + 1}/{len(image_files)})"
                    )
                    
                    try:
                        clip = self._create_clip(img_file)
                        clips.append(clip)
                    except Exception as e:
                        print(f"클립 생성 오류 ({img_file.name}): {e}")
            
            if not clips:
                print("생성할 클립이 없습니다.")
                return False
            
            # 비트 싱크 (배경음악이 있고 활성화된 경우)
            if self.config.enable_beat_sync and self.config.background_music_path:
                bg_music_path = Path(self.config.background_music_path)
                if bg_music_path.exists():
                    self._update_progress(progress_callback, 60, "음악 비트 분석 및 싱크 조절 중...")
                    beats = detect_beats(bg_music_path)
                    if beats:
                        # 오디오 길이 가져오기
                        from moviepy import AudioFileClip
                        audio = AudioFileClip(str(bg_music_path))
                        clips = adjust_clips_to_beats(clips, beats, audio.duration)
                        print(f"[Audio] 클립 길이 비트 싱크 완료")
            
            # 전환 효과 적용
            if self.config.enable_transitions:
                self._update_progress(progress_callback, 70, "전환 효과 적용 중...")
                clips = self._apply_transitions(clips)
            
            # 영상 합치기
            self._update_progress(progress_callback, 80, "영상 합치는 중...")
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # AI 자막 추가 (설정에 따라)
            if self.config.enable_ai_subtitles and self.ai_content:
                self._update_progress(progress_callback, 85, "AI 자막 추가 중...")
                final_clip = self._add_ai_subtitles(final_clip)
            
            # 나레이션 오디오 추가 (설정에 따라)
            elif self.config.enable_narration and self.narration_audio_path:
                self._update_progress(progress_callback, 85, "나레이션 추가 중...")
                final_clip = self._add_narration_to_video(final_clip)
            
            # 배경음악 추가 (설정에 따라)
            if self.config.background_music_path:
                bg_music_path = Path(self.config.background_music_path)
                if bg_music_path.exists():
                    self._update_progress(progress_callback, 88, "배경음악 추가 중...")
                    final_clip = self._add_background_music(final_clip, bg_music_path)
            
            # 출력 디렉토리 생성
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 영상 저장
            self._update_progress(progress_callback, 90, f"영상 저장 중: {output_path.name}")
            final_clip.write_videofile(
                str(output_path),
                fps=self.fps,
                codec='libx264',
                audio_codec='aac',
                bitrate='8000k',        # 높은 비트레이트로 화질 개선 (기본값보다 훨씬 높음)
                preset='slow',          # 느리지만 더 나은 압축 품질 (ultrafast/superfast/veryfast/faster/fast/medium/slow/slower/veryslow)
                ffmpeg_params=[
                    '-profile:v', 'high',     # H.264 High Profile (더 나은 압축)
                    '-crf', '18',             # Constant Rate Factor (0-51, 낮을수록 고화질, 18은 거의 무손실)
                    '-pix_fmt', 'yuv420p'     # 호환성을 위한 픽셀 포맷
                ]
            )
            
            self._update_progress(progress_callback, 100, "완료!")
            print("릴스 생성 완료!")
            return True
        
        except Exception as e:
            print(f"릴스 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _create_clip(self, image_path: Path) -> ImageClip:
        """
        이미지 클립 생성
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            생성된 ImageClip
        """
        # 이미지 클립 생성
        clip = ImageClip(str(image_path))
        
        # 이미지 리사이즈 및 크롭 (Center Crop)
        img_w, img_h = clip.size
        target_w, target_h = self.target_size
        
        # 너비 기준 비율과 높이 기준 비율 중 큰 쪽을 선택하여 리사이즈 (Cover)
        scale_x = target_w / img_w
        scale_y = target_h / img_h
        scale = max(scale_x, scale_y)
        
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # 리사이즈
        clip = clip.resized(new_size=(new_w, new_h))
        
        # 중앙 크롭
        center_x = new_w / 2
        center_y = new_h / 2
        clip = clip.cropped(width=target_w, height=target_h, x_center=center_x, y_center=center_y)
        
        # 고급 카메라 효과 적용
        clip = self._apply_camera_effects(clip)
        
        # 지속 시간 설정 (텍스트 오버레이 전에 설정 필요)
        clip = clip.with_duration(self.config.duration_per_photo)
        
        # 텍스트 오버레이 (설정에 따라)
        if self.config.enable_text_overlay:
            clip = self._add_text_overlay(clip, image_path)
        
        return clip
    
    def _apply_camera_effects(self, clip: ImageClip) -> ImageClip:
        """
        카메라 효과 통합 적용
        
        Args:
            clip: 원본 클립
            
        Returns:
            효과가 적용된 클립
        """
        import random
        
        # 카메라 스타일에 따라 효과 선택
        if self.config.camera_style == "cinematic":
            # 시네마틱: 부드럽고 느린 움직임
            if self.config.enable_3d_rotation:
                clip = self._apply_3d_rotation(clip)
            elif self.config.enable_circular_motion:
                clip = self._apply_circular_motion(clip)
            elif self.config.enable_zoom_pan_combo:
                clip = self._apply_zoom_pan_combo(clip)
            else:
                clip = self._apply_ken_burns(clip)
                
        elif self.config.camera_style == "dynamic":
            # 다이나믹: 다양한 효과 랜덤 선택
            effects = []
            if self.config.enable_ken_burns:
                effects.append(self._apply_ken_burns)
            if self.config.enable_3d_rotation:
                effects.append(self._apply_3d_rotation)
            if self.config.enable_circular_motion:
                effects.append(self._apply_circular_motion)
            if self.config.enable_zoom_pan_combo:
                effects.append(self._apply_zoom_pan_combo)
            
            if effects:
                effect = random.choice(effects)
                clip = effect(clip)
            elif self.config.enable_ken_burns:
                clip = self._apply_ken_burns(clip)
                
        else:  # basic
            # 기본: Ken Burns만
            if self.config.enable_ken_burns:
                clip = self._apply_ken_burns(clip)
        
        # 핸드헬드 흔들림 (모든 스타일에 적용 가능)
        if self.config.enable_handheld:
            clip = self._apply_handheld(clip)
        
        # 기본 회전 효과
        if self.config.enable_rotation:
            clip = self._apply_rotation(clip)
        
        return clip
    
    def _apply_ken_burns(self, clip: ImageClip) -> ImageClip:
        """
        Ken Burns 효과 적용 (다양한 움직임)
        
        Args:
            clip: 원본 클립
            
        Returns:
            효과가 적용된 클립
        """
        import random
        
        duration = self.config.duration_per_photo
        
        # 효과 강도 설정
        intensity_map = {
            "low": 0.05,      # 1.0 → 1.05 (5% 변화)
            "medium": 0.15,   # 1.0 → 1.15 (15% 변화)
            "high": 0.30      # 1.0 → 1.30 (30% 변화)
        }
        intensity = intensity_map.get(self.config.effect_intensity, 0.15)
        
        # Ken Burns 스타일 선택
        style = self.config.ken_burns_style
        if style == "random":
            style = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "diagonal"])
        
        # 스타일별 효과 적용
        if style == "zoom_in":
            # 줌 인: 1.0 → 1.0 + intensity
            def effect(get_frame, t):
                zoom = 1.0 + (t / duration) * intensity
                frame = get_frame(t)
                h, w = frame.shape[:2]
                new_h, new_w = int(h * zoom), int(w * zoom)
                
                # 리사이즈
                from PIL import Image
                import numpy as np
                # float to uint8 변환
                frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                img = Image.fromarray(frame_uint8)
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                
                # 중앙 크롭
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                img_cropped = img_resized.crop((left, top, left + w, top + h))
                
                return np.array(img_cropped)
            
            return clip.transform(effect)
        
        elif style == "zoom_out":
            # 줌 아웃: 1.0 + intensity → 1.0
            def effect(get_frame, t):
                zoom = (1.0 + intensity) - (t / duration) * intensity
                frame = get_frame(t)
                h, w = frame.shape[:2]
                new_h, new_w = int(h * zoom), int(w * zoom)
                
                from PIL import Image
                import numpy as np
                # float to uint8 변환
                frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                img = Image.fromarray(frame_uint8)
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                img_cropped = img_resized.crop((left, top, left + w, top + h))
                
                return np.array(img_cropped)
            
            return clip.transform(effect)
        
        elif style in ["pan_left", "pan_right", "pan_up", "pan_down"]:
            # 패닝 효과
            pan_amount = int(clip.w * intensity) if style in ["pan_left", "pan_right"] else int(clip.h * intensity)
            
            # 먼저 이미지를 확대 (패닝할 공간 확보)
            scale = 1.0 + intensity
            clip_scaled = clip.resized(lambda t: scale)
            
            def effect(get_frame, t):
                frame = get_frame(t)
                h, w = frame.shape[:2]
                progress = t / duration
                
                if style == "pan_left":
                    # 오른쪽에서 왼쪽으로
                    offset_x = int(pan_amount * (1 - progress))
                    offset_y = 0
                elif style == "pan_right":
                    # 왼쪽에서 오른쪽으로
                    offset_x = int(pan_amount * progress)
                    offset_y = 0
                elif style == "pan_up":
                    # 아래에서 위로
                    offset_x = 0
                    offset_y = int(pan_amount * (1 - progress))
                elif style == "pan_down":
                    # 위에서 아래로
                    offset_x = 0
                    offset_y = int(pan_amount * progress)
                
                # 크롭
                from PIL import Image
                import numpy as np
                # float to uint8 변환
                frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                img = Image.fromarray(frame_uint8)
                target_w, target_h = self.target_size
                
                left = offset_x
                top = offset_y
                right = left + target_w
                bottom = top + target_h
                
                # 경계 체크
                if right > w:
                    right = w
                    left = w - target_w
                if bottom > h:
                    bottom = h
                    top = h - target_h
                if left < 0:
                    left = 0
                if top < 0:
                    top = 0
                
                img_cropped = img.crop((left, top, right, bottom))
                
                return np.array(img_cropped)
            
            return clip_scaled.transform(effect)
        
        elif style == "diagonal":
            # 대각선 움직임 (줌 + 패닝 조합)
            direction = random.choice(["top_left", "top_right", "bottom_left", "bottom_right"])
            
            def effect(get_frame, t):
                zoom = 1.0 + (t / duration) * intensity
                frame = get_frame(t)
                h, w = frame.shape[:2]
                new_h, new_w = int(h * zoom), int(w * zoom)
                
                from PIL import Image
                import numpy as np
                # float to uint8 변환
                frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                img = Image.fromarray(frame_uint8)
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                
                progress = t / duration
                target_w, target_h = self.target_size
                
                # 방향에 따라 크롭 위치 결정
                if direction == "top_left":
                    left = int((new_w - target_w) * (1 - progress))
                    top = int((new_h - target_h) * (1 - progress))
                elif direction == "top_right":
                    left = int((new_w - target_w) * progress)
                    top = int((new_h - target_h) * (1 - progress))
                elif direction == "bottom_left":
                    left = int((new_w - target_w) * (1 - progress))
                    top = int((new_h - target_h) * progress)
                else:  # bottom_right
                    left = int((new_w - target_w) * progress)
                    top = int((new_h - target_h) * progress)
                
                img_cropped = img_resized.crop((left, top, left + target_w, top + target_h))
                
                return np.array(img_cropped)
            
            return clip.transform(effect)
        
        else:
            # 기본값: 단순 줌 인
            def effect(get_frame, t):
                zoom = 1.0 + (t / duration) * 0.1
                frame = get_frame(t)
                h, w = frame.shape[:2]
                new_h, new_w = int(h * zoom), int(w * zoom)
                
                from PIL import Image
                import numpy as np
                # float to uint8 변환
                frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                img = Image.fromarray(frame_uint8)
                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                
                left = (new_w - w) // 2
                top = (new_h - h) // 2
                img_cropped = img_resized.crop((left, top, left + w, top + h))
                
                return np.array(img_cropped)
            
            return clip.transform(effect)

    
    def _apply_rotation(self, clip: ImageClip) -> ImageClip:
        """
        회전 효과 적용 (미묘한 회전)
        
        Args:
            clip: 원본 클립
            
        Returns:
            회전 효과가 적용된 클립
        """
        import random
        
        duration = self.config.duration_per_photo
        
        # 랜덤 회전 방향 및 각도 (-3도 ~ +3도)
        max_angle = 3.0
        direction = random.choice([-1, 1])
        target_angle = direction * random.uniform(1.5, max_angle)
        
        def rotation_effect(t):
            # 시간에 따라 회전 각도 계산 (0도 → target_angle)
            progress = t / duration
            angle = target_angle * progress
            return angle
        
        # 회전 적용
        clip = clip.rotated(lambda t: rotation_effect(t), resample='bicubic', expand=False)
        
        return clip
    
    def _apply_3d_rotation(self, clip: ImageClip) -> ImageClip:
        """
        3D 회전 효과 (Y축 회전)
        
        Args:
            clip: 원본 클립
            
        Returns:
            3D 회전 효과가 적용된 클립
        """
        import random
        import numpy as np
        from PIL import Image
        
        duration = self.config.duration_per_photo
        max_angle = 15  # 최대 회전 각도
        direction = random.choice([-1, 1])
        
        def effect(get_frame, t):
            progress = t / duration
            angle = direction * max_angle * np.sin(progress * np.pi)  # 부드러운 회전
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # float to uint8 변환
            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
            img = Image.fromarray(frame_uint8)
            
            # 3D 회전 시뮬레이션 (원근 변환)
            # 간단한 스케일 변환으로 3D 효과 시뮬레이션
            scale_factor = 1.0 - abs(angle) / 100.0  # 회전 시 약간 축소
            new_w = int(w * scale_factor)
            new_h = h
            
            if new_w > 0:
                img_scaled = img.resize((new_w, new_h), Image.LANCZOS)
                
                # 중앙 배치
                result = np.zeros_like(frame_uint8)
                left = (w - new_w) // 2
                result[:, left:left+new_w] = np.array(img_scaled)
                
                return result
            else:
                return frame_uint8
        
        return clip.transform(effect)
    
    def _apply_circular_motion(self, clip: ImageClip) -> ImageClip:
        """
        원형 움직임 효과
        
        Args:
            clip: 원본 클립
            
        Returns:
            원형 움직임 효과가 적용된 클립
        """
        import numpy as np
        from PIL import Image
        
        duration = self.config.duration_per_photo
        radius = 50  # 원형 움직임 반지름 (픽셀)
        
        # 먼저 이미지를 확대 (움직일 공간 확보)
        scale = 1.2
        clip_scaled = clip.resized(lambda t: scale)
        
        def effect(get_frame, t):
            progress = t / duration
            angle = progress * 2 * np.pi  # 0 ~ 2π
            
            # 원형 경로 계산
            offset_x = int(radius * np.cos(angle))
            offset_y = int(radius * np.sin(angle))
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # float to uint8 변환
            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
            img = Image.fromarray(frame_uint8)
            
            # 크롭 위치 계산
            target_w, target_h = self.target_size
            center_x = w // 2 + offset_x
            center_y = h // 2 + offset_y
            
            left = max(0, center_x - target_w // 2)
            top = max(0, center_y - target_h // 2)
            right = min(w, left + target_w)
            bottom = min(h, top + target_h)
            
            # 경계 체크
            if right - left < target_w:
                left = max(0, right - target_w)
            if bottom - top < target_h:
                top = max(0, bottom - target_h)
            
            img_cropped = img.crop((left, top, left + target_w, top + target_h))
            
            return np.array(img_cropped)
        
        return clip_scaled.transform(effect)
    
    def _apply_zoom_pan_combo(self, clip: ImageClip) -> ImageClip:
        """
        줌 + 팬 조합 효과
        
        Args:
            clip: 원본 클립
            
        Returns:
            줌+팬 효과가 적용된 클립
        """
        import random
        import numpy as np
        from PIL import Image
        
        duration = self.config.duration_per_photo
        
        # 랜덤 방향 선택
        pan_direction = random.choice(['left', 'right', 'up', 'down'])
        zoom_direction = random.choice(['in', 'out'])
        
        # 효과 강도
        intensity_map = {
            "low": 0.1,
            "medium": 0.2,
            "high": 0.3
        }
        intensity = intensity_map.get(self.config.effect_intensity, 0.2)
        
        def effect(get_frame, t):
            progress = t / duration
            
            # 줌 계산
            if zoom_direction == 'in':
                zoom = 1.0 + progress * intensity
            else:
                zoom = (1.0 + intensity) - progress * intensity
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            new_h, new_w = int(h * zoom), int(w * zoom)
            
            # float to uint8 변환
            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
            img = Image.fromarray(frame_uint8)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            
            # 팬 계산
            target_w, target_h = self.target_size
            pan_amount = int(min(new_w - target_w, new_h - target_h) * 0.3)
            
            if pan_direction == 'left':
                left = int(pan_amount * (1 - progress))
                top = (new_h - target_h) // 2
            elif pan_direction == 'right':
                left = int(pan_amount * progress)
                top = (new_h - target_h) // 2
            elif pan_direction == 'up':
                left = (new_w - target_w) // 2
                top = int(pan_amount * (1 - progress))
            else:  # down
                left = (new_w - target_w) // 2
                top = int(pan_amount * progress)
            
            # 경계 체크
            left = max(0, min(left, new_w - target_w))
            top = max(0, min(top, new_h - target_h))
            
            img_cropped = img_resized.crop((left, top, left + target_w, top + target_h))
            
            return np.array(img_cropped)
        
        return clip.transform(effect)
    
    def _apply_handheld(self, clip: ImageClip) -> ImageClip:
        """
        핸드헬드 흔들림 효과 (다큐멘터리 스타일)
        
        Args:
            clip: 원본 클립
            
        Returns:
            흔들림 효과가 적용된 클립
        """
        import random
        import numpy as np
        from PIL import Image
        
        duration = self.config.duration_per_photo
        shake_amount = 5  # 흔들림 강도 (픽셀)
        
        # 먼저 이미지를 약간 확대 (흔들릴 공간 확보)
        scale = 1.05
        clip_scaled = clip.resized(lambda t: scale)
        
        def effect(get_frame, t):
            # 랜덤 흔들림
            offset_x = random.randint(-shake_amount, shake_amount)
            offset_y = random.randint(-shake_amount, shake_amount)
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            
            # float to uint8 변환
            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
            img = Image.fromarray(frame_uint8)
            
            # 크롭 위치 계산
            target_w, target_h = self.target_size
            center_x = w // 2 + offset_x
            center_y = h // 2 + offset_y
            
            left = max(0, min(center_x - target_w // 2, w - target_w))
            top = max(0, min(center_y - target_h // 2, h - target_h))
            
            img_cropped = img.crop((left, top, left + target_w, top + target_h))
            
            return np.array(img_cropped)
        
        return clip_scaled.transform(effect)
    
    
    def _add_text_overlay(self, clip: ImageClip, image_path: Path) -> ImageClip:
        """
        텍스트 오버레이 추가 (날짜 또는 AI 생성 텍스트)
        
        Args:
            clip: 원본 클립
            image_path: 이미지 파일 경로
            
        Returns:
            텍스트가 추가된 클립
        """
        text_to_display = None
        
        # AI 텍스트 오버레이가 활성화된 경우
        if self.config.enable_ai_text_overlay and AI_AVAILABLE:
            try:
                # OpenAI 서비스 초기화 (캐싱)
                if not hasattr(self, '_openai_service'):
                    self._openai_service = OpenAIService()
                
                # AI로 이미지 분석하여 텍스트 생성
                print(f"[AI] 이미지 분석 중: {image_path.name}")
                ai_text = self._openai_service.analyze_single_image(
                    image_path, 
                    style=self.config.ai_text_style
                )
                text_to_display = ai_text
                print(f"[AI] 생성된 텍스트: {ai_text}")
                
            except Exception as e:
                print(f"[AI] 텍스트 생성 실패 ({image_path.name}): {e}")
                # 실패 시 날짜로 폴백
                exif_data = extract_exif_data(image_path)
                if exif_data.get("datetime"):
                    text_to_display = format_datetime_korean(exif_data["datetime"])
        
        # AI 비활성화 또는 실패 시 날짜 사용
        if not text_to_display:
            exif_data = extract_exif_data(image_path)
            if exif_data.get("datetime"):
                text_to_display = format_datetime_korean(exif_data["datetime"])
        
        # 텍스트가 있으면 오버레이 추가
        if text_to_display:
            from moviepy import ColorClip
            from moviepy.video.fx.FadeIn import FadeIn
            from moviepy.video.fx.FadeOut import FadeOut
            
            # 폰트 설정 (Windows)
            font = 'Arial'
            import platform
            if platform.system() == 'Windows':
                if os.path.exists("C:/Windows/Fonts/malgun.ttf"):
                    font = "C:/Windows/Fonts/malgun.ttf"
            
            txt_clip = TextClip(
                text=text_to_display,
                font_size=40,
                color='white',
                font=font,
                method='label'
            )
            
            # 배경 박스
            padding = 20
            bg_w, bg_h = txt_clip.w + padding*2, txt_clip.h + padding
            bg_clip = ColorClip(size=(bg_w, bg_h), color=(0,0,0)).with_opacity(0.5).with_duration(clip.duration)
            txt_clip = txt_clip.with_duration(clip.duration)
            
            # 텍스트와 배경 합성
            txt_composite = CompositeVideoClip([
                bg_clip.with_position('center'),
                txt_clip.with_position('center')
            ])
            
            # 위치 설정 (하단)
            txt_composite = txt_composite.with_position(('center', 0.85), relative=True)
            
            # 페이드 인/아웃
            txt_composite = txt_composite.with_effects([FadeIn(0.5), FadeOut(0.5)])
            
            # 클립에 텍스트 합성
            clip = CompositeVideoClip([clip, txt_composite])
        
        return clip
    
    def _apply_transitions(self, clips: List[ImageClip]) -> List[ImageClip]:
        """
        클립 간 전환 효과 적용 (다양한 스타일)
        
        Args:
            clips: 클립 리스트
            
        Returns:
            전환 효과가 적용된 클립 리스트
        """
        if len(clips) <= 1:
            return clips
        
        import random
        from moviepy.video.fx.FadeIn import FadeIn
        from moviepy.video.fx.FadeOut import FadeOut
        
        transition_duration = 0.5  # 0.5초 전환
        style = self.config.transition_style
        
        processed_clips = []
        
        for i, clip in enumerate(clips):
            # 랜덤 모드인 경우 각 전환마다 다른 스타일 선택 (고급 효과 포함)
            if style == "random":
                current_style = random.choice(["fade", "slide", "zoom", "morph", "glitch", "circular", "page_curl"])
            else:
                current_style = style
            
            # 페이드 전환 (기본)
            if current_style == "fade":
                effects = []
                
                if i > 0:
                    effects.append(FadeIn(transition_duration))
                if i < len(clips) - 1:
                    effects.append(FadeOut(transition_duration))
                
                if effects:
                    clip = clip.with_effects(effects)
            
            # 슬라이드 전환
            elif current_style == "slide":
                if i > 0:
                    # 슬라이드 인 효과 (왼쪽에서 들어옴)
                    direction = random.choice(["left", "right", "top", "bottom"])
                    
                    def slide_in(get_frame, t):
                        if t < transition_duration:
                            progress = t / transition_duration
                            frame = get_frame(t)
                            h, w = frame.shape[:2]
                            
                            from PIL import Image
                            import numpy as np
                            
                            # float to uint8 변환
                            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                            
                            # 검은 배경 생성
                            result = np.zeros_like(frame_uint8)
                            img = Image.fromarray(frame_uint8)
                            
                            if direction == "left":
                                offset = int(w * (1 - progress))
                                result[:, offset:] = np.array(img)[:, :w-offset]
                            elif direction == "right":
                                offset = int(w * (1 - progress))
                                result[:, :w-offset] = np.array(img)[:, offset:]
                            elif direction == "top":
                                offset = int(h * (1 - progress))
                                result[offset:, :] = np.array(img)[:h-offset, :]
                            else:  # bottom
                                offset = int(h * (1 - progress))
                                result[:h-offset, :] = np.array(img)[offset:, :]
                            
                            return result
                        else:
                            return get_frame(t)
                    
                    clip = clip.transform(slide_in)
                
                if i < len(clips) - 1:
                    # 페이드 아웃 (슬라이드 아웃은 복잡하므로 페이드 사용)
                    clip = clip.with_effects([FadeOut(transition_duration)])
            
            # 줌 전환
            elif current_style == "zoom":
                if i > 0:
                    # 줌 인 효과로 시작
                    def zoom_in(get_frame, t):
                        if t < transition_duration:
                            progress = t / transition_duration
                            zoom = 0.5 + (progress * 0.5)  # 0.5 -> 1.0
                            frame = get_frame(t)
                            h, w = frame.shape[:2]
                            new_h, new_w = int(h * zoom), int(w * zoom)
                            
                            from PIL import Image
                            import numpy as np
                            
                            # float to uint8 변환
                            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
                            
                            if new_h > 0 and new_w > 0:
                                img = Image.fromarray(frame_uint8)
                                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                                
                                # 중앙에 배치
                                result = np.zeros_like(frame_uint8)
                                top = (h - new_h) // 2
                                left = (w - new_w) // 2
                                
                                if top >= 0 and left >= 0:
                                    result[top:top+new_h, left:left+new_w] = np.array(img_resized)
                                else:
                                    # 크롭 필요
                                    crop_top = max(0, -top)
                                    crop_left = max(0, -left)
                                    crop_bottom = crop_top + h
                                    crop_right = crop_left + w
                                    
                                    img_cropped = img_resized.crop((crop_left, crop_top, crop_right, crop_bottom))
                                    result = np.array(img_cropped)
                                
                                return result
                            else:
                                return frame
                        else:
                            return get_frame(t)
                    
                    clip = clip.transform(zoom_in)
                
                if i < len(clips) - 1:
                    clip = clip.with_effects([FadeOut(transition_duration)])
            
            # 고급 전환 효과 (Morph)
            elif current_style == "morph":
                if i > 0:
                    def morph_effect(get_frame, t):
                        if t < transition_duration:
                            progress = t / transition_duration
                            # 이전 클립의 마지막 프레임 (이미지이므로 첫 프레임과 동일)
                            frame1 = clips[i-1].get_frame(clips[i-1].duration) 
                            # 현재 클립의 현재 프레임
                            frame2 = get_frame(t)
                            
                            # 크기 맞추기 (혹시 다를 경우)
                            if frame1.shape != frame2.shape:
                                from PIL import Image
                                img1 = Image.fromarray(frame1)
                                img1 = img1.resize((frame2.shape[1], frame2.shape[0]))
                                frame1 = np.array(img1)
                            
                            return apply_morph_transition(frame1, frame2, progress)
                        else:
                            return get_frame(t)
                    
                    clip = clip.transform(morph_effect)
            
            # 고급 전환 효과 (Glitch)
            elif current_style == "glitch":
                if i > 0:
                    def glitch_effect(get_frame, t):
                        if t < transition_duration:
                            progress = 1.0 - (t / transition_duration) # 점점 줄어들게
                            frame = get_frame(t)
                            return apply_glitch_transition(frame, progress, intensity=0.5)
                        else:
                            return get_frame(t)
                    
                    clip = clip.transform(glitch_effect)
                    # 페이드 인 추가하여 부드럽게
                    clip = clip.with_effects([FadeIn(transition_duration)])

            # 고급 전환 효과 (Circular Wipe)
            elif current_style == "circular":
                if i > 0:
                    def circular_effect(get_frame, t):
                        if t < transition_duration:
                            progress = t / transition_duration
                            frame2 = get_frame(t)
                            # 이전 클립의 마지막 프레임
                            frame1 = clips[i-1].get_frame(clips[i-1].duration)
                            
                            if frame1.shape != frame2.shape:
                                from PIL import Image
                                img1 = Image.fromarray(frame1)
                                img1 = img1.resize((frame2.shape[1], frame2.shape[0]))
                                frame1 = np.array(img1)
                                
                            return apply_circular_wipe_transition(frame1, frame2, progress)
                        else:
                            return get_frame(t)
                    
                    clip = clip.transform(circular_effect)

            # 고급 전환 효과 (Page Curl)
            elif current_style == "page_curl":
                if i > 0:
                    direction = random.choice(["left", "right", "up", "down"])
                    def page_curl_effect(get_frame, t):
                        if t < transition_duration:
                            progress = t / transition_duration
                            frame2 = get_frame(t)
                            frame1 = clips[i-1].get_frame(clips[i-1].duration)
                            
                            if frame1.shape != frame2.shape:
                                from PIL import Image
                                img1 = Image.fromarray(frame1)
                                img1 = img1.resize((frame2.shape[1], frame2.shape[0]))
                                frame1 = np.array(img1)
                                
                            return apply_page_curl_transition(frame1, frame2, progress, direction)
                        else:
                            return get_frame(t)
                    
                    clip = clip.transform(page_curl_effect)

            processed_clips.append(clip)
        
        return processed_clips
    
    def _update_progress(
        self,
        callback: Optional[Callable[[int, str], None]],
        progress: int,
        message: str
    ):
        """진행률 업데이트"""
        if callback:
            callback(progress, message)
        print(f"[{progress}%] {message}")
    
    def _analyze_with_ai(self, image_files: List[Path], output_dir: Path):
        """
        AI로 이미지 분석 및 스토리 생성
        
        Args:
            image_files: 이미지 파일 리스트
            output_dir: 출력 디렉토리 (나레이션 파일 저장용)
        """
        try:
            ai_service = OpenAIService()
            
            # 이미지 분석
            analysis = ai_service.analyze_images(image_files)
            
            # 스토리 생성
            story = ai_service.generate_story(analysis, len(image_files))
            
            # AI 캡션 생성 (설정에 따라)
            if self.config.enable_ai_captions:
                captions = ai_service.generate_captions_for_images(image_files, analysis)
            else:
                captions = None
            
            # AI 콘텐츠 저장
            self.ai_content = {
                "analysis": analysis,
                "story": story,
                "captions": captions
            }
            
            # 나레이션 생성 (설정에 따라)
            if self.config.enable_narration and story.get("narration"):
                narration_path = output_dir / "narration.mp3"
                success = ai_service.generate_narration_audio(
                    text=story["narration"],
                    output_path=narration_path,
                    voice=self.config.narration_voice
                )
                if success:
                    self.narration_audio_path = narration_path
            
            print(f"[AI] 분석 완료 - 제목: {story.get('title', '알 수 없음')}")
            
        except Exception as e:
            print(f"[AI] 분석 오류: {e}")
            import traceback
            traceback.print_exc()
    

    
    def _create_clips_fallback(
        self,
        image_files: List[Path],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List:
        """
        기존 방식으로 클립 생성 (폴백)
        
        Args:
            image_files: 이미지 파일 리스트
            progress_callback: 진행률 콜백 함수
            
        Returns:
            클립 리스트
        """
        clips = []
        
        for idx, img_file in enumerate(image_files):
            progress = 30 + int((idx / len(image_files)) * 40)
            self._update_progress(
                progress_callback,
                progress,
                f"처리 중: {img_file.name} ({idx + 1}/{len(image_files)})"
            )
            
            try:
                clip = self._create_clip(img_file)
                clips.append(clip)
            except Exception as e:
                print(f"클립 생성 오류 ({img_file.name}): {e}")
        
        return clips
    

    
    def _add_text_overlay_to_video(self, video_clip, image_path: Path):
        """
        비디오 클립에 텍스트 오버레이 추가
        
        Args:
            video_clip: 비디오 클립
            image_path: 원본 이미지 경로 (EXIF 데이터 추출용)
            
        Returns:
            텍스트가 추가된 비디오 클립
        """
        from moviepy import TextClip, CompositeVideoClip
        
        # EXIF 데이터 추출
        exif_data = extract_exif_data(image_path)
        
        # 날짜 정보가 있으면 텍스트 추가
        if exif_data.get("datetime"):
            date_text = format_datetime_korean(exif_data["datetime"])
            
            # 텍스트 클립 생성
            txt_clip = TextClip(
                text=date_text,
                font_size=40,
                color='white',
                font='Arial',
                stroke_color='black',
                stroke_width=2
            )
            
            # 하단 중앙에 배치
            txt_clip = txt_clip.with_position(('center', 'bottom')).margin(bottom=50)
            txt_clip = txt_clip.with_duration(video_clip.duration)
            
            # 페이드 인/아웃 효과
            from moviepy.video.fx.FadeIn import FadeIn
            from moviepy.video.fx.FadeOut import FadeOut
            txt_clip = txt_clip.with_effects([FadeIn(0.5), FadeOut(0.5)])
            
            # 클립에 텍스트 합성
            video_clip = CompositeVideoClip([video_clip, txt_clip])
        
        return video_clip
    
    def _create_clips_with_svd(
        self,
        image_files: List[Path],
        output_dir: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List:
        """
        Stable Video Diffusion을 사용하여 이미지를 비디오 클립으로 변환
        
        Args:
            image_files: 이미지 파일 리스트
            output_dir: 출력 디렉토리 (SVD 비디오 저장용)
            progress_callback: 진행률 콜백 함수
            
        Returns:
            비디오 클립 리스트
        """
        from moviepy import VideoFileClip
        
        clips = []
        svd_dir = output_dir / "svd_videos"
        svd_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            from svd_service import SVDService
            svd_service = SVDService()
        except Exception as e:
            print(f"[SVD] SVD 서비스 초기화 실패: {e}")
            print("[SVD] 기존 방식으로 폴백합니다.")
            return self._create_clips_fallback(image_files, progress_callback)
        
        for idx, img_file in enumerate(image_files):
            progress = 30 + int((idx / len(image_files)) * 40)
            self._update_progress(
                progress_callback,
                progress,
                f"[SVD] 비디오 생성 중: {img_file.name} ({idx + 1}/{len(image_files)})"
            )
            
            # SVD 비디오 출력 경로
            video_output = svd_dir / f"{img_file.stem}_svd.mp4"
            
            # SVD로 비디오 생성
            try:
                success = svd_service.generate_video(
                    image_path=img_file,
                    output_path=video_output,
                    num_frames=self.config.svd_num_frames,
                    fps=self.config.svd_fps,
                    motion_bucket_id=self.config.svd_motion_bucket_id
                )
                
                if success and video_output.exists():
                    # 비디오 클립 로드
                    video_clip = VideoFileClip(str(video_output))
                    
                    # 크기 조정 (9:16 비율)
                    video_clip = video_clip.resized(self.target_size)
                    
                    # 텍스트 오버레이 (설정에 따라)
                    if self.config.enable_text_overlay:
                        video_clip = self._add_text_overlay_to_video(video_clip, img_file)
                    
                    clips.append(video_clip)
                    print(f"[SVD] 비디오 생성 성공: {img_file.name}")
                else:
                    # SVD 실패 → 폴백
                    print(f"[SVD] 비디오 생성 실패, 기존 방식으로 폴백: {img_file.name}")
                    clip = self._create_clip(img_file)
                    clips.append(clip)
                    
            except Exception as e:
                print(f"[SVD] 오류 발생 ({img_file.name}): {e}")
                print(f"[SVD] 기존 방식으로 폴백: {img_file.name}")
                try:
                    clip = self._create_clip(img_file)
                    clips.append(clip)
                except Exception as fallback_error:
                    print(f"[오류] 폴백도 실패 ({img_file.name}): {fallback_error}")
        
        # 메모리 정리
        try:
            svd_service.cleanup()
        except:
            pass
        
        return clips
    

    
    def _add_background_music(self, video_clip, music_path: Path):
        """
        비디오에 배경음악 추가 (나레이션과 믹싱)
        """
        try:
            from moviepy import AudioFileClip, CompositeAudioClip
            
            music_audio = AudioFileClip(str(music_path))
            
            # 비디오 길이만큼 반복 또는 자르기
            if music_audio.duration < video_clip.duration:
                # 반복 (loop) - moviepy 버전에 따라 다를 수 있음, 여기선 간단히 자르기만
                pass 
            else:
                music_audio = music_audio.subclipped(0, video_clip.duration)
            
            # 볼륨 조절 (나레이션이 있으면 배경음악 줄임)
            bg_volume = 0.3 if (self.config.enable_narration and self.narration_audio_path) else 0.8
            music_audio = music_audio.with_volume_scaled(bg_volume)
            
            # 기존 오디오(나레이션 등)와 합성
            if video_clip.audio:
                final_audio = CompositeAudioClip([music_audio, video_clip.audio])
            else:
                final_audio = music_audio
            
            video_clip = video_clip.with_audio(final_audio)
            print(f"[Audio] 배경음악 추가 완료")
            return video_clip
            
        except Exception as e:
            print(f"[오류] 배경음악 추가 실패: {e}")
            return video_clip
    def _add_narration_audio(self, video_clip):
        """
        비디오에 나레이션 오디오 추가
        
        Args:
            video_clip: 원본 비디오 클립
            
        Returns:
            나레이션이 추가된 비디오 클립
        """
        try:
            from moviepy import AudioFileClip
            
            if not self.narration_audio_path or not self.narration_audio_path.exists():
                print("[경고] 나레이션 파일을 찾을 수 없습니다.")
                return video_clip
            
            # 나레이션 오디오 로드
            narration_audio = AudioFileClip(str(self.narration_audio_path))
            
            # 비디오 길이에 맞게 조정
            if narration_audio.duration > video_clip.duration:
                # 나레이션이 더 길면 자르기
                narration_audio = narration_audio.subclipped(0, video_clip.duration)
            
            # 볼륨 조절 (70%로 설정)
            narration_audio = narration_audio.with_volume_scaled(0.7)
            
            # 비디오에 오디오 추가
            video_clip = video_clip.with_audio(narration_audio)
            
            print(f"[AI] 나레이션 추가 완료 ({narration_audio.duration:.1f}초)")
            return video_clip
            
        except Exception as e:
            print(f"[오류] 나레이션 추가 실패: {e}")
            return video_clip
    
    def _add_ai_subtitles(self, video_clip):
        """
        비디오에 AI 생성 스토리를 자막으로 추가
        
        Args:
            video_clip: 원본 비디오 클립
            
        Returns:
            자막이 추가된 비디오 클립
        """
        try:
            if not self.ai_content or not self.ai_content.get("story"):
                print("[경고] AI 스토리가 없습니다.")
                return video_clip
            
            story = self.ai_content["story"]
            narration_text = story.get("narration", "")
            title_text = story.get("title", "")
            
            if not narration_text:
                print("[경고] 나레이션 텍스트가 없습니다.")
                return video_clip
            
            # 자막 텍스트 준비 (제목 + 스토리)
            if title_text:
                subtitle_text = f"{title_text}\n\n{narration_text}"
            else:
                subtitle_text = narration_text
            
            # Windows 폰트 경로 찾기
            import platform
            font_path = None
            
            if platform.system() == 'Windows':
                # Windows 시스템 폰트 경로
                possible_fonts = [
                    r"C:\Windows\Fonts\malgun.ttf",      # 맑은 고딕 (한글)
                    r"C:\Windows\Fonts\malgunbd.ttf",    # 맑은 고딕 Bold
                    r"C:\Windows\Fonts\arial.ttf",       # Arial
                    r"C:\Windows\Fonts\arialbd.ttf",     # Arial Bold
                ]
                
                for font in possible_fonts:
                    if os.path.exists(font):
                        font_path = font
                        break
            
            # 자막 클립 생성
            from moviepy import TextClip, CompositeVideoClip
            
            # MoviePy 2.x 호환 방식
            if font_path:
                subtitle_clip = TextClip(
                    text=subtitle_text,
                    font_size=50,
                    color='white',
                    font=font_path,
                    stroke_color='black',
                    stroke_width=3,
                    method='caption',
                    size=(video_clip.w - 100, None)  # 좌우 여백 50px
                )
            else:
                # 폰트를 찾지 못한 경우 기본 폰트 사용
                print("[경고] 시스템 폰트를 찾지 못했습니다. 기본 폰트를 사용합니다.")
                subtitle_clip = TextClip(
                    text=subtitle_text,
                    font_size=50,
                    color='white',
                    stroke_color='black',
                    stroke_width=3,
                    method='caption',
                    size=(video_clip.w - 100, None)
                )
            
            # 상단 중앙에 배치
            subtitle_clip = subtitle_clip.with_position(('center', 100))
            subtitle_clip = subtitle_clip.with_duration(video_clip.duration)
            
            # 페이드 인/아웃 효과
            from moviepy.video.fx.FadeIn import FadeIn
            from moviepy.video.fx.FadeOut import FadeOut
            subtitle_clip = subtitle_clip.with_effects([FadeIn(1.0), FadeOut(1.0)])
            
            # 비디오에 자막 합성
            video_clip = CompositeVideoClip([video_clip, subtitle_clip])
            
            print(f"[AI] 자막 추가 완료: {subtitle_text[:30]}...")
            return video_clip
            
        except Exception as e:
            print(f"[오류] 자막 추가 실패: {e}")
            print("[정보] 자막 없이 비디오를 생성합니다.")
            import traceback
            traceback.print_exc()
            return video_clip




    def _preprocess_images_parallel(self, image_files: List[Path], output_dir: Path) -> List[Path]:
        """
        이미지 병렬 전처리 (ThreadPoolExecutor 사용 - Windows 호환)
        """
        processed_files = []
        tasks = []
        
        # Windows에서는 ThreadPoolExecutor를 사용하여 multiprocessing 문제 회피
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            for img_file in image_files:
                tasks.append((img_file, self.target_size, output_dir))
            
            results = list(executor.map(preprocess_image_task, tasks))
            
        # 결과 확인 (None이나 실패 제외)
        for res in results:
            if res and res.exists():
                processed_files.append(res)
            else:
                # 실패 시 원본이라도 사용하려 했으나 순서가 꼬일 수 있음.
                # map은 순서 보장하므로 tasks와 인덱스 매칭 가능하지만,
                # 여기선 결과가 경로이므로 그대로 사용
                pass
                
        return processed_files

def generate_reels(
    input_dir: Path,
    output_path: Path,
    config: ReelsConfig,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> bool:
    """
    릴스 생성 (편의 함수)
    
    Args:
        input_dir: 입력 이미지 디렉토리
        output_path: 출력 비디오 파일 경로
        config: 릴스 생성 설정
        progress_callback: 진행률 콜백 함수
        
    Returns:
        성공 여부
    """
    engine = ReelsEngine(config)
    return engine.generate_reels(input_dir, output_path, progress_callback)
