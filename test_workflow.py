"""LangGraph 워크플로우 테스트 시나리오
Phase 4: 통합 및 테스트
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from agents.langgraph_workflow import LandmarkWorkflow

def run_test_scenarios():
    """테스트 시나리오 실행"""
    print("=" * 80)
    print("🎉 LangGraph 워크플로우 테스트 시작!")
    print("=" * 80)
    print()
    
    # 워크플로우 초기화
    workflow = LandmarkWorkflow(user_id="test_user")
    
    # 테스트 시나리오 정의
    test_scenarios = [
        {
            "name": "시나리오 1: 기본 검색",
            "queries": [
                "제주도 테마파크 찾아줘",
            ],
            "expected": "검색 결과 반환"
        },
        {
            "name": "시나리오 2: 상세 정보 조회",
            "queries": [
                "서울 박물관 찾아줘",
                "첫 번째 자세히 알려줘",
            ],
            "expected": "상세 정보 반환"
        },
        {
            "name": "시나리오 3: 주변 검색",
            "queries": [
                "강릉 자연 관광지 찾아줘",
                "첫 번째 주변 관광지",
            ],
            "expected": "주변 관광지 반환"
        },
        {
            "name": "시나리오 4: 계절 기반 추천",
            "queries": [
                "서울 봄 여행지 추천해줘",
            ],
            "expected": "계절 추천 결과 반환"
        },
        {
            "name": "시나리오 5: 시간대 기반 추천",
            "queries": [
                "서울 야경 명소",
            ],
            "expected": "시간대 추천 결과 반환"
        },
    ]
    
    # 각 시나리오 실행
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"📋 {scenario['name']}")
        print(f"기대 결과: {scenario['expected']}")
        print(f"{'='*80}\n")
        
        for query in scenario['queries']:
            print(f"🗣️  사용자: {query}")
            print("-" * 80)
            
            try:
                response = workflow.run(query)
                print(f"🤖 응답:\n{response}")
                print()
            except Exception as e:
                print(f"❌ 오류 발생: {e}")
                print()
        
        # 시나리오 간 구분선
        if i < len(test_scenarios):
            input("\n⏸️  다음 시나리오로 진행하려면 Enter를 누르세요...\n")
    
    print("\n" + "=" * 80)
    print("✅ 모든 테스트 시나리오 완료!")
    print("=" * 80)

if __name__ == "__main__":
    run_test_scenarios()
