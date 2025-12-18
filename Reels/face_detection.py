"""
얼굴 감지 및 스마트 크롭 유틸리티
OpenCV를 사용한 CPU 전용 얼굴 감지
"""
from pathlib import Path
from typing import Optional, Tuple, List
import cv2
import numpy as np
from PIL import Image


class FaceDetector:
    """얼굴 감지 클래스"""
    
    def __init__(self):
        """
        Haar Cascade 분류기 초기화
        """
        # OpenCV에 내장된 Haar Cascade 모델 사용 (CPU 전용)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            print("[경고] Haar Cascade 모델을 로드할 수 없습니다.")
    
    def detect_faces(self, image_path: Path) -> List[Tuple[int, int, int, int]]:
        """
        이미지에서 얼굴 감지
        
        Args:
            image_path: 이미지 파일 경로
        
        Returns:
            얼굴 영역 리스트 [(x, y, w, h), ...]
        """
        try:
            # 이미지 로드
            img = cv2.imread(str(image_path))
            if img is None:
                return []
            
            # 그레이스케일 변환 (얼굴 감지 성능 향상)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 얼굴 감지
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
        
        except Exception as e:
            print(f"[얼굴 감지 오류] {image_path.name}: {e}")
            return []
    
    def get_focus_point(self, image_path: Path, image_size: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """
        이미지의 포커스 포인트 계산 (얼굴 중심 또는 이미지 중심)
        
        Args:
            image_path: 이미지 파일 경로
            image_size: 이미지 크기 (width, height)
        
        Returns:
            포커스 포인트 (x, y) 또는 None
        """
        faces = self.detect_faces(image_path)
        
        if faces:
            # 얼굴이 있으면 가장 큰 얼굴의 중심 반환
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            focus_x = x + w // 2
            focus_y = y + h // 2
            return (focus_x, focus_y)
        else:
            # 얼굴이 없으면 이미지 중심 반환
            width, height = image_size
            return (width // 2, height // 2)
    
    def get_smart_crop_region(
        self,
        image_path: Path,
        target_size: Tuple[int, int],
        focus_on_faces: bool = True
    ) -> Tuple[int, int, int, int]:
        """
        스마트 크롭 영역 계산
        
        Args:
            image_path: 이미지 파일 경로
            target_size: 목표 크기 (width, height)
            focus_on_faces: 얼굴에 포커스할지 여부
        
        Returns:
            크롭 영역 (left, top, right, bottom)
        """
        try:
            # 이미지 로드
            img = Image.open(image_path)
            img_w, img_h = img.size
            target_w, target_h = target_size
            
            # 비율 계산
            scale_x = target_w / img_w
            scale_y = target_h / img_h
            scale = max(scale_x, scale_y)
            
            # 리사이즈 후 크기
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            
            if focus_on_faces:
                # 얼굴 감지
                focus_point = self.get_focus_point(image_path, (img_w, img_h))
                
                if focus_point:
                    focus_x, focus_y = focus_point
                    
                    # 스케일 적용
                    focus_x = int(focus_x * scale)
                    focus_y = int(focus_y * scale)
                    
                    # 크롭 영역 계산 (포커스 포인트 중심)
                    left = max(0, focus_x - target_w // 2)
                    top = max(0, focus_y - target_h // 2)
                    
                    # 경계 체크
                    if left + target_w > new_w:
                        left = new_w - target_w
                    if top + target_h > new_h:
                        top = new_h - target_h
                    
                    return (left, top, left + target_w, top + target_h)
            
            # 기본: 중앙 크롭
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            return (left, top, left + target_w, top + target_h)
        
        except Exception as e:
            print(f"[스마트 크롭 오류] {image_path.name}: {e}")
            # 폴백: 중앙 크롭
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            return (left, top, left + target_w, top + target_h)
    
    def analyze_image_importance(self, image_path: Path) -> float:
        """
        이미지 중요도 분석 (얼굴 개수 및 크기 기반)
        
        Args:
            image_path: 이미지 파일 경로
        
        Returns:
            중요도 점수 (0.0 ~ 1.0)
        """
        faces = self.detect_faces(image_path)
        
        if not faces:
            return 0.5  # 기본 중요도
        
        # 얼굴 개수와 크기로 중요도 계산
        try:
            img = Image.open(image_path)
            img_area = img.size[0] * img.size[1]
            
            # 얼굴 영역 비율 계산
            face_areas = [w * h for (x, y, w, h) in faces]
            total_face_area = sum(face_areas)
            face_ratio = total_face_area / img_area
            
            # 중요도 계산
            # - 얼굴 개수: 1-3개가 최적
            # - 얼굴 비율: 10-30%가 최적
            face_count_score = min(len(faces) / 3.0, 1.0)
            face_ratio_score = min(face_ratio / 0.3, 1.0)
            
            importance = (face_count_score * 0.6 + face_ratio_score * 0.4)
            return min(max(importance, 0.5), 1.0)  # 0.5 ~ 1.0 범위
        
        except Exception as e:
            print(f"[중요도 분석 오류] {image_path.name}: {e}")
            return 0.5


def adjust_duration_by_importance(
    base_duration: int,
    importance: float,
    min_duration: int = 2,
    max_duration: int = 6
) -> int:
    """
    중요도에 따라 지속 시간 조정
    
    Args:
        base_duration: 기본 지속 시간
        importance: 중요도 (0.0 ~ 1.0)
        min_duration: 최소 지속 시간
        max_duration: 최대 지속 시간
    
    Returns:
        조정된 지속 시간
    """
    # 중요도가 높을수록 더 길게 표시
    adjusted = base_duration + (importance - 0.5) * 2
    return int(max(min_duration, min(adjusted, max_duration)))
