"""
한국 관광지 추천 AI 에이전트
Google Places API (New) + Google Geolocation API
"""

import os
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import requests
import json

# LangChain imports
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import concurrent.futures

# 환경 변수 로드
load_dotenv()

# API 키
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
VISITKOREA_API_KEY = os.getenv("VISITKOREA_API_KEY")

# API 엔드포인트
GOOGLE_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACES_NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"
GOOGLE_PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places"
GOOGLE_GEOLOCATION_URL = "https://www.googleapis.com/geolocation/v1/geolocate"
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# 한국관광공사 VisitKorea API 엔드포인트
VISITKOREA_API_BASE_URL = "http://apis.data.go.kr/B551011/KorService1"
VISITKOREA_API_AREA_BASED_URL = f"{VISITKOREA_API_BASE_URL}/areaBasedList1"
VISITKOREA_API_DETAIL_COMMON_URL = f"{VISITKOREA_API_BASE_URL}/detailCommon1"
VISITKOREA_API_DETAIL_INTRO_URL = f"{VISITKOREA_API_BASE_URL}/detailIntro1"
VISITKOREA_API_SEARCH_KEYWORD_URL = f"{VISITKOREA_API_BASE_URL}/searchKeyword1"

# 검색 설정 (Agent가 제어 가능)
SEARCH_PREFERENCES = {
    "sort_by": "popularity",  # popularity (평점+리뷰), rating (평점), distance (거리)
    "radius": 5000,           # 미터 (기본 5km)
    "max_results": 10         # 최대 결과 수
}


def get_wifi_access_points():
    """WiFi AP 정보 수집 (Windows)"""
    try:
        import subprocess
        # Windows에서 WiFi 네트워크 스캔
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
            capture_output=True,
            text=True,
            encoding='cp949'
        )
        
        wifi_aps = []
        lines = result.stdout.split('\n')
        current_ssid = None
        
        for line in lines:
            line = line.strip()
            if 'SSID' in line and ':' in line:
                current_ssid = line.split(':', 1)[1].strip()
            elif 'BSSID' in line and ':' in line:
                bssid = line.split(':', 1)[1].strip()
                if bssid and bssid != '':
                    wifi_aps.append({
                        "macAddress": bssid.replace(':', '-'),
                        "signalStrength": -50  # 기본값
                    })
        
        return wifi_aps[:5]  # 최대 5개만 사용
    except Exception as e:
        print(f"⚠️  WiFi 스캔 실패: {e}")
        return []


def get_location_from_ip():
    """IP 기반 위치 추정 (폴백 방법) - 여러 서비스 시도"""
    print("🌐 IP 주소 기반으로 위치를 추정합니다...")
    
    # 여러 IP 위치 서비스 시도
    services = [
        {
            'name': 'ipapi.co',
            'url': 'https://ipapi.co/json/',
            'lat_key': 'latitude',
            'lng_key': 'longitude',
            'city_key': 'city',
            'region_key': 'region'
        },
        {
            'name': 'ip-api.com',
            'url': 'http://ip-api.com/json/',
            'lat_key': 'lat',
            'lng_key': 'lon',
            'city_key': 'city',
            'region_key': 'regionName'
        },
        {
            'name': 'ipinfo.io',
            'url': 'https://ipinfo.io/json',
            'lat_key': 'loc',  # "37.5665,126.9780" 형식
            'lng_key': 'loc',
            'city_key': 'city',
            'region_key': 'region'
        }
    ]
    
    results = []
    
    for service in services:
        try:
            response = requests.get(service['url'], timeout=5)
            data = response.json()
            
            # 위도/경도 추출
            if service['name'] == 'ipinfo.io':
                loc = data.get(service['lat_key'], '')
                if loc and ',' in loc:
                    lat, lng = map(float, loc.split(','))
                else:
                    continue
            else:
                lat = data.get(service['lat_key'])
                lng = data.get(service['lng_key'])
            
            city = data.get(service['city_key'], '알 수 없음')
            region = data.get(service['region_key'], '알 수 없음')
            
            if lat and lng:
                results.append({
                    'service': service['name'],
                    'lat': float(lat),
                    'lng': float(lng),
                    'city': city,
                    'region': region
                })
                print(f"   ✓ {service['name']}: {region} {city} ({lat:.4f}, {lng:.4f})")
        except Exception as e:
            print(f"   ✗ {service['name']} 실패: {e}")
            continue
    
    if not results:
        print("❌ 모든 IP 위치 서비스 실패")
        return None, None
    
    # 가장 많이 나온 결과 사용 (또는 첫 번째 결과)
    selected = results[0]
    print(f"\n📍 선택된 위치: {selected['region']} {selected['city']}")
    print(f"   좌표: {selected['lat']:.4f}, {selected['lng']:.4f}")
    print(f"⚠️  IP 기반 위치는 대략적입니다 (±5-20km 오차)")
    
    return selected['lat'], selected['lng']


