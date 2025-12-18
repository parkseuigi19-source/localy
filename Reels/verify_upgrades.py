import os
from pathlib import Path
from models import ReelsConfig
from reels_engine import generate_reels

def test_reels_generation():
    print("=== 릴스 시스템 업그레이드 검증 시작 ===")
    
    # 설정
    input_dir = Path("c:/AIX/Reels/photos")
    output_path = Path("c:/AIX/Reels/output/test_reel.mp4")
    
    config = ReelsConfig(
        duration_per_photo=3,
        enable_transitions=True,
        transition_style="random",  # 고급 전환 효과 포함
        enable_text_overlay=True,   # 개선된 텍스트 오버레이
        enable_ken_burns=True,
        effect_intensity="medium"
    )
    
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 경로: {output_path}")
    
    # 실행
    try:
        success = generate_reels(
            input_dir=input_dir,
            output_path=output_path,
            config=config,
            progress_callback=lambda p, m: print(f"[{p}%] {m}")
        )
        
        if success and output_path.exists():
            print("=== 검증 성공: 릴스가 정상적으로 생성되었습니다. ===")
            print(f"생성된 파일: {output_path}")
        else:
            print("=== 검증 실패: 파일이 생성되지 않았습니다. ===")
            
    except Exception as e:
        print(f"=== 검증 중 오류 발생: {e} ===")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reels_generation()
