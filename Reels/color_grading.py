"""
색상 그레이딩 유틸리티
AI 분석 결과에 따라 자동으로 색상 필터 적용
"""
import numpy as np
import cv2
from typing import Dict, Any, Optional
from PIL import Image


class ColorGrading:
    """색상 그레이딩 클래스"""
    
    # 분위기별 색상 필터 프리셋
    PRESETS = {
        "sunset": {
            "name": "일몰/따뜻한 톤",
            "temperature": 20,  # 따뜻하게
            "saturation": 1.2,
            "brightness": 1.05,
            "contrast": 1.1,
            "tint": (1.1, 1.0, 0.9)  # R, G, B 배율
        },
        "ocean": {
            "name": "바다/시원한 톤",
            "temperature": -15,  # 차갑게
            "saturation": 1.15,
            "brightness": 1.0,
            "contrast": 1.05,
            "tint": (0.9, 1.0, 1.15)
        },
        "forest": {
            "name": "숲/자연스러운 톤",
            "temperature": 0,
            "saturation": 1.25,
            "brightness": 0.95,
            "contrast": 1.1,
            "tint": (0.95, 1.1, 0.95)
        },
        "city": {
            "name": "도시/현대적인 톤",
            "temperature": -5,
            "saturation": 0.9,
            "brightness": 1.0,
            "contrast": 1.2,
            "tint": (1.0, 1.0, 1.05)
        },
        "vintage": {
            "name": "빈티지/복고풍",
            "temperature": 10,
            "saturation": 0.8,
            "brightness": 0.95,
            "contrast": 1.15,
            "tint": (1.1, 1.05, 0.9)
        },
        "dramatic": {
            "name": "드라마틱/강렬한",
            "temperature": 0,
            "saturation": 1.3,
            "brightness": 0.9,
            "contrast": 1.3,
            "tint": (1.0, 1.0, 1.0)
        },
        "soft": {
            "name": "부드러운/파스텔",
            "temperature": 5,
            "saturation": 0.85,
            "brightness": 1.1,
            "contrast": 0.9,
            "tint": (1.05, 1.05, 1.05)
        },
        "neutral": {
            "name": "중립/자연스러운",
            "temperature": 0,
            "saturation": 1.0,
            "brightness": 1.0,
            "contrast": 1.0,
            "tint": (1.0, 1.0, 1.0)
        }
    }
    
    @staticmethod
    def detect_mood_from_ai_analysis(ai_content: Optional[Dict[str, Any]]) -> str:
        """
        AI 분석 결과에서 분위기 감지
        
        Args:
            ai_content: AI 분석 결과
        
        Returns:
            분위기 키 (preset 이름)
        """
        if not ai_content or "analysis" not in ai_content:
            return "neutral"
        
        analysis = ai_content["analysis"]
        
        # 분석 텍스트에서 키워드 검색
        text = str(analysis).lower()
        
        if any(word in text for word in ["sunset", "일몰", "저녁", "노을", "golden hour"]):
            return "sunset"
        elif any(word in text for word in ["ocean", "sea", "beach", "바다", "해변", "물"]):
            return "ocean"
        elif any(word in text for word in ["forest", "nature", "green", "숲", "자연", "나무"]):
            return "forest"
        elif any(word in text for word in ["city", "urban", "building", "도시", "건물", "거리"]):
            return "city"
        elif any(word in text for word in ["vintage", "retro", "old", "빈티지", "복고", "옛날"]):
            return "vintage"
        elif any(word in text for word in ["dramatic", "intense", "strong", "드라마틱", "강렬", "역동"]):
            return "dramatic"
        elif any(word in text for word in ["soft", "gentle", "calm", "부드러운", "차분", "평화"]):
            return "soft"
        else:
            return "neutral"
    
    @staticmethod
    def apply_color_grading(
        frame: np.ndarray,
        preset_name: str = "neutral",
        intensity: float = 1.0
    ) -> np.ndarray:
        """
        색상 그레이딩 적용
        
        Args:
            frame: 입력 프레임
            preset_name: 프리셋 이름
            intensity: 효과 강도 (0.0 ~ 1.0)
        
        Returns:
            색상 그레이딩이 적용된 프레임
        """
        # float to uint8 변환
        if frame.dtype == np.float64 or frame.dtype == np.float32:
            frame = (frame * 255).astype(np.uint8)
        
        # 프리셋 가져오기
        preset = ColorGrading.PRESETS.get(preset_name, ColorGrading.PRESETS["neutral"])
        
        # 강도 조절
        temperature = preset["temperature"] * intensity
        saturation = 1.0 + (preset["saturation"] - 1.0) * intensity
        brightness = 1.0 + (preset["brightness"] - 1.0) * intensity
        contrast = 1.0 + (preset["contrast"] - 1.0) * intensity
        tint_r, tint_g, tint_b = preset["tint"]
        tint_r = 1.0 + (tint_r - 1.0) * intensity
        tint_g = 1.0 + (tint_g - 1.0) * intensity
        tint_b = 1.0 + (tint_b - 1.0) * intensity
        
        result = frame.copy().astype(np.float32)
        
        # 1. 색온도 조정
        if temperature != 0:
            result[:, :, 2] = np.clip(result[:, :, 2] + temperature, 0, 255)  # R 채널
            result[:, :, 0] = np.clip(result[:, :, 0] - temperature, 0, 255)  # B 채널
        
        # 2. 틴트 적용 (RGB 배율)
        result[:, :, 2] *= tint_r  # R
        result[:, :, 1] *= tint_g  # G
        result[:, :, 0] *= tint_b  # B
        result = np.clip(result, 0, 255)
        
        # 3. 채도 조정
        if saturation != 1.0:
            hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] *= saturation
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        
        # 4. 밝기 조정
        if brightness != 1.0:
            result *= brightness
            result = np.clip(result, 0, 255)
        
        # 5. 대비 조정
        if contrast != 1.0:
            mean = np.mean(result)
            result = (result - mean) * contrast + mean
            result = np.clip(result, 0, 255)
        
        return result.astype(np.uint8)
    
    @staticmethod
    def apply_vignette(frame: np.ndarray, intensity: float = 0.3) -> np.ndarray:
        """
        비네팅 효과 적용 (가장자리 어둡게)
        
        Args:
            frame: 입력 프레임
            intensity: 효과 강도 (0.0 ~ 1.0)
        
        Returns:
            비네팅이 적용된 프레임
        """
        if frame.dtype == np.float64 or frame.dtype == np.float32:
            frame = (frame * 255).astype(np.uint8)
        
        h, w = frame.shape[:2]
        
        # 중심으로부터의 거리 계산
        y, x = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        
        # 정규화된 거리 (0 ~ 1)
        max_dist = np.sqrt(cx**2 + cy**2)
        dist = np.sqrt((x - cx)**2 + (y - cy)**2) / max_dist
        
        # 비네팅 마스크 생성
        vignette = 1 - (dist * intensity)
        vignette = np.clip(vignette, 0, 1)
        
        # 3채널로 확장
        vignette_3ch = np.stack([vignette, vignette, vignette], axis=2)
        
        # 적용
        result = (frame.astype(np.float32) * vignette_3ch).astype(np.uint8)
        
        return result
    
    @staticmethod
    def apply_film_grain(frame: np.ndarray, intensity: float = 0.05) -> np.ndarray:
        """
        필름 그레인 효과 적용 (빈티지 느낌)
        
        Args:
            frame: 입력 프레임
            intensity: 효과 강도 (0.0 ~ 1.0)
        
        Returns:
            필름 그레인이 적용된 프레임
        """
        if frame.dtype == np.float64 or frame.dtype == np.float32:
            frame = (frame * 255).astype(np.uint8)
        
        h, w = frame.shape[:2]
        
        # 노이즈 생성
        noise = np.random.randn(h, w, 3) * 255 * intensity
        
        # 프레임에 노이즈 추가
        result = frame.astype(np.float32) + noise
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result


def apply_auto_color_grading(
    frame: np.ndarray,
    ai_content: Optional[Dict[str, Any]] = None,
    intensity: float = 0.7
) -> np.ndarray:
    """
    AI 분석 결과에 따라 자동으로 색상 그레이딩 적용
    
    Args:
        frame: 입력 프레임
        ai_content: AI 분석 결과
        intensity: 효과 강도 (0.0 ~ 1.0)
    
    Returns:
        색상 그레이딩이 적용된 프레임
    """
    # 분위기 감지
    mood = ColorGrading.detect_mood_from_ai_analysis(ai_content)
    
    # 색상 그레이딩 적용
    result = ColorGrading.apply_color_grading(frame, mood, intensity)
    
    # 비네팅 추가 (선택적)
    if mood in ["dramatic", "vintage", "sunset"]:
        result = ColorGrading.apply_vignette(result, intensity * 0.3)
    
    # 필름 그레인 추가 (빈티지만)
    if mood == "vintage":
        result = ColorGrading.apply_film_grain(result, intensity * 0.05)
    
    return result
