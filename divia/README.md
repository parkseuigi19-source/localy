# DIVIA (Digital Vision Interaction Assistant)

DIVIA는 GPS 정보와 이미지 분석을 결합하여 위치 기반 미션을 검증하는 시스템입니다. 사용자가 특정 장소에서 목표물을 촬영하면, 시스템은 GPS 좌표의 일치 여부와 이미지의 유사성, 그리고 객체 탐지 기술을 활용하여 미션의 성공 여부를 판정합니다.

---

## 🚀 주요 기능

### 1. 미션 업로드 및 관리
- **미션 등록**: 관리자가 목표 위치(위도, 경도)와 미션 종류(음식, 랜드마크, 일반 장소)를 설정하고 기준 이미지를 업로드합니다.
- **이미지 분석**: 업로드된 이미지에서 `imagehash` (phash)를 사용하여 고유한 해시값을 생성하고 저장합니다.

### 2. 미션 검증 (`/mission/check`)
- **GPS 검증**: 사용자의 현재 위치가 목표 지점으로부터 지정된 반경(기본 50m) 내에 있는지 확인합니다.
- **이미지 유사도 분석**: 사용자가 촬영한 이미지와 기준 이미지의 phash 값을 비교하여 유사도를 측정합니다.
- **객체 탐지 (YOLOv8)**: YOLOv8 모델을 사용하여 촬영된 이미지 내에 특정 객체(예: 특정 음식)가 포함되어 있는지 분석합니다.

---

## 🛠 기술 스택

- **Backend**: Python 3.9+, FastAPI
- **AI/ML**: YOLOv8 (ultralytics), imagehash
- **Geospatial**: geopy (geodesic distance)
- **Image Processing**: Pillow (PIL)
- **Server**: Uvicorn

---

## 📂 파일 구조

```text
c:\AIX\divia\
├── main.py              # FastAPI 메인 서버, 미션 업로드 및 상태 관리
├── mission_check.py     # GPS, 이미지 유사도, YOLO 분석 로직 및 라우터
├── mission_db.py        # 인메모리 데이터 저장소 (미션 정보 관리)
├── mission/             # 미션 이미지 및 체크 이미지가 저장되는 폴더
├── static/              # 정적 파일 (테스트용 HTML 등)
└── yolov8n.pt           # YOLOv8 Nano 사전 학습 모델
```

---

## ⚙️ 설치 및 실행 방법

### 1. 필수 라이브러리 설치
```bash
pip install fastapi uvicorn ultralytics geopy imagehash pillow python-multipart
```

### 2. 서버 실행
```bash
python main.py
# 또는
uvicorn main:app --reload
```

---

## 📝 API 엔드포인트

### `POST /upload`
- 미션을 새로 생성하고 기준 이미지를 등록합니다.
- **Parameters**: `file`, `mission_kind`, `latitude`, `longitude`, `target_objects`

### `GET /status/{mission_id}`
- 생성된 미션의 현재 상태 및 정보를 확인합니다.

### `POST /mission/check`
- 사용자가 수행한 미션의 결과(이미지, GPS)를 전송하여 성공 여부를 검증받습니다.
- **Parameters**: `mission_id`, `file`, `latitude`, `longitude`
