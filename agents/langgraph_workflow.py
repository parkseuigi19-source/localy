"""LangGraph 워크플로우 - 관광지 에이전트
기존 landmark_agent의 함수들을 LangGraph로 통합하여 상태 기반 워크플로우 구현
"""
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from schemas.data_models import TravelState, AgentResponse, PlaceData

# 기존 landmark_agent 함수들 임포트
from agents.landmark_agent import (
    search_landmarks,
    get_landmark_detail,
    find_nearby_landmarks,
    recommend_by_season,
    recommend_by_time,
    TOURIST_CATEGORIES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 1. State 스키마 정의
# ============================================================================

class AgentState(TypedDict):
    """LangGraph 워크플로우 상태"""
    user_input: str                    # 사용자 입력
    intent: str                        # 파악된 의도
    travel_state: TravelState          # 여행 상태 (기존 활용)
    response: str                      # 최종 응답
    intermediate_steps: list           # 중간 단계 기록
    error: str                         # 에러 메시지

# ============================================================================
# 2. 노드 함수들
# ============================================================================

def router_node(state: AgentState) -> AgentState:
    """사용자 입력을 분석하여 의도를 파악합니다 (규칙 기반)"""
    user_input = state["user_input"].lower()
    logger.info(f"🔍 라우터: 사용자 입력 분석 - '{user_input}'")
    
    intent = "unknown"
    
    # 1. 계절 기반 추천 (우선순위 높음)
    if any(season in user_input for season in ["봄", "여름", "가을", "겨울", "spring", "summer", "fall", "autumn", "winter"]):
        intent = "season_recommend"
    
    # 2. 시간대 기반 추천 (우선순위 높음)
    elif any(time in user_input for time in ["아침", "오후", "저녁", "밤", "야경", "일출", "석양", "야시장"]):
        intent = "time_recommend"
    
    # 3. 검색 의도
    elif any(keyword in user_input for keyword in ["찾아줘", "검색", "추천", "알려줘", "보여줘", "명소", "관광지", "여행지"]):
        intent = "search"
    
    # 4. 상세 정보 조회
    elif any(keyword in user_input for keyword in ["상세", "자세히", "정보", "어때"]):
        intent = "detail"
    
    # 5. 경로 계산 (비활성화 - 별도 경로 에이전트 사용)
    # elif any(keyword in user_input for keyword in ["경로", "가는 법", "이동", "어떻게 가"]):
    #     intent = "route"
    
    # 6. 주변 검색
    elif any(keyword in user_input for keyword in ["주변", "근처", "가까운"]):
        intent = "nearby"
    
    # 7. 순서 참조 (첫 번째, 두 번째 등)
    elif any(keyword in user_input for keyword in ["첫", "두", "세", "번째"]):
        if "주변" in user_input or "근처" in user_input:
            intent = "nearby"
        # elif "경로" in user_input or "가는" in user_input:
        #     intent = "route"
        else:
            intent = "detail"
    
    state["intent"] = intent
    state["intermediate_steps"].append(f"의도 파악: {intent}")
    logger.info(f"✅ 파악된 의도: {intent}")
    
    return state


def search_node(state: AgentState) -> AgentState:
    """관광지 검색을 수행합니다"""
    user_input = state["user_input"]
    logger.info(f"🔍 검색 노드 실행: {user_input}")
    
    # 지역 추출
    region = "서울"  # 기본값
    regions = ["제주", "부산", "서울", "용인", "경주", "강릉", "인천", "대구", "광주", "대전"]
    for r in regions:
        if r in user_input:
            region = r
            break
    
    # 카테고리 추출
    category = None
    for cat, keywords in TOURIST_CATEGORIES.items():
        if any(k in user_input for k in keywords):
            category = cat
            break
    
    # 추가 선호도 추출
    preference = None
    if "벚꽃" in user_input: preference = "벚꽃"
    elif "해변" in user_input or "바다" in user_input: preference = "해변"
    elif "산" in user_input: preference = "산"
    
    # 검색 실행
    result = search_landmarks(region, preference=preference, category=category)
    
    if result.success:
        # 상태에 검색 결과 저장
        state["travel_state"].current_region = region
        state["travel_state"].search_results[region] = [
            PlaceData(**place_dict) for place_dict in result.data
        ]
        
        # 응답 생성
        places_text = "\n".join([
            f"{i+1}. {place['name']} ({place['category']}) - ⭐ {place['rating']} ({place['review_count']}개 리뷰)"
            for i, place in enumerate(result.data[:5])
        ])
        
        state["response"] = f"✅ {result.message}\n\n{places_text}\n\n💡 상세 정보를 원하시면 '첫 번째 자세히'처럼 말씀해주세요!"
        state["intermediate_steps"].append(f"검색 완료: {len(result.data)}개 결과")
    else:
        state["response"] = f"❌ {result.message}"
        state["error"] = result.error or "검색 실패"
        state["intermediate_steps"].append(f"검색 실패: {result.error}")
    
    return state


def detail_node(state: AgentState) -> AgentState:
    """상세 정보를 조회합니다"""
    user_input = state["user_input"]
    logger.info(f"📋 상세 노드 실행: {user_input}")
    
    # 순서 추출 (첫 번째, 두 번째 등)
    index = 0
    if "첫" in user_input or "1" in user_input:
        index = 0
    elif "두" in user_input or "2" in user_input:
        index = 1
    elif "세" in user_input or "3" in user_input:
        index = 2
    elif "네" in user_input or "4" in user_input:
        index = 3
    elif "다섯" in user_input or "5" in user_input:
        index = 4
    
    # 이전 검색 결과에서 place_id 가져오기
    current_region = state["travel_state"].current_region
    if not current_region or current_region not in state["travel_state"].search_results:
        state["response"] = "❌ 먼저 관광지를 검색해주세요!"
        state["error"] = "검색 결과 없음"
        return state
    
    search_results = state["travel_state"].search_results[current_region]
    if index >= len(search_results):
        state["response"] = f"❌ {index+1}번째 결과가 없습니다. (총 {len(search_results)}개)"
        state["error"] = "인덱스 범위 초과"
        return state
    
    place_id = search_results[index].place_id
    
    # 상세 정보 조회
    result = get_landmark_detail(place_id)
    
    if result.success:
        place = result.data[0]
        
        # 상세 응답 생성
        response_parts = [
            f"📍 **{place['name']}**",
            f"🏷️ 카테고리: {place['category']}",
            f"⭐ 평점: {place['rating']} ({place['review_count']}개 리뷰)",
            f"📍 주소: {place['address']}",
        ]
        
        if place.get('phone'):
            response_parts.append(f"📞 전화: {place['phone']}")
        
        if place.get('opening_hours'):
            response_parts.append(f"\n⏰ **운영시간**:")
            for hour in place['opening_hours']:
                response_parts.append(f"  {hour}")
        
        if place.get('ticket_info'):
            response_parts.append(f"\n🎫 입장료: {place['ticket_info']}")
        
        if place.get('amenities'):
            response_parts.append(f"\n🏢 편의시설: {', '.join(place['amenities'])}")
        
        if place.get('accessibility'):
            response_parts.append(f"\n♿ 접근성: {', '.join(place['accessibility'])}")
        
        if place.get('crowdedness_info'):
            response_parts.append(f"\n👥 혼잡도: {place['crowdedness_info']}")
        
        if place.get('guide_tours'):
            response_parts.append(f"\n🎯 **가이드 투어**:")
            for tour in place['guide_tours'][:2]:  # 최대 2개만
                response_parts.append(f"  • {tour['name']}: {tour['description']}")
        
        if place.get('recent_reviews'):
            response_parts.append(f"\n💬 **최근 리뷰**:")
            for review in place['recent_reviews'][:2]:  # 최대 2개만
                response_parts.append(f"  \"{review[:100]}...\"")
        
        response_parts.append(f"\n🗺️ [Google Maps에서 보기]({place['google_maps_url']})")
        
        state["response"] = "\n".join(response_parts)
        state["intermediate_steps"].append(f"상세 조회 완료: {place['name']}")
    else:
        state["response"] = f"❌ {result.message}"
        state["error"] = result.error or "상세 조회 실패"
    
    return state


# GPS 경로 기능은 별도 경로 에이전트에서 처리
# def route_node(state: AgentState) -> AgentState:
#     """두 장소 간 경로를 계산합니다 (비활성화 - 별도 경로 에이전트 사용)"""
#     state["response"] = "❌ 경로 기능은 별도 경로 에이전트를 사용해주세요."
#     state["error"] = "경로 기능 비활성화"
#     return state


def nearby_node(state: AgentState) -> AgentState:
    """주변 관광지를 검색합니다"""
    user_input = state["user_input"]
    logger.info(f"📍 주변 노드 실행: {user_input}")
    
    # 기준 장소 인덱스 추출
    index = 0
    if "첫" in user_input or "1" in user_input:
        index = 0
    elif "두" in user_input or "2" in user_input:
        index = 1
    elif "세" in user_input or "3" in user_input:
        index = 2
    
    # 검색 결과에서 place_id 가져오기
    current_region = state["travel_state"].current_region
    if not current_region or current_region not in state["travel_state"].search_results:
        state["response"] = "❌ 먼저 관광지를 검색해주세요!"
        return state
    
    search_results = state["travel_state"].search_results[current_region]
    if index >= len(search_results):
        state["response"] = f"❌ {index+1}번째 결과가 없습니다."
        return state
    
    place_id = search_results[index].place_id
    
    # 주변 검색
    result = find_nearby_landmarks(place_id, radius=2000, limit=5)
    
    if result.success:
        places_text = "\n".join([
            f"{i+1}. {place['name']} - ⭐ {place['rating']} ({place['description']})"
            for i, place in enumerate(result.data)
        ])
        
        state["response"] = f"✅ {result.message}\n\n{places_text}"
        state["intermediate_steps"].append(f"주변 검색 완료: {len(result.data)}개")
    else:
        state["response"] = f"❌ {result.message}"
        state["error"] = result.error or "주변 검색 실패"
    
    return state


def season_recommend_node(state: AgentState) -> AgentState:
    """계절에 맞는 관광지를 추천합니다"""
    user_input = state["user_input"]
    logger.info(f"🌸 계절 추천 노드 실행: {user_input}")
    
    # 지역 추출
    region = "서울"
    regions = ["제주", "부산", "서울", "용인", "경주", "강릉"]
    for r in regions:
        if r in user_input:
            region = r
            break
    
    # 계절 추출
    season = "봄"
    if any(s in user_input for s in ["여름", "summer"]):
        season = "여름"
    elif any(s in user_input for s in ["가을", "fall", "autumn"]):
        season = "가을"
    elif any(s in user_input for s in ["겨울", "winter"]):
        season = "겨울"
    
    # 추천 실행
    result = recommend_by_season(region, season)
    
    if result.success:
        state["travel_state"].current_region = region
        state["travel_state"].search_results[region] = [
            PlaceData(**place_dict) for place_dict in result.data
        ]
        
        places_text = "\n".join([
            f"{i+1}. {place['name']} ({place['category']}) - ⭐ {place['rating']}"
            for i, place in enumerate(result.data[:5])
        ])
        
        state["response"] = f"✅ {result.message}\n\n{places_text}"
        state["intermediate_steps"].append(f"계절 추천 완료: {season}")
    else:
        state["response"] = f"❌ {result.message}"
        state["error"] = result.error or "계절 추천 실패"
    
    return state


def time_recommend_node(state: AgentState) -> AgentState:
    """시간대에 맞는 관광지를 추천합니다"""
    user_input = state["user_input"]
    logger.info(f"🕐 시간 추천 노드 실행: {user_input}")
    
    # 지역 추출
    region = "서울"
    regions = ["제주", "부산", "서울", "용인", "경주", "강릉"]
    for r in regions:
        if r in user_input:
            region = r
            break
    
    # 시간대 추출
    time_of_day = "저녁"
    if any(t in user_input for t in ["아침", "morning", "일출"]):
        time_of_day = "아침"
    elif any(t in user_input for t in ["오후", "afternoon", "점심"]):
        time_of_day = "오후"
    elif any(t in user_input for t in ["밤", "night"]):
        time_of_day = "밤"
    
    # 추천 실행
    result = recommend_by_time(region, time_of_day)
    
    if result.success:
        state["travel_state"].current_region = region
        state["travel_state"].search_results[region] = [
            PlaceData(**place_dict) for place_dict in result.data
        ]
        
        places_text = "\n".join([
            f"{i+1}. {place['name']} ({place['category']}) - ⭐ {place['rating']}"
            for i, place in enumerate(result.data[:5])
        ])
        
        state["response"] = f"✅ {result.message}\n\n{places_text}"
        state["intermediate_steps"].append(f"시간 추천 완료: {time_of_day}")
    else:
        state["response"] = f"❌ {result.message}"
        state["error"] = result.error or "시간 추천 실패"
    
    return state


def unknown_node(state: AgentState) -> AgentState:
    """알 수 없는 의도 처리"""
    state["response"] = "죄송합니다. 요청을 이해하지 못했습니다. 다음과 같이 말씀해주세요:\n" \
                       "• '서울 박물관 찾아줘'\n" \
                       "• '첫 번째 자세히'\n" \
                       "• '첫 번째에서 두 번째로 가는 법'\n" \
                       "• '첫 번째 주변 관광지'"
    state["intermediate_steps"].append("알 수 없는 의도")
    return state


# ============================================================================
# 3. 조건부 라우팅
# ============================================================================

def route_by_intent(state: AgentState) -> Literal["search", "detail", "nearby", "season_recommend", "time_recommend", "unknown"]:
    """의도에 따라 다음 노드를 결정합니다"""
    intent = state["intent"]
    logger.info(f"🔀 라우팅: {intent}")
    return intent


# ============================================================================
# 4. 그래프 구성
# ============================================================================

def create_workflow() -> StateGraph:
    """LangGraph 워크플로우를 생성합니다"""
    
    # 그래프 초기화
    workflow = StateGraph(AgentState)
    
    # 노드 추가
    workflow.add_node("router", router_node)
    workflow.add_node("search", search_node)
    workflow.add_node("detail", detail_node)
    # workflow.add_node("route", route_node)  # 비활성화 - 별도 경로 에이전트 사용
    workflow.add_node("nearby", nearby_node)
    workflow.add_node("season_recommend", season_recommend_node)
    workflow.add_node("time_recommend", time_recommend_node)
    workflow.add_node("unknown", unknown_node)
    
    # 시작점 설정
    workflow.set_entry_point("router")
    
    # 조건부 엣지 (라우터 → 각 노드)
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "search": "search",
            "detail": "detail",
            # "route": "route",  # 비활성화
            "nearby": "nearby",
            "season_recommend": "season_recommend",
            "time_recommend": "time_recommend",
            "unknown": "unknown"
        }
    )
    
    # 각 노드에서 END로
    workflow.add_edge("search", END)
    workflow.add_edge("detail", END)
    # workflow.add_edge("route", END)  # 비활성화
    workflow.add_edge("nearby", END)
    workflow.add_edge("season_recommend", END)
    workflow.add_edge("time_recommend", END)
    workflow.add_edge("unknown", END)
    
    return workflow.compile()