def geocode_address(address: str):
    """주소를 좌표로 변환 (Google Geocoding API)"""
    if not GOOGLE_PLACES_API_KEY:
        print("❌ Google API 키가 없습니다.")
        return None, None
    
    print(f"🔍 '{address}' 위치를 검색합니다...\n")
    
    try:
        params = {
            "address": address,
            "key": GOOGLE_PLACES_API_KEY,
            "language": "ko",
            "region": "kr"  # 한국 우선
        }
        
        response = requests.get(GOOGLE_GEOCODING_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result['status'] != 'OK':
            print(f"❌ 주소를 찾을 수 없습니다: {result.get('status')}")
            return None, None
        
        results = result.get('results', [])
        if not results:
            print("❌ 검색 결과가 없습니다.")
            return None, None
        
        # 여러 결과가 있을 경우 선택
        if len(results) > 1:
            print("📍 여러 위치가 발견되었습니다:\n")
            for i, res in enumerate(results[:5], 1):
                formatted_addr = res.get('formatted_address', 'N/A')
                print(f"   {i}. {formatted_addr}")
            
            while True:
                try:
                    choice = input("\n선택 (1-{}): ".format(min(5, len(results)))).strip()
                    idx = int(choice) - 1
                    if 0 <= idx < min(5, len(results)):
                        selected = results[idx]
                        break
                    else:
                        print("❌ 올바른 번호를 입력하세요.")
                except ValueError:
                    print("❌ 숫자를 입력하세요.")
        else:
            selected = results[0]
        
        location = selected.get('geometry', {}).get('location', {})
        lat = location.get('lat')
        lng = location.get('lng')
        formatted_addr = selected.get('formatted_address', 'N/A')
        
        if lat and lng:
            print(f"\n✅ 위치 확인: {formatted_addr}")
            print(f"📍 좌표: {lat:.6f}, {lng:.6f}\n")
            return lat, lng
        else:
            print("❌ 좌표를 가져올 수 없습니다.")
            return None, None
            
    except Exception as e:
        print(f"❌ Geocoding API 오류: {e}")
        return None, None


def get_current_location():
    """사용자의 현재 위치 가져오기 (Google Geolocation API)"""
    if not GOOGLE_PLACES_API_KEY:
        print("❌ Google API 키가 없습니다.")
        return None, None
    
    print("🗺️  위치를 감지합니다...\n")
    
    # 1. WiFi 기반 위치 감지 시도
    wifi_aps = get_wifi_access_points()
    
    if wifi_aps:
        print(f"📡 {len(wifi_aps)}개의 WiFi AP를 감지했습니다.")
        try:
            url = f"{GOOGLE_GEOLOCATION_URL}?key={GOOGLE_PLACES_API_KEY}"
            data = {
                "considerIp": True,
                "wifiAccessPoints": wifi_aps
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                lat = result.get('location', {}).get('lat')
                lng = result.get('location', {}).get('lng')
                accuracy = result.get('accuracy', 0)
                
                if lat and lng:
                    print(f"✅ WiFi 기반 위치 획득 성공!")
                    print(f"📍 정확도: ±{accuracy:.0f}m\n")
                    return lat, lng
            else:
                print(f"⚠️  Geolocation API 오류: {response.status_code}")
        except Exception as e:
            print(f"⚠️  WiFi 기반 위치 감지 실패: {e}")
    
    # 2. WiFi 없이 Google Geolocation API (IP만 사용)
    print("\n🔄 Google Geolocation API (IP 기반)로 시도합니다...")
    try:
        url = f"{GOOGLE_GEOLOCATION_URL}?key={GOOGLE_PLACES_API_KEY}"
        data = {
            "considerIp": True
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            lat = result.get('location', {}).get('lat')
            lng = result.get('location', {}).get('lng')
            accuracy = result.get('accuracy', 0)
            
            if lat and lng:
                print(f"✅ Google IP 기반 위치 획득 성공!")
                print(f"📍 정확도: ±{accuracy:.0f}m\n")
                return lat, lng
        else:
            print(f"⚠️  Google Geolocation API 오류: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Google IP 기반 위치 감지 실패: {e}")
    
    # 3. 다른 IP 서비스들로 폴백
    print("\n🔄 다른 IP 위치 서비스로 전환합니다...\n")
    return get_location_from_ip()


def set_search_preferences(sort_by: str = None, radius: int = None, max_results: int = None) -> str:
    """검색 설정 변경 (Agent 제어용)"""
    global SEARCH_PREFERENCES
    
    changes = []
    if sort_by:
        if sort_by in ['popularity', 'rating', 'distance']:
            SEARCH_PREFERENCES['sort_by'] = sort_by
            changes.append(f"정렬 기준: {sort_by}")
        else:
            return "❌ 잘못된 정렬 기준입니다. (popularity, rating, distance 중 선택)"
            
    if radius:
        if 100 <= radius <= 50000:
            SEARCH_PREFERENCES['radius'] = radius
            changes.append(f"검색 반경: {radius}m")
        else:
            return "❌ 반경은 100m ~ 50000m 사이여야 합니다."
            
    if max_results:
        if 1 <= max_results <= 20:
            SEARCH_PREFERENCES['max_results'] = max_results
            changes.append(f"최대 결과 수: {max_results}개")
        else:
            return "❌ 결과 수는 1 ~ 20개 사이여야 합니다."
    
    if not changes:
        return "⚠️ 변경된 설정이 없습니다."
        
    return f"✅ 검색 설정이 변경되었습니다:\n" + "\n".join(changes)



# ============================================================================
# 한국관광공사 Tour API 함수들
# ============================================================================

# 지역 코드 매핑 (시/도)
AREA_CODES = {
    "서울": "1", "인천": "2", "대전": "3", "대구": "4", "광주": "5",
    "부산": "6", "울산": "7", "세종": "8", "경기": "31", "강원": "32",
    "충북": "33", "충남": "34", "경북": "35", "경남": "36", "전북": "37",
    "전남": "38", "제주": "39"
}


def get_area_code_from_address(address: str) -> Optional[str]:
    """주소에서 지역 코드 추출"""
    for area_name, area_code in AREA_CODES.items():
        if area_name in address:
            return area_code
    return None


def visitkorea_search_keyword(keyword: str, area_code: str = None) -> str:
    """VisitKorea API 키워드 검색"""
    if not VISITKOREA_API_KEY:
        return "❌ Tour API 키가 없습니다."
    
    params = {
        "serviceKey": VISITKOREA_API_KEY,
        "numOfRows": "10",
        "pageNo": "1",
        "MobileOS": "ETC",
        "MobileApp": "TourApp",
        "_type": "json",
        "listYN": "Y",
        "arrange": "A",  # 정렬 (A=제목순, B=조회순, C=수정일순, D=생성일순)
        "keyword": keyword,
        "contentTypeId": "12"  # 12=관광지
    }
    
    if area_code:
        params["areaCode"] = area_code
    
    try:
        response = requests.get(VISITKOREA_API_SEARCH_KEYWORD_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        items = result.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not items:
            return f"'{keyword}' 관련 관광지를 찾을 수 없습니다."
        
        # 리스트가 아니면 리스트로 변환
        if isinstance(items, dict):
            items = [items]
        
        formatted_results = []
        for i, item in enumerate(items[:10], 1):
            formatted_results.append({
                '순번': i,
                '장소명': item.get('title', 'N/A'),
                '주소': item.get('addr1', 'N/A'),
                '전화': item.get('tel', 'N/A'),
                'Content_ID': item.get('contentid', ''),
                'Content_Type': item.get('contenttypeid', '')
            })
        
        return json.dumps(formatted_results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"❌ VisitKorea API 오류: {str(e)}"


def visitkorea_detail_common(content_id: str) -> dict:
    """VisitKorea API 공통 상세 정보 조회"""
    if not VISITKOREA_API_KEY:
        return {}
    
    params = {
        "serviceKey": VISITKOREA_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "TourApp",
        "_type": "json",
        "contentId": content_id,
        "defaultYN": "Y",
        "firstImageYN": "Y",
        "areacodeYN": "Y",
        "catcodeYN": "Y",
        "addrinfoYN": "Y",
        "mapinfoYN": "Y",
        "overviewYN": "Y"
    }
    
    try:
        response = requests.get(VISITKOREA_API_DETAIL_COMMON_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        items = result.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if items:
            return items[0] if isinstance(items, list) else items
        return {}
    except Exception as e:
        print(f"⚠️  VisitKorea API 공통 정보 조회 실패: {e}")
        return {}


def visitkorea_detail_intro(content_id: str, content_type: str = "12") -> dict:
    """VisitKorea API 소개 정보 조회 (관광지 특화 정보)"""
    if not VISITKOREA_API_KEY:
        return {}
    
    params = {
        "serviceKey": VISITKOREA_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "TourApp",
        "_type": "json",
        "contentId": content_id,
        "contentTypeId": content_type
    }
    
    try:
        response = requests.get(VISITKOREA_API_DETAIL_INTRO_URL, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        items = result.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if items:
            return items[0] if isinstance(items, list) else items
        return {}
    except Exception as e:
        print(f"⚠️  VisitKorea API 소개 정보 조회 실패: {e}")
        return {}


def visitkorea_get_detailed_info(content_id: str, content_type: str = "12") -> str:
    """VisitKorea API 상세 정보 통합 조회"""
    if not VISITKOREA_API_KEY:
        return "❌ VisitKorea API 키가 없습니다."
    
    # 공통 정보 + 소개 정보 조회
    common_info = visitkorea_detail_common(content_id)
    intro_info = visitkorea_detail_intro(content_id, content_type)
    
    if not common_info:
        return "❌ 상세 정보를 찾을 수 없습니다."
    
    # 정보 포맷팅
    info = f"""
📍 {common_info.get('title', 'N/A')}

📝 설명: {common_info.get('overview', '정보 없음')[:200]}...

🏠 주소: {common_info.get('addr1', 'N/A')}
📞 전화번호: {common_info.get('tel', 'N/A')}
🌐 홈페이지: {common_info.get('homepage', 'N/A')}

⏰ 이용시간: {intro_info.get('usetime', 'N/A')}
💰 입장료: {intro_info.get('usefee', 'N/A')}
🅿️ 주차: {intro_info.get('parking', 'N/A')}
🚻 화장실: {intro_info.get('restdate', 'N/A')}

🚌 대중교통: {intro_info.get('publictransport', 'N/A')}

👶 유모차 대여: {intro_info.get('chkbabycarriage', 'N/A')}
🐕 반려동물: {intro_info.get('chkpet', 'N/A')}
"""
    return info



def google_places_text_search(query: str) -> str:
    """텍스트 기반 관광지 검색"""
    if not GOOGLE_PLACES_API_KEY:
        return "❌ API 키가 없습니다."
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.id,places.types,places.primaryType,places.businessStatus,places.currentOpeningHours,places.regularOpeningHours,places.priceLevel,places.websiteUri,places.internationalPhoneNumber,places.editorialSummary,places.accessibilityOptions,places.parkingOptions,places.paymentOptions,places.restroom,places.goodForChildren,places.goodForGroups,places.allowsDogs"
    }
    
    data = {
        "textQuery": f"{query} 관광지",
        "languageCode": "ko",
        "maxResultCount": SEARCH_PREFERENCES['max_results'],
        "includedType": "tourist_attraction"
    }
    
    try:
        response = requests.post(GOOGLE_PLACES_TEXT_SEARCH_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        places = result.get('places', [])
        if not places:
            return f"'{query}' 관련 관광지를 찾을 수 없습니다."
        
        # 정렬 로직 적용
        sort_by = SEARCH_PREFERENCES['sort_by']
        
        if sort_by == 'rating':
            # 평점 높은 순
            places.sort(key=lambda x: (x.get('rating', 0) or 0), reverse=True)
        elif sort_by == 'popularity':
            # 평점 + 리뷰 수 (기본)
            places.sort(key=lambda x: (x.get('rating', 0) or 0, x.get('userRatingCount', 0) or 0), reverse=True)
        # distance는 텍스트 검색에서 지원 안 함 (API 레벨) -> popularity와 동일하게 처리
        
        formatted_results = []
        for i, place in enumerate(places, 1):
            # businessStatus 확인 (OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY)
            business_status = place.get('businessStatus', '')
            
            # currentOpeningHours에서 openNow 확인
            opening_hours = place.get('currentOpeningHours', {})
            is_open = opening_hours.get('openNow', None)
            
            # 영업상태 결정
            if business_status == 'CLOSED_PERMANENTLY':
                status = '영구 폐업'
            elif business_status == 'CLOSED_TEMPORARILY':
                status = '임시 휴업'
            elif is_open is True:
                status = '영업 중'
            elif is_open is False:
                status = '영업 종료'
            elif business_status == 'OPERATIONAL':
                status = '운영 중 (시간 정보 없음)'
            else:
                status = '정보 없음'
            
            formatted_results.append({
                '순위': i,
                '장소명': place.get('displayName', {}).get('text', 'N/A'),
                '주소': place.get('formattedAddress', 'N/A'),
                '평점': f"{place.get('rating', 'N/A')} ⭐",
                '리뷰수': f"{place.get('userRatingCount', 0)}개",
                '영업상태': status,
                '설명': place.get('editorialSummary', {}).get('text', '설명 없음')[:100],
                'Place_ID': place.get('id', '').replace('places/', '')
            })
        
        return json.dumps(formatted_results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"❌ 오류: {str(e)}"


def google_places_nearby_search(latitude: float, longitude: float, radius: int = 5000) -> str:
    """위치 기반 관광지 검색"""
    if not GOOGLE_PLACES_API_KEY:
        return "❌ API 키가 없습니다."
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.id,places.types,places.primaryType,places.businessStatus,places.currentOpeningHours,places.regularOpeningHours,places.priceLevel,places.websiteUri,places.internationalPhoneNumber,places.editorialSummary,places.accessibilityOptions,places.parkingOptions,places.paymentOptions,places.restroom,places.goodForChildren,places.goodForGroups,places.allowsDogs"
    }
    
    # 설정된 반경 사용 (인자가 없으면)
    if radius == 5000 and SEARCH_PREFERENCES['radius'] != 5000:
        radius = SEARCH_PREFERENCES['radius']

    # 정렬 기준 설정
    rank_preference = "DISTANCE" if SEARCH_PREFERENCES['sort_by'] == 'distance' else "POPULARITY"
    # Google Places API New는 rankPreference로 DISTANCE 지원, POPULARITY는 기본값(관련성 등)이나 여기서는 API 호출 후 수동 정렬로 처리
    # API 파라미터로는 DISTANCE만 명시적으로 사용 가능 (POPULARITY는 없음, 생략 시 기본)
    
    data = {
        "includedTypes": ["tourist_attraction"],
        "maxResultCount": SEARCH_PREFERENCES['max_results'],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius
            }
        },
        "languageCode": "ko"
    }
    
    if SEARCH_PREFERENCES['sort_by'] == 'distance':
        data["rankPreference"] = "DISTANCE"
        # 거리순 정렬 시 반경 제한 불가 (API 제약) -> circle 대신 locationRestriction 변경 필요할 수 있음
        # 하지만 New API에서는 circle과 rankPreference=DISTANCE 함께 사용 시 오류 가능성 있음.
        # 문서상: rankPreference=DISTANCE 시 locationRestriction 생략하거나 circle radius 생략?
        # 안전하게: 거리순일 때도 일단 가져오고 API가 지원하면 씀. 
        # *실제 API 동작*: DISTANCE 사용 시 radius 무시됨.
        del data["locationRestriction"]["circle"]["radius"]
    
    try:
        response = requests.post(GOOGLE_PLACES_NEARBY_SEARCH_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        places = result.get('places', [])
        if not places:
            return f"위도 {latitude}, 경도 {longitude} 근처에 관광지가 없습니다."
        
        # 수동 정렬 (API가 DISTANCE가 아닐 때)
        sort_by = SEARCH_PREFERENCES['sort_by']
        if sort_by == 'rating':
            places.sort(key=lambda x: (x.get('rating', 0) or 0), reverse=True)
        elif sort_by == 'popularity':
            places.sort(key=lambda x: (x.get('rating', 0) or 0, x.get('userRatingCount', 0) or 0), reverse=True)
        # distance일 경우 API가 이미 정렬해서 줌
        
        formatted_results = []
        for i, place in enumerate(places, 1):
            # businessStatus 확인 (OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY)
            business_status = place.get('businessStatus', '')
            
            # currentOpeningHours에서 openNow 확인
            opening_hours = place.get('currentOpeningHours', {})
            is_open = opening_hours.get('openNow', None)
            
            # 영업상태 결정
            if business_status == 'CLOSED_PERMANENTLY':
                status = '영구 폐업'
            elif business_status == 'CLOSED_TEMPORARILY':
                status = '임시 휴업'
            elif is_open is True:
                status = '영업 중'
            elif is_open is False:
                status = '영업 종료'
            elif business_status == 'OPERATIONAL':
                status = '운영 중 (시간 정보 없음)'
            else:
                status = '정보 없음'
            
            formatted_results.append({
                '순위': i,
                '장소명': place.get('displayName', {}).get('text', 'N/A'),
                '주소': place.get('formattedAddress', 'N/A'),
                '평점': f"{place.get('rating', 'N/A')} ⭐",
                '리뷰수': f"{place.get('userRatingCount', 0)}개",
                '영업상태': status,
                '설명': place.get('editorialSummary', {}).get('text', '설명 없음')[:100],
                'Place_ID': place.get('id', '').replace('places/', '')
            })
        
        return json.dumps(formatted_results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"❌ 오류: {str(e)}"


def google_places_details(place_id: str) -> str:
    """장소 상세 정보 조회"""
    if not GOOGLE_PLACES_API_KEY:
        return "❌ API 키가 없습니다."
    
    if not place_id.startswith('places/'):
        place_id = f"places/{place_id}"
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "id,displayName,formattedAddress,internationalPhoneNumber,websiteUri,regularOpeningHours,rating,userRatingCount,reviews,priceLevel"
    }
    
    try:
        url = f"{GOOGLE_PLACES_DETAILS_URL}/{place_id}"
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        place = response.json()
        
        opening_hours = place.get('regularOpeningHours', {})
        weekday_descriptions = opening_hours.get('weekdayDescriptions', [])
        hours_text = '\n   '.join(weekday_descriptions) if weekday_descriptions else '정보 없음'
        
        reviews = place.get('reviews', [])[:3]
        reviews_text = ""
        for i, review in enumerate(reviews, 1):
            author = review.get('authorAttribution', {}).get('displayName', '익명')
            rating = review.get('rating', 'N/A')
            text = review.get('text', {}).get('text', '')[:100]
            reviews_text += f"\n   {i}. {author}: {rating}⭐\n      \"{text}...\"\n"
        
        price_map = {
            'PRICE_LEVEL_FREE': '무료',
            'PRICE_LEVEL_INEXPENSIVE': '₩',
            'PRICE_LEVEL_MODERATE': '₩₩',
            'PRICE_LEVEL_EXPENSIVE': '₩₩₩',
            'PRICE_LEVEL_VERY_EXPENSIVE': '₩₩₩₩'
        }
        price_text = price_map.get(place.get('priceLevel'), 'N/A')
        
        info = f"""
📍 {place.get('displayName', {}).get('text', 'N/A')}

⭐ 평점: {place.get('rating', 'N/A')} ({place.get('userRatingCount', 0)}개 리뷰)
💰 가격대: {price_text}

🏠 주소: {place.get('formattedAddress', 'N/A')}
📞 전화번호: {place.get('internationalPhoneNumber', 'N/A')}
🌐 웹사이트: {place.get('websiteUri', 'N/A')}

⏰ 영업시간:
   {hours_text}

💬 최근 리뷰:{reviews_text if reviews_text else '\n   리뷰 없음'}
"""
        return info
    except Exception as e:
        return f"❌ 오류: {str(e)}"


def create_tools() -> List[Tool]:
    """도구 생성"""
    from langchain_core.tools import StructuredTool
    
    tools = [
        StructuredTool.from_function(
            func=google_places_text_search,
            name="google_places_text_search",
            description="텍스트 기반 관광지 검색 (Google Places)"
        ),
        StructuredTool.from_function(
            func=google_places_nearby_search,
            name="google_places_nearby_search",
            description="위치 기반 관광지 검색 (Google Places)"
        ),
        StructuredTool.from_function(
            func=google_places_details,
            name="google_places_details",
            description="Google Places 상세 정보 조회"
        ),
        StructuredTool.from_function(
            func=set_search_preferences,
            name="set_search_preferences",
            description="검색 설정 변경 (반경, 정렬, 결과수). 예: radius=10000, sort_by='distance'"
        )
    ]
    
    # VisitKorea API 도구 추가 (키가 있을 때만)
    if VISITKOREA_API_KEY:
        tools.extend([
            StructuredTool.from_function(
                func=visitkorea_search_keyword,
                name="visitkorea_search",
                description="한국 관광지 키워드 검색 (VisitKorea API)"
            ),
            StructuredTool.from_function(
                func=visitkorea_get_detailed_info,
                name="visitkorea_detail",
                description="한국 관광지 상세 정보 조회 (VisitKorea API)"
            )
        ])
    
    return tools


def create_tourist_agent(current_lat=None, current_lng=None):
    """에이전트 생성"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=OPENAI_API_KEY)
    tools = create_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    location_info = ""
    if current_lat and current_lng:
        location_info = f"""

📍 사용자의 현재 위치: 위도 {current_lat:.4f}, 경도 {current_lng:.4f}

사용자가 "내 주변", "근처", "내가 있는 위치" 등을 언급하면:
→ google_places_nearby_search("{current_lat}, {current_lng}")를 사용하세요!
"""
    
    visitkorea_api_info = ""
    if VISITKOREA_API_KEY:
        visitkorea_api_info = """

🇰🇷 한국 관광지 특화 정보 (VisitKorea API 사용 가능):
- 입장료 상세 정보
- 이용시간 및 휴무일
- 주차 정보
- 대중교통 안내
- 편의시설 (유모차, 반려동물 등)

도구 선택 가이드:
1. 한국 관광지 검색 → visitkorea_search (한국 특화 정보)
2. 글로벌 관광지 검색 → google_places_text_search
3. 한국 관광지 상세 정보 → visitkorea_detail (입장료, 교통 등)
4. 글로벌 관광지 상세 정보 → google_places_details
5. 검색 설정 변경 → set_search_preferences (반경, 정렬 등)
   - "넓게 찾아줘", "10km 반경" → radius=10000
   - "거리순으로", "가까운 순" → sort_by='distance'
   - "인기순으로", "유명한 순" → sort_by='popularity'
"""
    
    system_prompt = f"""당신은 한국 관광 전문 AI 가이드입니다.
{location_info}{visitkorea_api_info}
⚠️ 중요: 오직 '관광지'만 추천합니다.
(검색 결과는 이미 **평점 높고 리뷰 많은 순**으로 정렬되어 있습니다. 상위 결과 위주로 추천하세요.)

📋 관광지 추천 시 반드시 포함할 정보:
1. **장소명**
2. **주소** (formattedAddress)
3. **평점** (rating) - 있으면 반드시 표시, 없으면 "평점 없음"
4. **리뷰수** (userRatingCount) - 있으면 반드시 표시
5. **영업상태** (businessStatus)
6. **간단한 설명** (editorialSummary 또는 일반 설명) - 검색 결과에 포함되어 있습니다.

⚠️ 평점이 도구 결과에 있으면 반드시 사용자에게 보여주세요!
예시: "평점: 4.5 ⭐ (120개 리뷰)"

⚠️ 검색 결과에 이미 '설명'이 포함되어 있습니다. 단순 설명을 위해 `google_places_details`를 호출하지 마세요!
입장료, 상세 이용시간 등이 필요할 때만 상세 조회를 하세요.

도구 선택 규칙 (매우 중요):
1. **"내 주변", "근처", "여기"** (사용자 위치 기준)
   → `google_places_nearby_search(lat, lng)` 사용
   
2. **"강릉역 근처", "서울역 주변", "부산 관광지"** (특정 장소 기준)
   → `google_places_text_search("강릉역 근처 관광지")` 사용
   ⚠️ 절대 `google_places_nearby_search`에 현재 위치 좌표를 넣지 마세요! 사용자가 언급한 장소가 기준입니다.

3. **상세 정보 (입장료, 이용시간 등)**
   - **한국 관광지**: `visitkorea_search`로 검색 후 `visitkorea_detail` 사용 (가장 정확함)
   - **글로벌 관광지**: `google_places_details` 사용

⚠️ "입장료 얼마야?", "이용시간 알려줘" 같은 질문에는 반드시 `visitkorea_detail`을 통해 정확한 정보를 찾아보세요!
"""
    
    return llm_with_tools, system_prompt, tools


def main():
    """메인 함수"""
    print("=" * 70)
    print("🗺️  한국 관광지 추천 AI 에이전트 (위치 기반)")
    print("=" * 70)
    print("\n💡 기능: 관광지 검색, 상세 정보, 위치 기반 검색")
    
    # API 상태 표시
    api_status = []
    if GOOGLE_PLACES_API_KEY:
        api_status.append("Google Places ✅")
    if VISITKOREA_API_KEY:
        api_status.append("VisitKorea API ✅")
    
    if api_status:
        print(f"🔑 사용 가능한 API: {', '.join(api_status)}")
    
    print("📝 예시: '서울 관광지', '천안역 근처', '내 주변 관광지'")
    print("종료: 'quit', 'exit', '종료'\n")
    
    # 자동으로 위치 감지
    print("=" * 70)
    print("📍 현재 위치를 자동으로 감지합니다...")
    print("=" * 70)
    print()
    
    current_lat, current_lng = get_current_location()
    
    # 자동 감지 실패 시 프로그램 종료
    if not current_lat or not current_lng:
        print("\n" + "=" * 70)
        print("❌ 위치를 자동으로 감지하지 못했습니다.")
        print("⚠️  이 프로그램은 위치 기반으로 동작하므로 종료합니다.")
        print("=" * 70)
        return
    
    print(f"\n✅ 설정된 위치: 위도 {current_lat:.6f}, 경도 {current_lng:.6f}")
    print("=" * 70)
    print()
    
    if not OPENAI_API_KEY or not GOOGLE_PLACES_API_KEY:
        print("⚠️  API 키가 설정되지 않았습니다.")
        return
    
    try:
        print("🔄 에이전트 초기화 중...\n")
        llm_with_tools, system_prompt, tools = create_tourist_agent(current_lat, current_lng)
        tool_map = {tool.name: tool.func for tool in tools}
        print("✅ 에이전트 준비 완료!\n")
    except Exception as e:
        print(f"❌ 에이전트 생성 실패: {str(e)}")
        return
    
    messages = []
    
    while True:
        try:
            user_input = input("💬 질문: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                print("\n👋 감사합니다!")
                break
            
            if not user_input:
                continue
            
            print()
            messages.append(HumanMessage(content=user_input))
            
            full_messages = [HumanMessage(content=system_prompt)] + messages
            response = llm_with_tools.invoke(full_messages)
            
            # 도구 실행 루프 (최대 5회 반복)
            max_iterations = 5
            current_iteration = 0
            
            while hasattr(response, 'tool_calls') and response.tool_calls and current_iteration < max_iterations:
                current_iteration += 1
                print(f"🔧 도구 사용 중 ({current_iteration}/{max_iterations})... (병렬 실행)")
                
                # 병렬 실행을 위한 Executor 생성
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future_to_tool = {}
                    
                    for tool_call in response.tool_calls:
                        tool_name = tool_call['name']
                        tool_args = tool_call['args']
                        tool_call_id = tool_call['id']
                        
                        if tool_name in tool_map:
                            print(f"   - {tool_name} 실행 요청...")
                            
                            # 실행할 함수와 인자 준비
                            if tool_name == "google_places_details":
                                place_id = tool_args.get('place_id', '') or tool_args.get('query', '')
                                func = tool_map[tool_name]
                                args = (place_id,)
                            elif tool_name == "visitkorea_detail":
                                content_id = tool_args.get('content_id', '')
                                func = tool_map[tool_name]
                                args = (content_id,)
                            elif tool_name == "google_places_nearby_search":
                                # args가 dict로 올 수 있음 (bind_tools 사용 시)
                                lat = tool_args.get('latitude')
                                lng = tool_args.get('longitude')
                                rad = tool_args.get('radius', 5000)
                                func = tool_map[tool_name]
                                args = (lat, lng, rad)
                            elif tool_name == "set_search_preferences":
                                func = tool_map[tool_name]
                                args = (tool_args.get('sort_by'), tool_args.get('radius'), tool_args.get('max_results'))
                            else:
                                # 일반적인 경우
                                if tool_name == "visitkorea_search":
                                    func = tool_map[tool_name]
                                    args = (tool_args.get('keyword', ''), tool_args.get('area_code'))
                                elif tool_name == "google_places_text_search":
                                    func = tool_map[tool_name]
                                    args = (tool_args.get('query', ''),)
                                else:
                                    # fallback
                                    func = tool_map[tool_name]
                                    args = (tool_args,)
                            
                            # Future 제출
                            future = executor.submit(func, *args)
                            future_to_tool[future] = tool_call
                        else:
                            print(f"❌ 알 수 없는 도구: {tool_name}")
                            full_messages.append(ToolMessage(
                                tool_call_id=tool_call_id,
                                content=f"Error: Tool {tool_name} not found"
                            ))

                    # 결과 수집
                    for future in concurrent.futures.as_completed(future_to_tool):
                        tool_call = future_to_tool[future]
                        tool_name = tool_call['name']
                        tool_call_id = tool_call['id']
                        
                        try:
                            result = future.result()
                            # 결과 출력 (너무 길면 자름)
                            print(f"   ✅ {tool_name} 완료 ({len(str(result))} bytes)")
                        except Exception as e:
                            print(f"   ❌ {tool_name} 실패: {e}")
                            result = f"Error executing {tool_name}: {str(e)}"
                        
                        full_messages.append(ToolMessage(
                            tool_call_id=tool_call_id,
                            content=str(result)
                        ))
                
                # ... (이전 코드) ...

        # 최종 응답 출력
    messages.append(AIMessage(content=response.content))

    print(f"\n{'='*70}")
    print(f"🤖 답변:\n{response.content}")  # ✅ 직접 출력
    print(f"{'='*70}\n")
           