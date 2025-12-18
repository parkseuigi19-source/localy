# 🎬 여행 릴스 자동 생성기

여행 사진으로 자동으로 Instagram Reels를 만들어주는 프로그램입니다!

## ✨ 주요 기능

### 기본 기능
- 📸 **자동 정렬**: EXIF 데이터를 읽어 촬영 시간순으로 자동 정렬
- 🎥 **Ken Burns 효과**: 부드러운 줌 인/아웃, 패닝 등 다양한 카메라 움직임
- 🌈 **전환 효과**: 사진 간 자연스러운 페이드, 슬라이드, 줌 전환
- 📱 **Instagram Reels 최적화**: 9:16 세로 비율 (1080x1920)
- 🎨 **고화질 인코딩**: CRF 18, 8000k bitrate로 거의 무손실 수준

### 🤖 AI 기능 (NEW!)
- 🔍 **AI 이미지 분석**: GPT-4 Vision으로 각 사진의 내용을 자동 분석
- ✨ **AI 텍스트 오버레이**: 사진마다 AI가 생성한 감성적인 텍스트 자동 추가
  - 3가지 스타일: descriptive (설명형), poetic (감성형), simple (간결형)
  - 예: "황금빛 추억", "바다와 함께하는 여름날", "행복한 웃음소리"
- 📝 **AI 스토리 자막**: AI가 생성한 여행 스토리를 화면에 표시
- 🎙️ **음성 나레이션**: OpenAI TTS로 자연스러운 한국어 나레이션 추가

### 🎬 고급 효과
- 🎯 **다양한 카메라 스타일**: basic, dynamic, cinematic
- 🔄 **고급 전환**: morph, glitch, circular wipe, page curl
- 🎨 **색상 그레이딩**: AI 기반 자동 색보정
- 🎵 **오디오 싱크**: 배경음악의 비트에 맞춰 클립 자동 조절

---

## 🚀 빠른 시작

### 1️⃣ 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 2️⃣ 릴스 만들기

#### **방법 A: 간단한 스크립트 사용** (추천! ⭐)

```bash
# 1. photos 폴더에 사진 넣기
# 2. 스크립트 실행
python create_reels_simple.py
# 3. output 폴더에서 결과 확인!
```

**현재 기본 설정:**
- ✅ AI 텍스트 오버레이 활성화 (감성형 스타일)
- ✅ Ken Burns 효과 (랜덤 스타일)
- ✅ 전환 효과 (랜덤)
- ✅ 고화질 인코딩 (CRF 18)

#### **방법 B: AI 기능 사용**

```bash
# 1. .env 파일에 OpenAI API 키 설정
# OPENAI_API_KEY=your_api_key_here

# 2. photos 폴더에 사진 넣기

# 3. AI 릴스 생성 스크립트 실행
python create_reels_ai.py

# 4. output 폴더에서 AI가 만든 릴스 확인!
```

#### **방법 C: API 서버 사용**

```bash
# 1. 서버 실행
python app.py

# 2. 브라우저에서 http://localhost:8000/docs 접속
# 3. Swagger UI에서 사진 업로드 및 릴스 생성
```

---

## 📁 프로젝트 구조

```
C:\AIX\Reels\
├── app.py                      # FastAPI 서버
├── reels_engine.py            # 릴스 생성 엔진
├── openai_service.py          # OpenAI API 서비스 (Vision, TTS)
├── models.py                  # 데이터 모델
├── utils.py                   # 유틸리티 함수
├── create_reels_simple.py     # 간단한 실행 스크립트 ⭐
├── create_reels_ai.py         # AI 기능 포함 스크립트
├── advanced_transitions.py    # 고급 전환 효과
├── audio_sync.py              # 오디오 비트 싱크
├── color_grading.py           # 색상 그레이딩
├── face_detection.py          # 얼굴 감지 (스마트 크롭)
├── photos/                    # 📸 여기에 사진 넣기
├── output/                    # 📹 결과 비디오 저장
└── requirements.txt           # 필수 패키지
```

---

## ⚙️ 설정 옵션

`create_reels_simple.py`에서 다음 옵션을 수정할 수 있습니다:

```python
config = ReelsConfig(
    # 기본 설정
    duration_per_photo=3,          # 사진당 지속 시간 (초)
    enable_transitions=True,       # 전환 효과 ON/OFF
    enable_ken_burns=True,         # 줌 효과 ON/OFF
    enable_text_overlay=True,      # 텍스트 오버레이 ON/OFF
    sort_by_time=True,             # 시간순 정렬 ON/OFF
    
    # AI 텍스트 오버레이 (NEW!)
    enable_ai_text_overlay=True,   # AI 생성 텍스트 활성화
    ai_text_style="poetic",        # descriptive/poetic/simple
    
    # 효과 설정
    effect_intensity="medium",     # low/medium/high
    transition_style="random",     # fade/slide/zoom/random
    ken_burns_style="random",      # zoom_in/zoom_out/pan/diagonal/random
    
    # 카메라 스타일
    camera_style="dynamic",        # basic/dynamic/cinematic
)
```

