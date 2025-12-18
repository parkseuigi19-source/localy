import uuid
import os
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from mission_check import router as mission_check_router
from mission_db import mission_status, mission_location, mission_hash, mission_type, mission_target_objects

import imagehash
from PIL import Image


# FastAPI 인스턴스 생성
app = FastAPI()

# CORS 설정 (프론트 테스트용 전체 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     
    allow_credentials=True,
    allow_methods=["*"],      
    allow_headers=["*"],      
)

# Static 폴더 연결
app.mount("/static", StaticFiles(directory="static"), name="static")

# root → test.html 자동 연결
@app.get("/")
def root():
    return FileResponse("static/test.html")

# mission_check 라우터 포함
app.include_router(mission_check_router)

# mission 이미지 저장 폴더 생성
os.makedirs("mission", exist_ok=True)


# 비동기 해시 생성
async def process_mission(mission_id: str, origin_path: str):
    try:
        h = imagehash.phash(Image.open(origin_path))
        mission_hash[mission_id] = h
        await asyncio.sleep(1)
        mission_status[mission_id] = "done"
    except Exception as e:
        mission_status[mission_id] = "error"
        print("Hash error:", e)

# 1) 미션 업로드
@app.post("/upload")
async def upload_mission(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    mission_kind: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    target_objects : str = Form("")
):

    mission_id = str(uuid.uuid4())

    mission_status[mission_id] = "pending"
    mission_location[mission_id] = {"latitude": latitude, "longitude": longitude}
    mission_type[mission_id] = mission_kind

    # 음식 미션일 때 타겟 음식 저장
    if mission_kind == "food" and target_objects.strip() != "":
        mission_target_objects[mission_id] = [
            item.strip() for item in target_objects.split(",") if item.strip()
        ]
    else:
        mission_target_objects[mission_id] = []

    # 원본 이미지 저장
    origin_path = f"mission/{mission_id}_origin.jpg"
    content = await file.read()
    with open(origin_path, "wb") as f:
        f.write(content)

    # 비동기 처리
    background_tasks.add_task(process_mission, mission_id, origin_path)

    return {
        "mission_id": mission_id,
        "mission_kind": mission_kind,
        "status": "pending",
        "location": mission_location[mission_id],
        "target_objects": mission_target_objects[mission_id]
    }

# 2) 상태 확인
@app.get("/status/{mission_id}")
def get_status(mission_id: str):
    return {
        "mission_id": mission_id,
        "status": mission_status.get(mission_id, "not_found"),
        "location": mission_location.get(mission_id),
        "mission_kind": mission_type.get(mission_id),
        "target_objects" : mission_target_objects(mission_id, [])
    }
