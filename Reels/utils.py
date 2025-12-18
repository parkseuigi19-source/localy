"""
유틸리티 함수 모음
"""
from PIL import Image
import piexif
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


def extract_exif_data(image_path: Path) -> Dict[str, Any]:
    """
    이미지에서 EXIF 데이터 추출
    
    Args:
        image_path: 이미지 파일 경로
        
    Returns:
        EXIF 데이터 딕셔너리
    """
    exif_data = {
        "datetime": None,
        "gps": None,
        "camera": None,
        "location_name": None,
    }
    
    try:
        img = Image.open(image_path)
        
        if "exif" not in img.info:
            return exif_data
        
        exif_dict = piexif.load(img.info["exif"])
        
        # 촬영 날짜/시간
        if piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            datetime_str = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal].decode()
            try:
                exif_data["datetime"] = datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")
            except:
                pass
        
        # GPS 정보
        if "GPS" in exif_dict and exif_dict["GPS"]:
            gps = exif_dict["GPS"]
            
            if piexif.GPSIFD.GPSLatitude in gps and piexif.GPSIFD.GPSLongitude in gps:
                lat = _convert_gps_to_decimal(gps[piexif.GPSIFD.GPSLatitude])
                lon = _convert_gps_to_decimal(gps[piexif.GPSIFD.GPSLongitude])
                
                # 남/북, 동/서 방향
                if piexif.GPSIFD.GPSLatitudeRef in gps:
                    lat_ref = gps[piexif.GPSIFD.GPSLatitudeRef].decode()
                    if lat_ref == "S":
                        lat = -lat
                
                if piexif.GPSIFD.GPSLongitudeRef in gps:
                    lon_ref = gps[piexif.GPSIFD.GPSLongitudeRef].decode()
                    if lon_ref == "W":
                        lon = -lon
                
                exif_data["gps"] = {"latitude": lat, "longitude": lon}
        
        # 카메라 정보
        if piexif.ImageIFD.Make in exif_dict["0th"]:
            make = exif_dict["0th"][piexif.ImageIFD.Make].decode()
            model = ""
            if piexif.ImageIFD.Model in exif_dict["0th"]:
                model = exif_dict["0th"][piexif.ImageIFD.Model].decode()
            exif_data["camera"] = f"{make} {model}".strip()
    
    except Exception as e:
        print(f"EXIF 추출 오류 ({image_path.name}): {e}")
    
    return exif_data


def _convert_gps_to_decimal(gps_coord: Tuple) -> float:
    """GPS 좌표를 십진수로 변환"""
    degrees = gps_coord[0][0] / gps_coord[0][1]
    minutes = gps_coord[1][0] / gps_coord[1][1]
    seconds = gps_coord[2][0] / gps_coord[2][1]
    return degrees + (minutes / 60.0) + (seconds / 3600.0)


def sort_photos_by_time(photo_paths: List[Path]) -> List[Path]:
    """
    사진을 촬영 시간순으로 정렬
    
    Args:
        photo_paths: 사진 파일 경로 리스트
        
    Returns:
        정렬된 사진 파일 경로 리스트
    """
    photos_with_time = []
    
    for path in photo_paths:
        exif_data = extract_exif_data(path)
        datetime_taken = exif_data.get("datetime")
        
        # EXIF에 날짜가 없으면 파일 수정 시간 사용
        if datetime_taken is None:
            datetime_taken = datetime.fromtimestamp(path.stat().st_mtime)
        
        photos_with_time.append((path, datetime_taken))
    
    # 시간순 정렬
    photos_with_time.sort(key=lambda x: x[1])
    
    return [path for path, _ in photos_with_time]


def validate_image(image_path: Path) -> bool:
    """
    이미지 유효성 검사
    
    Args:
        image_path: 이미지 파일 경로
        
    Returns:
        유효한 이미지 여부
    """
    try:
        img = Image.open(image_path)
        img.verify()  # 이미지 검증
        return True
    except Exception as e:
        print(f"이미지 검증 실패 ({image_path.name}): {e}")
        return False


def get_image_quality_score(image_path: Path) -> float:
    """
    이미지 품질 점수 계산 (간단한 버전)
    
    Args:
        image_path: 이미지 파일 경로
        
    Returns:
        품질 점수 (0.0 ~ 1.0)
    """
    try:
        img = Image.open(image_path)
        
        # 해상도 점수 (높을수록 좋음)
        width, height = img.size
        resolution_score = min((width * height) / (1920 * 1080), 1.0)
        
        # 파일 크기 점수 (너무 작으면 압축이 심한 것)
        file_size_mb = image_path.stat().st_size / (1024 * 1024)
        size_score = min(file_size_mb / 2.0, 1.0)  # 2MB 이상이면 만점
        
        # 종합 점수
        quality_score = (resolution_score * 0.7 + size_score * 0.3)
        
        return quality_score
    
    except Exception as e:
        print(f"품질 점수 계산 실패 ({image_path.name}): {e}")
        return 0.5  # 기본값


def get_location_name_from_gps(latitude: float, longitude: float) -> Optional[str]:
    """
    GPS 좌표로부터 위치 이름 가져오기 (역지오코딩)
    
    Note: 실제 구현을 위해서는 Google Maps API 또는 Nominatim 등의 서비스 필요
    현재는 플레이스홀더
    
    Args:
        latitude: 위도
        longitude: 경도
        
    Returns:
        위치 이름 또는 None
    """
    # TODO: 실제 역지오코딩 API 연동
    # 예: Google Maps Geocoding API, Nominatim 등
    return None


def format_datetime_korean(dt: datetime) -> str:
    """
    날짜/시간을 한국어 형식으로 포맷
    
    Args:
        dt: datetime 객체
        
    Returns:
        포맷된 문자열 (예: "2024년 12월 1일")
    """
    return dt.strftime("%Y년 %m월 %d일")