---

## 🎨 AI 텍스트 오버레이 스타일

### 1. **Descriptive (설명형)**
사진의 주요 내용을 간결하게 설명
- 예: "해변의 석양", "도심 야경", "맛있는 음식"

### 2. **Poetic (감성형)** ⭐ 추천
사진의 분위기를 감성적으로 표현
- 예: "황금빛 추억", "별이 빛나는 밤", "행복한 순간"

### 3. **Simple (간결형)**
짧고 간단한 단어로 표현
- 예: "여유로운 오후", "특별한 하루", "평화로운 시간"

---

## 💰 AI 기능 비용

### OpenAI Vision API (이미지 분석)
- **모델**: GPT-4o
- **비용**: 약 $0.00085/이미지 (detail="low")
- **예시**:
  - 10장: 약 $0.0085 (약 11원)
  - 30장: 약 $0.0255 (약 33원)

매우 저렴하게 사용 가능합니다! 🎉

---

## 📝 사용 예시

### 예시 1: 기본 사용 (AI 텍스트 포함)

```bash
# photos 폴더에 사진 넣기
copy "C:\Users\Admin\Pictures\여행사진\*.jpg" photos\

# 릴스 생성 (AI가 각 사진 분석하여 텍스트 추가)
python create_reels_simple.py

# 결과 확인
start output\my_travel_reels.mp4
```

### 예시 2: 텍스트 스타일 변경

```python
# create_reels_simple.py 수정
config = ReelsConfig(
    enable_ai_text_overlay=True,
    ai_text_style="descriptive",  # 설명형으로 변경
    # ... 기타 설정
)
```

### 예시 3: AI 비활성화 (날짜만 표시)

```python
config = ReelsConfig(
    enable_text_overlay=True,      # 텍스트 오버레이 활성화
    enable_ai_text_overlay=False,  # AI 비활성화 → 날짜 표시
    # ... 기타 설정
)
```

---

## 🎬 화질 설정

현재 고화질 설정이 적용되어 있습니다:

- **비트레이트**: 8000k (기본값보다 훨씬 높음)
- **CRF**: 18 (거의 무손실 수준, 0-51 범위)
- **Preset**: slow (더 나은 압축 품질)
- **Profile**: high (H.264 High Profile)

인코딩 시간이 조금 더 걸리지만 화질이 훨씬 좋습니다!

---

## 🔧 문제 해결

### Q: "AI 텍스트가 생성되지 않아요"
```bash
# 1. .env 파일에 OpenAI API 키 확인
cat .env

# 2. API 키 유효성 확인
https://platform.openai.com/api-keys

# 3. 크레딧 확인
https://platform.openai.com/usage
```

### Q: "사진이 시간순으로 정렬되지 않아요"
- EXIF 데이터가 없는 사진은 파일명순으로 정렬됩니다
- 스마트폰으로 찍은 사진은 대부분 EXIF 데이터가 있습니다

### Q: "비디오 생성이 너무 느려요"
- AI 텍스트 오버레이: 사진당 약 2-3초 추가 (API 호출)
- 고화질 인코딩: preset='slow'로 인해 시간이 더 걸림
- 빠른 생성이 필요하면 `enable_ai_text_overlay=False` 설정

---

## 📦 API 엔드포인트

### `POST /api/reels/create`

**파라미터:**
- `photos` (required): 업로드할 사진 파일들
- `duration_per_photo` (optional): 사진당 지속 시간 (기본 3초)
- `enable_transitions` (optional): 전환 효과 (기본 true)
- `enable_ken_burns` (optional): 줌 효과 (기본 true)
- `enable_text_overlay` (optional): 텍스트 오버레이 (기본 true)
- `enable_ai_text_overlay` (optional): AI 텍스트 오버레이 (기본 false)
- `ai_text_style` (optional): AI 텍스트 스타일 (기본 "poetic")

**응답:**
- 생성된 MP4 비디오 파일

---

## 🎯 다음 단계

이 프로젝트를 확장하려면:

1. ✅ **AI 텍스트 오버레이** - 완료!
2. ✅ **고화질 인코딩** - 완료!
3. **배경 음악 추가**: `background_music_path` 설정
4. **오디오 비트 싱크**: `enable_beat_sync=True`
5. **색상 그레이딩**: `enable_color_grading=True`
6. **얼굴 감지 스마트 크롭**: `enable_smart_crop=True`

---

## 📄 라이선스

MIT License

---

## 🙋‍♂️ 문의

문제가 있거나 기능 제안이 있으시면 이슈를 등록해주세요!

**즐거운 여행 추억 만들기! 🌍✈️📸**
