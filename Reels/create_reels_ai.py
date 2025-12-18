"""
AI 기능을 사용한 릴스 생성 스크립트

사용법:
1. .env 파일에 OPENAI_API_KEY 설정
2. photos 폴더에 사진 넣기
3. python create_reels_ai.py 실행
4. output 폴더에서 결과 확인
"""
from pathlib import Path
from models import ReelsConfig
from reels_engine import generate_reels
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


def main():
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_openai_api_key_here":
        print("=" * 60)
        print("[오류] OPENAI_API_KEY가 설정되지 않았습니다!")
        print("=" * 60)
        print("1. .env 파일을 생성하세요")
        print("2. OPENAI_API_KEY=your_actual_api_key 를 추가하세요")
        print("=" * 60)
        return
    
    # 입력/출력 경로 설정
    input_dir = Path("photos")  # 사진이 있는 폴더
    output_dir = Path("output")
    output_file = output_dir / "ai_travel_reels.mp4"
    
    # 폴더 생성
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # 사진 확인
    photos = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.png")) + list(input_dir.glob("*.PNG"))
    if not photos:
        print("=" * 60)
        print(f"[오류] {input_dir} 폴더에 사진이 없습니다!")
        print("=" * 60)
        return
    
    print("=" * 60)
    print("[AI 릴스 생성] 여행 릴스 자동 생성 시작!")
    print("=" * 60)
    print(f"[입력] 폴더: {input_dir.absolute()}")
    print(f"[사진] 개수: {len(photos)}장")
    print(f"[출력] 파일: {output_file.absolute()}")
    print("=" * 60)
    print("[AI] 기능:")
    print("  ✓ GPT-4 Vision으로 이미지 분석")
    print("  ✓ AI가 자동으로 스토리 생성")
    print("  ✓ AI 캡션 생성")
    print("  ✓ 텍스트 자막으로 스토리 표시 (음성 나레이션 대신)")
    print("=" * 60)
    
    # 릴스 생성 설정 (AI 기능 활성화)
    config = ReelsConfig(
        duration_per_photo=3,        # 사진당 3초
        enable_transitions=True,     # 전환 효과 활성화
        enable_ken_burns=True,       # Ken Burns 줌 효과 활성화
        enable_text_overlay=True,    # 텍스트 오버레이 활성화
        sort_by_time=True,           # 촬영 시간순 정렬
        # AI 기능 활성화
        enable_ai_analysis=True,     # AI 이미지 분석
        enable_ai_captions=True,     # AI 캡션 생성
        enable_ai_subtitles=True,    # AI 스토리 텍스트 자막 (추천!)
        enable_narration=False,      # 음성 나레이션 (비활성화)
        narration_voice="nova",      # 음성: nova (여성), onyx (남성)
    )
    
    # 릴스 생성
    success = generate_reels(
        input_dir=input_dir,
        output_path=output_file,
        config=config,
        progress_callback=None
    )
    
    if success:
        print("\n" + "=" * 60)
        print("[성공] AI 릴스 생성 완료!")
        print(f"[파일] 위치: {output_file.absolute()}")
        print("=" * 60)
        print("\n[팁] 다른 옵션을 사용하려면:")
        print("\n  ** 텍스트 자막 (추천, 비용 절감) **")
        print("  - enable_ai_subtitles=True")
        print("  - enable_narration=False")
        print("  → 화면에 텍스트로 스토리 표시")
        print("\n  ** 음성 나레이션 (더 몰입감 있음) **")
        print("  - enable_ai_subtitles=False")
        print("  - enable_narration=True")
        print("  → 음성으로 스토리 들려줌")
        print("\n  ** 음성 옵션 **")
        print("  - nova (여성, 밝은)")
        print("  - alloy (중성, 차분한)")
        print("  - echo (남성, 깊은)")
        print("  - fable (중성, 따뜻한)")
        print("  - onyx (남성, 강한)")
        print("  - shimmer (여성, 부드러운)")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[실패] 릴스 생성 실패")
        print("=" * 60)


if __name__ == "__main__":
    main()