# ============================================================================
# 5. 메인 실행 함수
# ============================================================================

class LandmarkWorkflow:
    """LangGraph 워크플로우 래퍼 클래스"""
    
    def __init__(self, user_id: str = "default_user"):
        self.workflow = create_workflow()
        self.travel_state = TravelState(user_id=user_id)
        logger.info(f"🚀 LangGraph 워크플로우 초기화 완료 (User: {user_id})")
    
    def run(self, user_input: str) -> str:
        """사용자 입력을 처리하고 응답을 반환합니다"""
        logger.info(f"\n{'='*60}\n🗣️ 사용자: {user_input}\n{'='*60}")
        
        # 초기 상태 설정
        initial_state: AgentState = {
            "user_input": user_input,
            "intent": "",
            "travel_state": self.travel_state,
            "response": "",
            "intermediate_steps": [],
            "error": ""
        }
        
        # 워크플로우 실행
        final_state = self.workflow.invoke(initial_state)
        
        # 상태 업데이트
        self.travel_state = final_state["travel_state"]
        
        # 로그 출력
        logger.info(f"\n📝 중간 단계: {' → '.join(final_state['intermediate_steps'])}")
        logger.info(f"\n🤖 응답:\n{final_state['response']}\n{'='*60}\n")
        
        return final_state["response"]
    
    def get_state(self) -> TravelState:
        """현재 여행 상태를 반환합니다"""
        return self.travel_state


# ============================================================================
# 6. 테스트 코드
# ============================================================================

if __name__ == "__main__":
    # 워크플로우 초기화
    workflow = LandmarkWorkflow(user_id="test_user")
    
    print("🎉 LangGraph 워크플로우 테스트 시작!\n")
    print("=" * 60)
    
    # 테스트 시나리오
    test_queries = [
        "제주도 테마파크 찾아줘",
        "첫 번째 자세히 알려줘",
        "첫 번째 주변 관광지",
        "서울 봄 여행지 추천해줘",
        "서울 야경 명소"
    ]
    
    for query in test_queries:
        response = workflow.run(query)
        print(f"\n질문: {query}")
        print(f"답변: {response}")
        print("-" * 60)
        input("\n다음 테스트로 진행하려면 Enter를 누르세요...")
