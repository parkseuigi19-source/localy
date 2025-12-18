import imagehash
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Form

from geopy.distance import geodesic
from ultralytics import YOLO

from mission_db import (
    mission_status,
    mission_location,
    mission_hash,
    mission_type,
)

router = APIRouter()

# YOLO (food 미션시 감지된 음식 보여주기 용도)
yolo_model = YOLO("yolov8n.pt")


#  GPS 검사
def gps_within_radius(user_lat, user_lng, target_lat, target_lng, radius=50):
    distance_m = geodesic((user_lat, user_lng), (target_lat, target_lng)).meters
    gps_noise = 10
    return distance_m <= (radius + gps_noise), round(distance_m, 2)



#  이미지 유사도 검사 (phash)
def image_similarity(mission_id, check_path):
    origin_hash = mission_hash.get(mission_id)
    if origin_hash is None:
        return 100

    new_hash = imagehash.phash(Image.open(check_path))
    diff = origin_hash - new_hash
    similarity = 100 - (diff / 64 * 100)
    return round(similarity, 2)



#  YOLO 객체 분석
def run_yolo(image_path):
    results = yolo_model(image_path)
    r = results[0]
    names = r.names
    return [names[int(c)] for c in r.boxes.cls]



#  미션 체크 (랜드마크/음식 모두 유사도 검사)
@router.post("/mission/check")
def mission_check(
    mission_id: str = Form(...),
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):

    # 미션 준비 상태
    if mission_status.get(mission_id) != "done":
        return {"error": "mission not ready"}

    # GPS 검사
    target = mission_location.get(mission_id)
    gps_ok, real_distance = gps_within_radius(
        latitude, longitude,
        target["latitude"], target["longitude"],
        radius=50
    )

    # 체크 이미지 저장
    check_path = f"mission/{mission_id}_check.jpg"
    with open(check_path, "wb") as f:
        f.write(file.file.read())

    # YOLO 감지 (food/landmark 참고용)
    detected_objects = run_yolo(check_path)

    # 공통: 원본 vs 체크 이미지 유사도
    similarity = image_similarity(mission_id, check_path)
    similarity_ok = similarity >= 70

    # 미션 타입
    m_type = mission_type.get(mission_id)

    # 성공 판정
    if m_type in ("landmark", "food"):
        success = gps_ok and similarity_ok
    elif m_type == "location":
        success = gps_ok
    else:
        success = False

    return {
        "mission_id": mission_id,
        "mission_type": m_type,
        "gps_ok": gps_ok,
        "distance_m": real_distance,
        "similarity": similarity,
        "similarity_ok": similarity_ok,
        "detected_objects": detected_objects,
        "success": success
    }
