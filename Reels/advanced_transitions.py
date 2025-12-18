"""
고급 전환 효과 모음
Morph, Glitch, Circular Wipe, Page Curl 등
"""
import numpy as np
from PIL import Image
import random
import cv2
from typing import Tuple, Optional


def apply_morph_transition(frame1: np.ndarray, frame2: np.ndarray, progress: float) -> np.ndarray:
    """
    Morph 전환: 두 이미지를 부드럽게 혼합
    
    Args:
        frame1: 첫 번째 프레임
        frame2: 두 번째 프레임
        progress: 진행률 (0.0 ~ 1.0)
    
    Returns:
        혼합된 프레임
    """
    # float to uint8 변환
    if frame1.dtype == np.float64 or frame1.dtype == np.float32:
        frame1 = (frame1 * 255).astype(np.uint8)
    if frame2.dtype == np.float64 or frame2.dtype == np.float32:
        frame2 = (frame2 * 255).astype(np.uint8)
    
    # 알파 블렌딩
    alpha = progress
    result = cv2.addWeighted(frame1, 1 - alpha, frame2, alpha, 0)
    
    return result


def apply_glitch_transition(frame: np.ndarray, progress: float, intensity: float = 0.5) -> np.ndarray:
    """
    Glitch 전환: 디지털 노이즈 효과
    
    Args:
        frame: 입력 프레임
        progress: 진행률 (0.0 ~ 1.0)
        intensity: 효과 강도 (0.0 ~ 1.0)
    
    Returns:
        Glitch 효과가 적용된 프레임
    """
    # float to uint8 변환
    if frame.dtype == np.float64 or frame.dtype == np.float32:
        frame = (frame * 255).astype(np.uint8)
    
    result = frame.copy()
    h, w = frame.shape[:2]
    
    # 진행률에 따라 glitch 강도 조절
    glitch_amount = int(intensity * progress * 10)
    
    for _ in range(glitch_amount):
        # 랜덤 위치에 수평 라인 왜곡
        y = random.randint(0, h - 1)
        shift = random.randint(-int(w * 0.1), int(w * 0.1))
        
        if shift > 0:
            result[y, shift:] = frame[y, :-shift]
        elif shift < 0:
            result[y, :shift] = frame[y, -shift:]
        
        # RGB 채널 분리 효과
        if random.random() < 0.3:
            channel = random.randint(0, 2)
            offset = random.randint(-5, 5)
            if offset > 0:
                result[y, offset:, channel] = frame[y, :-offset, channel]
            elif offset < 0:
                result[y, :offset, channel] = frame[y, -offset:, channel]
    
    return result


def create_circular_mask(size: Tuple[int, int], center: Tuple[int, int], radius: float) -> np.ndarray:
    """
    원형 마스크 생성
    
    Args:
        size: 마스크 크기 (width, height)
        center: 원의 중심 (x, y)
        radius: 반지름
    
    Returns:
        원형 마스크 (0 ~ 255)
    """
    w, h = size
    cx, cy = center
    
    # 좌표 그리드 생성
    y, x = np.ogrid[:h, :w]
    
    # 중심으로부터의 거리 계산
    dist_from_center = np.sqrt((x - cx)**2 + (y - cy)**2)
    
    # 원형 마스크 생성
    mask = (dist_from_center <= radius).astype(np.uint8) * 255
    
    return mask


def apply_circular_wipe_transition(
    frame1: np.ndarray,
    frame2: np.ndarray,
    progress: float,
    center: Optional[Tuple[int, int]] = None
) -> np.ndarray:
    """
    Circular Wipe 전환: 원형으로 확장되는 전환
    
    Args:
        frame1: 첫 번째 프레임
        frame2: 두 번째 프레임
        progress: 진행률 (0.0 ~ 1.0)
        center: 원의 중심 (None이면 화면 중앙)
    
    Returns:
        전환 효과가 적용된 프레임
    """
    # float to uint8 변환
    if frame1.dtype == np.float64 or frame1.dtype == np.float32:
        frame1 = (frame1 * 255).astype(np.uint8)
    if frame2.dtype == np.float64 or frame2.dtype == np.float32:
        frame2 = (frame2 * 255).astype(np.uint8)
    
    h, w = frame1.shape[:2]
    
    # 중심 설정
    if center is None:
        center = (w // 2, h // 2)
    
    # 최대 반지름 계산 (화면 대각선)
    max_radius = np.sqrt(w**2 + h**2) / 2
    
    # 현재 반지름
    current_radius = max_radius * progress
    
    # 원형 마스크 생성
    mask = create_circular_mask((w, h), center, current_radius)
    
    # 마스크를 3채널로 확장
    mask_3ch = np.stack([mask, mask, mask], axis=2)
    
    # 마스크 적용
    result = np.where(mask_3ch > 0, frame2, frame1)
    
    return result


def apply_page_curl_transition(
    frame1: np.ndarray,
    frame2: np.ndarray,
    progress: float,
    direction: str = "right"
) -> np.ndarray:
    """
    Page Curl 전환: 페이지 넘기는 효과 (간소화 버전)
    
    Args:
        frame1: 첫 번째 프레임
        frame2: 두 번째 프레임
        progress: 진행률 (0.0 ~ 1.0)
        direction: 넘기는 방향 ("left", "right", "up", "down")
    
    Returns:
        전환 효과가 적용된 프레임
    """
    # float to uint8 변환
    if frame1.dtype == np.float64 or frame1.dtype == np.float32:
        frame1 = (frame1 * 255).astype(np.uint8)
    if frame2.dtype == np.float64 or frame2.dtype == np.float32:
        frame2 = (frame2 * 255).astype(np.uint8)
    
    h, w = frame1.shape[:2]
    result = frame1.copy()
    
    if direction == "right":
        # 오른쪽으로 넘기기
        split_x = int(w * progress)
        result[:, :split_x] = frame2[:, :split_x]
        
        # 그림자 효과 (간단한 그라데이션)
        if split_x < w - 10:
            shadow_width = 10
            for i in range(shadow_width):
                if split_x + i < w:
                    alpha = (shadow_width - i) / shadow_width * 0.3
                    result[:, split_x + i] = (result[:, split_x + i] * (1 - alpha)).astype(np.uint8)
    
    elif direction == "left":
        # 왼쪽으로 넘기기
        split_x = int(w * (1 - progress))
        result[:, split_x:] = frame2[:, split_x:]
        
        if split_x > 10:
            shadow_width = 10
            for i in range(shadow_width):
                if split_x - i - 1 >= 0:
                    alpha = (shadow_width - i) / shadow_width * 0.3
                    result[:, split_x - i - 1] = (result[:, split_x - i - 1] * (1 - alpha)).astype(np.uint8)
    
    elif direction == "down":
        # 아래로 넘기기
        split_y = int(h * progress)
        result[:split_y, :] = frame2[:split_y, :]
        
        if split_y < h - 10:
            shadow_height = 10
            for i in range(shadow_height):
                if split_y + i < h:
                    alpha = (shadow_height - i) / shadow_height * 0.3
                    result[split_y + i, :] = (result[split_y + i, :] * (1 - alpha)).astype(np.uint8)
    
    elif direction == "up":
        # 위로 넘기기
        split_y = int(h * (1 - progress))
        result[split_y:, :] = frame2[split_y:, :]
        
        if split_y > 10:
            shadow_height = 10
            for i in range(shadow_height):
                if split_y - i - 1 >= 0:
                    alpha = (shadow_height - i) / shadow_height * 0.3
                    result[split_y - i - 1, :] = (result[split_y - i - 1, :] * (1 - alpha)).astype(np.uint8)
    
    return result



