"""
간단한 릴스 생성 스크립트

사용법:
1. photos 폴더에 사진 넣기
2. python create_reels_simple.py 실행
3. output 폴더에서 결과 확인
"""
from pathlib import Path
from models import ReelsConfig
from reels_engine import generate_reels


def main():
    # 입력/출력 경로 설정
    input_dir = Path("photos")  # 사진이 있는 폴더
    output_dir = Path("output")
    output_file = output_dir / "my_travel_reels.mp4"
    
    # 폴더 생성
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # 사진 확인
    photos = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.png")) + list(input_dir.glob("*.PNG"))
    if not photos:
        print("=" * 60)
        print(f"[오류] {input_dir} 폴더에 사진이 없습니다!")
        print("=" * 60)
        print("사진을 추가한 후 다시 실행해주세요.")
        return
    
    print("=" * 60)
    print("[릴스 생성] 여행 릴스 자동 생성 시작!")
    print("=" * 60)
    print(f"[입력] 폴더: {input_dir.absolute()}")
    print(f"[사진] 개수: {len(photos)}장")
    print(f"[출력] 파일: {output_file.absolute()}")
    print("=" * 60)
    
    # 릴스 생성 설정
    config = ReelsConfig(
        duration_per_photo=3,        # 사진당 3초
        enable_transitions=True,     # 전환 효과 활성화
        enable_ken_burns=True,       # Ken Burns 줌 효과 활성화
        enable_text_overlay=True,    # 텍스트 오버레이 활성화
        sort_by_time=True,           # 촬영 시간순 정렬
        # 동적 효과 설정
        effect_intensity="medium",   # 효과 강도: low, medium, high
        enable_rotation=False,       # 회전 효과 (선택)
        transition_style="random",   # 전환 스타일: fade, slide, zoom, random
        ken_burns_style="random",    # Ken Burns 스타일: zoom_in, zoom_out, pan, diagonal, random
        # AI 기능 설정
        enable_ai_text_overlay=True, # AI 생성 텍스트 오버레이 활성화
        ai_text_style="poetic",      # AI 텍스트 스타일: descriptive, poetic, simple
        enable_ai_analysis=False,
        enable_ai_captions=False,
        enable_ai_subtitles=False,
        enable_narration=False,
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
        print("[성공] 릴스 생성 완료!")
        print(f"[파일] 위치: {output_file.absolute()}")
        print("=" * 60)
        print("\n[팁] 설정을 변경하려면 이 파일을 편집하세요:")
        print("  - duration_per_photo: 사진당 지속 시간 (초)")
        print("  - effect_intensity: 효과 강도 (low/medium/high)")
        print("  - enable_rotation: 회전 효과 (True/False)")
        print("  - transition_style: 전환 스타일 (fade/slide/zoom/random)")
        print("  - ken_burns_style: 줌 스타일 (zoom_in/zoom_out/pan/diagonal/random)")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[실패] 릴스 생성 실패")
        print("=" * 60)


if __name__ == "__main__":
    main()
