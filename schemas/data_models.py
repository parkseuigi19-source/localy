"""통일된 데이터 스키마"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlaceData(BaseModel):
    """모든 장소 데이터의 표준 형식"""
    place_id: str = Field(..., description="Google Place ID")
    name: str
    category: str  # restaurant | cafe | hotel | landmark | shopping
    address: str
    latitude: float
    longitude: float
    region: str
    rating: float = 0
    review_count: int = 0
    price_level: int = 0
    opening_hours: List[str] = []
    open_now: Optional[bool] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    images: List[str] = []
    google_maps_url: str
    description: Optional[str] = None
    tags: List[str] = []
    
    # 상세 정보 필드 (get_landmark_detail_tool 사용 시 채워짐)
    amenities: List[str] = []  # 편의시설 (주차, 휠체어 등)
    accessibility: List[str] = [] # 접근성 정보 (휠체어, 엘리베이터 등)
    ticket_info: Optional[str] = None # 입장권/가격 정보
    editorial_summary: Optional[str] = None  # 구글 제공 요약
    recent_reviews: List[str] = []  # 최근 리뷰 텍스트 (요약용)
    crowdedness_info: Optional[str] = None  # 혼잡도 정보 (추정)
    best_time_to_visit: Optional[str] = None  # 추천 방문 시간
    nearby_attractions: List[str] = []  # 주변 관광지 목록
    guide_tours: List[Dict[str, str]] = []  # 가이드 투어 정보 (이름, 설명, 가격, 예약 링크 등)

class AgentResponse(BaseModel):
    """모든 에이전트의 표준 응답"""
    success: bool
    agent_name: str
    data: List[Dict[str, Any]] = []
    count: int = 0
    message: str
    error: Optional[str] = None

class UserPersona(BaseModel):
    """
    사용자 페르소나 - 회원가입 시 수집, 여행 계획 시 참고용
    
    ⚠️ 중요: 페르소나는 기본 선호도일 뿐!
    - LLM은 페르소나를 참고하되, 매번 사용자에게 확인 필요
    - 예: "평소 한식 좋아하시는데, 이번엔 어떤 음식 드시고 싶으세요?"
    - 사용자가 다른 선택을 할 수 있음 (페르소나 ≠ 강제)
    """
    user_id: str
    age_group: str  # "20대", "30대", "40대", "50대+"
    gender: Optional[str] = None
    travel_style: List[str] = []  # ["힐링", "액티비티", "맛집투어", "문화체험"]
    budget_level: str = "중"  # "저" | "중" | "고"
    food_preferences: List[str] = []  # ["한식", "일식", "양식", "해산물"]
    accommodation_style: str = "호텔"  # "호텔" | "펜션" | "게스트하우스" | "한옥"
    interests: List[str] = []  # ["사진", "쇼핑", "자연", "역사", "카페"]
    created_at: str
    updated_at: str

class TravelState(BaseModel):
    """
    전역 상태 관리 - 여행 계획 전체 정보 저장
    
    Phase 1: 기본 정보만 사용
    Phase 2: 에이전트 간 공유
    """
    # 기본 정보
    user_id: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    num_travelers: int = 1
    total_budget: Optional[int] = None
    
    # 선택된 지역들
    selected_regions: List[str] = []
    current_region: Optional[str] = None
    
    # 검색 결과 캐시
    search_results: Dict[str, List[PlaceData]] = {}
    
    # 선택된 장소들
    selected_places: Dict[str, List[PlaceData]] = {}  # {category: [places]}
    
    # 경로 정보
    routes: List["RouteData"] = []
    
    # 날씨 정보
    weather_forecast: List["WeatherData"] = []
    
    # 예산 정보
    budget: Optional["BudgetData"] = None
    
    # 대화 기록
    chat_history: List[Dict[str, str]] = []
    
    # 페르소나 (선택사항)
    persona: Optional[UserPersona] = None
    
    # 메타데이터
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed: bool = False

class RouteData(BaseModel):
    """GPS 경로 데이터"""
    origin: str
    destination: str
    mode: str  # "transit" | "driving" | "walking"
    duration: str  # "2시간 30분"
    distance: str  # "237km"
    cost: Optional[str] = None  # "약 25,000원"
    steps: List[Dict[str, Any]] = []
    google_maps_url: str

class WeatherData(BaseModel):
    """날씨 데이터"""
    date: str  # "2025-12-05"
    day_of_week: str  # "금요일"
    temperature_high: int
    temperature_low: int
    condition: str  # "맑음" | "흐림" | "비" | "눈"
    precipitation: int = 0  # 강수 확률 (%)
    icon: str  # "☀️" | "☁️" | "🌧️" | "❄️"
    clothing_recommendation: str

class BudgetData(BaseModel):
    """예산 데이터"""
    total_budget: int
    spent: Dict[str, int] = {}  # {"식비": 50000, "숙박": 150000}
    remaining: int
    warning: bool = False  # 예산 초과 경고