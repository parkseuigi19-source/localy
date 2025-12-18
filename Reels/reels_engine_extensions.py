"""
ReelsEngine 확장 메서드
기존 reels_engine.py를 확장하여 새로운 기능 추가

사용법:
from reels_engine_extensions import patch_reels_engine
patch_reels_engine()
"""
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Dict, Any
from moviepy import ImageClip
import random

from easing_functions import get_easing_function
from face_detection import FaceDetector, adjust_duration_by_importance
from color_grading import apply_auto_color_grading


def create_enhanced_clip(
    engine,
    image_path: Path
) -> ImageClip:
    """
    향상된 이미지 클립 생성 (스마트 크롭 + 색상 그레이딩 + 적응형 지속 시간)
    
    Args:
        engine: ReelsEngine 인스턴스
        image_path: 이미지 파일 경로
    
    Returns:
        생성된 ImageClip
    """
    # 이미지 클립 생성
    clip = ImageClip(str(image_path))
    
    # 이미지 리사이즈 및 크롭
    img_w, img_h = clip.size
    target_w, target_h = engine.target_size
    
    # 스케일 계산
    scale_x = target_w / img_w
    scale_y = target_h / img_h
    scale = max(scale_x, scale_y)
    
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    
    # 리사이즈
    clip = clip.resized(new_size=(new_w, new_h))
    
    # 스마트 크롭 (얼굴 감지 기반) 또는 중앙 크롭
    if engine.config.enable_smart_crop and hasattr(engine, 'face_detector') and engine.face_detector:
        try:
            crop_region = engine.face_detector.get_smart_crop_region(
                image_path, 
                engine.target_size,
                focus_on_faces=True
            )
            left, top, right, bottom = crop_region
            
            # PIL을 사용하여 크롭
            frame = clip.get_frame(0)
            if frame.dtype == np.float64 or frame.dtype == np.float32:
                frame = (frame * 255).astype(np.uint8)
            
            pil_img = Image.fromarray(frame)
            pil_img_resized = pil_img.resize((new_w, new_h), Image.LANCZOS)
            pil_img_cropped = pil_img_resized.crop((left, top, right, bottom))
            
            # 다시 MoviePy 클립으로 변환
            clip = ImageClip(np.array(pil_img_cropped))
            
            print(f"[스마트 크롭] {image_path.name} - 얼굴 중심 포커스")
        except Exception as e:
            print(f"[스마트 크롭 오류] {image_path.name}: {e}, 중앙 크롭으로 폴백")
            # 폴백: 중앙 크롭
            center_x = new_w / 2
            center_y = new_h / 2
            clip = clip.cropped(width=target_w, height=target_h, x_center=center_x, y_center=center_y)
    else:
        # 중앙 크롭
        center_x = new_w / 2
        center_y = new_h / 2
        clip = clip.cropped(width=target_w, height=target_h, x_center=center_x, y_center=center_y)
    
    # 색상 그레이딩 (설정에 따라)
    if engine.config.enable_color_grading:
        try:
            def apply_grading(get_frame, t):
                frame = get_frame(t)
                # BGR로 변환 (OpenCV 형식)
                if frame.dtype == np.float64 or frame.dtype == np.float32:
                    frame_uint8 = (frame * 255).astype(np.uint8)
                else:
                    frame_uint8 = frame
                
                # RGB -> BGR
                frame_bgr = frame_uint8[:, :, ::-1]
                
                # 색상 그레이딩 적용
                graded_bgr = apply_auto_color_grading(frame_bgr, engine.ai_content, intensity=0.7)
                
                # BGR -> RGB
                graded_rgb = graded_bgr[:, :, ::-1]
                
                return graded_rgb
            
            clip = clip.transform(apply_grading)
            print(f"[색상 그레이딩] {image_path.name}")
        except Exception as e:
            print(f"[색상 그레이딩 오류] {image_path.name}: {e}")
    
    # 지속 시간 먼저 설정 (Ken Burns 전에 필요!)
    if engine.config.enable_adaptive_duration and hasattr(engine, 'face_detector') and engine.face_detector:
        try:
            importance = engine.face_detector.analyze_image_importance(image_path)
            duration = adjust_duration_by_importance(
                engine.config.duration_per_photo,
                importance,
                min_duration=2,
                max_duration=6
            )
            clip = clip.with_duration(duration)
            print(f"[적응형 지속시간] {image_path.name}: {duration}초 (중요도: {importance:.2f})")
        except Exception as e:
            print(f"[적응형 지속시간 오류] {image_path.name}: {e}")
            clip = clip.with_duration(engine.config.duration_per_photo)
    else:
        clip = clip.with_duration(engine.config.duration_per_photo)
    
    # Ken Burns 효과 (설정에 따라)
    if engine.config.enable_ken_burns:
        clip = apply_enhanced_ken_burns(engine, clip)
    
    # 회전 효과 (설정에 따라)
    if engine.config.enable_rotation:
        clip = engine._apply_rotation(clip)
    
    # 텍스트 오버레이는 폰트 문제로 임시 비활성화
    # if engine.config.enable_text_overlay:
    #     clip = engine._add_text_overlay(clip, image_path)
    
    return clip



