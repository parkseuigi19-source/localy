# -*- coding: utf-8 -*-
"""
향상된 릴스 생성 스크립트 (A안 - 모든 기능 활성화)

사용법:
1. photos 폴더에 사진 넣기
2. python create_reels_enhanced.py 실행
3. output 폴더에서 결과 확인
"""
from pathlib import Path
from models import ReelsConfig
from reels_engine import generate_reels
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# ReelsEngine에 향상된 기능 패치 적용
from reels_engine_extensions import patch_reels_engine
patch_reels_engine()


def main():
    # 입력/출력 경로 설정
    input_dir = Path("photos")
    output_dir = Path("output")
    output_file = output_dir / "enhanced_travel_reels.mp4"
    
    # 폴더 생성
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # 사진 확인
    photos = list(input_dir.glob("*.jpg")) + list(input_dir.glob("*.jpeg")) + list(input_dir.glob("*.png")) + list(input_dir.glob("*.PNG")) + list(input_dir.glob("*.JPG"))
    if not photos:
        print("=" * 60)
        print(f"[오류] {input_dir} 폴더에 사진이 없습니다!")
        print("=" * 60)
        return
    
    print("=" * 60)
    print("[향상된 릴스 생성] A안 모든 기능 활성화!")
    print("=" * 60)
    print(f"[입력] 폴더: {input_dir.absolute()}")
    print(f"[사진] 개수: {len(photos)}장")
    print(f"[출력] 파일: {output_file.absolute()}")
    print("=" * 60)
    print("[활성화된 기능]")
    print("  - 부드러운 이징 함수 (ease_in_out_cubic)")
    print("  - 얼굴 감지 기반 스마트 크롭")
    print("  - 중요도 기반 적응형 지속 시간 (2-6초)")
    print("  - AI 기반 색상 그레이딩")
    print("  - 고급 전환 효과 (random)")
    print("  - 향상된 Ken Burns 효과")
    print("=" * 60)
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        print("[AI] OpenAI API 키 감지 - AI 분석 활성화")
        enable_ai = True
    else:
        print("[AI] OpenAI API 키 없음 - AI 분석 비활성화")
        enable_ai = False
    print("=" * 60)
    
    # 릴스 생성 설정
    config = ReelsConfig(
        duration_per_photo=4,
        enable_transitions=True,
        enable_ken_burns=True,
        enable_text_overlay=False,  # 폰트 문제로 임시 비활성화
        sort_by_time=True,
        
        effect_intensity="high",
        enable_rotation=False,
        transition_style="random",
        ken_burns_style="random",
        
        easing_function="ease_in_out_cubic",
        
        enable_smart_crop=True,
        enable_adaptive_duration=True,
        
        # 2.5D Parallax 효과 (CPU에서도 작동하지만 느릴 수 있음)
        # GPU가 없으면 False로 설정하는 것이 안전하지만, 
        # "진짜 영상처럼" 원한다면 True로 시도해볼 수 있음 (단, 깊이 추정 모델 필요)
        # 현재는 안전하게 False로 유지하되, Ken Burns 강도를 높임
        enable_parallax=False,
        parallax_intensity=0.8,
        
        enable_color_grading=enable_ai,
        
        enable_ai_analysis=enable_ai,
        enable_ai_captions=False,
        enable_ai_subtitles=False,
        enable_narration=False,
        
        enable_sora=False,
        enable_svd=False,
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
        print("[성공] 향상된 릴스 생성 완료!")
        print(f"[파일] 위치: {output_file.absolute()}")
        print("=" * 60)
        print("\n[적용된 기능]")
        print("  - 부드러운 이징 함수로 자연스러운 움직임")
        print("  - 얼굴 감지로 중요한 부분에 포커스")
        print("  - 중요한 사진은 더 길게, 덜 중요한 사진은 짧게")
        if enable_ai:
            print("  - AI가 분석한 분위기에 맞는 색상 필터")
        print("  - 다양한 전환 효과로 역동적인 영상")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[실패] 릴스 생성 실패")
        print("=" * 60)


if __name__ == "__main__":
    main()
