"""
고급 효과가 적용된 릴스 생성 스크립트
프로페셔널 카메라 움직임과 시각 효과 포함
"""
from pathlib import Path
from models import ReelsConfig
from reels_engine import generate_reels

print("=" * 60)
print("[Pro] 고급 효과 릴스 생성기")
print("=" * 60)
print()

# 입력/출력 경로
input_dir = Path("photos")
output_file = Path("output/travel_reels_pro.mp4")

# 사진 개수 확인
image_files = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.png"))
photo_count = len(image_files)

if photo_count == 0:
    print(f"❌ {input_dir} 폴더에 사진이 없습니다!")
    print("   photos 폴더에 사진을 넣어주세요.")
    exit(1)

print(f"[Info] 발견된 사진: {photo_count}장")
print()

# 프로페셔널 설정
config = ReelsConfig(
    # 고급 카메라 효과
    camera_style="dynamic",  # dynamic: 다양한 효과 랜덤
    enable_ken_burns=True,
    enable_3d_rotation=True,
    enable_circular_motion=True,
    enable_zoom_pan_combo=True,
    enable_handheld=False,  # 원하면 True로 변경
    
    # 효과 강도
    effect_intensity="medium",  # low/medium/high
    
    # 전환 효과
    enable_transitions=True,
    transition_style="random",  # 다양한 전환
    
    # 텍스트
    enable_text_overlay=True,
    
    # AI 기능 (선택)
    enable_ai_analysis=False,  # True로 변경하면 AI 분석 활성화
    enable_ai_subtitles=False,
    
    # 기본 설정
    duration_per_photo=4,  # 효과를 잘 보기 위해 4초
    sort_by_time=True,
)

print("[Settings] 설정:")
print(f"   - 카메라 스타일: {config.camera_style}")
print(f"   - 3D 회전: {'ON' if config.enable_3d_rotation else 'OFF'}")
print(f"   - 원형 움직임: {'ON' if config.enable_circular_motion else 'OFF'}")
print(f"   - 줌+팬 조합: {'ON' if config.enable_zoom_pan_combo else 'OFF'}")
print(f"   - 핸드헬드: {'ON' if config.enable_handheld else 'OFF'}")
print(f"   - 효과 강도: {config.effect_intensity}")
print()

print("[Time] 예상 시간: 30초-1분")
print("[Cost] 비용: 완전 무료!")
print()

# 확인
response = input("계속하시겠습니까? (y/n): ")
if response.lower() != 'y':
    print("취소되었습니다.")
    exit(0)

print()
print("=" * 60)
print("릴스 생성 중...")
print("=" * 60)
print()

success = generate_reels(
    input_dir=input_dir,
    output_path=output_file,
    config=config
)

print()
print("=" * 60)
if success:
    print(f"[SUCCESS] 릴스 생성 완료: {output_file}")
    if output_file.exists():
        print(f"[Info] 파일 크기: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
        print()
        print("[Pro Effects] 프로페셔널 효과가 적용된 릴스를 확인하세요!")
        print("   - 다양한 카메라 움직임")
        print("   - 3D 회전, 원형 움직임, 줌+팬 조합")
        print("   - 랜덤 전환 효과")
else:
    print("[ERROR] 릴스 생성 실패")
print("=" * 60)