def apply_enhanced_ken_burns(engine, clip: ImageClip) -> ImageClip:
    """
    향상된 Ken Burns 효과 (이징 함수 적용)
    
    Args:
        engine: ReelsEngine 인스턴스
        clip: 원본 클립
    
    Returns:
        효과가 적용된 클립
    """
    duration = clip.duration
    
    # 효과 강도 설정
    intensity_map = {
        "low": 0.05,
        "medium": 0.15,
        "high": 0.30
    }
    intensity = intensity_map.get(engine.config.effect_intensity, 0.15)
    
    # 이징 함수 가져오기
    easing_func = get_easing_function(engine.config.easing_function)
    
    # Ken Burns 스타일 선택
    style = engine.config.ken_burns_style
    if style == "random":
        style = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right", "diagonal"])
    
    # 스타일별 효과 적용
    if style == "zoom_in":
        def effect(get_frame, t):
            # 이징 적용
            progress = easing_func(t / duration)
            zoom = 1.0 + progress * intensity
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            new_h, new_w = int(h * zoom), int(w * zoom)
            
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
        def effect(get_frame, t):
            # 이징 적용
            progress = easing_func(t / duration)
            zoom = (1.0 + intensity) - progress * intensity
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            new_h, new_w = int(h * zoom), int(w * zoom)
            
            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
            img = Image.fromarray(frame_uint8)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img_cropped = img_resized.crop((left, top, left + w, top + h))
            
            return np.array(img_cropped)
        
        return clip.transform(effect)
    
    elif style == "diagonal":
        direction = random.choice(["top_left", "top_right", "bottom_left", "bottom_right"])
        
        def effect(get_frame, t):
            # 이징 적용
            progress = easing_func(t / duration)
            zoom = 1.0 + progress * intensity
            
            frame = get_frame(t)
            h, w = frame.shape[:2]
            new_h, new_w = int(h * zoom), int(w * zoom)
            
            frame_uint8 = (frame * 255).astype(np.uint8) if frame.dtype == np.float64 or frame.dtype == np.float32 else frame
            img = Image.fromarray(frame_uint8)
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            
            target_w, target_h = engine.target_size
            
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
        # 기본: 원래 메서드 사용
        return engine._apply_ken_burns(clip)


def patch_reels_engine():
    """
    ReelsEngine 클래스에 향상된 메서드 패치
    """
    from reels_engine import ReelsEngine
    
    # 원본 _create_clip 백업
    ReelsEngine._create_clip_original = ReelsEngine._create_clip
    
    # 향상된 _create_clip으로 교체
    ReelsEngine._create_clip = lambda self, image_path: create_enhanced_clip(self, image_path)
    
    print("[패치] ReelsEngine에 향상된 기능 적용 완료")
