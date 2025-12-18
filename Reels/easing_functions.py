"""
이징(Easing) 함수 모음
부드러운 애니메이션을 위한 다양한 이징 함수 제공
"""
import math


def linear(t: float) -> float:
    """
    선형 이징 (기본)
    
    Args:
        t: 진행률 (0.0 ~ 1.0)
    
    Returns:
        이징 적용된 값 (0.0 ~ 1.0)
    """
    return t


def ease_in_quad(t: float) -> float:
    """
    2차 가속 (천천히 시작)
    """
    return t * t


def ease_out_quad(t: float) -> float:
    """
    2차 감속 (빠르게 시작, 천천히 끝)
    """
    return t * (2 - t)


def ease_in_out_quad(t: float) -> float:
    """
    2차 가속/감속 (부드러운 시작과 끝)
    """
    if t < 0.5:
        return 2 * t * t
    else:
        return -1 + (4 - 2 * t) * t


def ease_in_cubic(t: float) -> float:
    """
    3차 가속 (더 천천히 시작)
    """
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """
    3차 감속 (더 빠르게 시작, 더 천천히 끝)
    """
    t -= 1
    return t * t * t + 1


def ease_in_out_cubic(t: float) -> float:
    """
    3차 가속/감속 (매우 부드러운 시작과 끝) - 추천!
    """
    if t < 0.5:
        return 4 * t * t * t
    else:
        t = 2 * t - 2
        return (t * t * t + 2) / 2


def ease_in_quart(t: float) -> float:
    """
    4차 가속
    """
    return t * t * t * t


def ease_out_quart(t: float) -> float:
    """
    4차 감속
    """
    t -= 1
    return 1 - t * t * t * t


def ease_in_out_quart(t: float) -> float:
    """
    4차 가속/감속
    """
    if t < 0.5:
        return 8 * t * t * t * t
    else:
        t -= 1
        return 1 - 8 * t * t * t * t


def ease_in_sine(t: float) -> float:
    """
    사인 가속 (부드러운 시작)
    """
    return 1 - math.cos(t * math.pi / 2)


def ease_out_sine(t: float) -> float:
    """
    사인 감속 (부드러운 끝)
    """
    return math.sin(t * math.pi / 2)


def ease_in_out_sine(t: float) -> float:
    """
    사인 가속/감속 (매우 부드러움) - 추천!
    """
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_expo(t: float) -> float:
    """
    지수 가속 (매우 천천히 시작)
    """
    return 0 if t == 0 else math.pow(2, 10 * (t - 1))


def ease_out_expo(t: float) -> float:
    """
    지수 감속 (매우 빠르게 시작)
    """
    return 1 if t == 1 else 1 - math.pow(2, -10 * t)


def ease_in_out_expo(t: float) -> float:
    """
    지수 가속/감속
    """
    if t == 0 or t == 1:
        return t
    
    if t < 0.5:
        return math.pow(2, 20 * t - 10) / 2
    else:
        return (2 - math.pow(2, -20 * t + 10)) / 2


def ease_in_elastic(t: float) -> float:
    """
    탄성 가속 (튕기는 효과)
    """
    if t == 0 or t == 1:
        return t
    
    c4 = (2 * math.pi) / 3
    return -math.pow(2, 10 * t - 10) * math.sin((t * 10 - 10.75) * c4)


def ease_out_elastic(t: float) -> float:
    """
    탄성 감속 (튕기는 효과) - 재미있는 효과!
    """
    if t == 0 or t == 1:
        return t
    
    c4 = (2 * math.pi) / 3
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * c4) + 1


def ease_in_out_elastic(t: float) -> float:
    """
    탄성 가속/감속
    """
    if t == 0 or t == 1:
        return t
    
    c5 = (2 * math.pi) / 4.5
    
    if t < 0.5:
        return -(math.pow(2, 20 * t - 10) * math.sin((20 * t - 11.125) * c5)) / 2
    else:
        return (math.pow(2, -20 * t + 10) * math.sin((20 * t - 11.125) * c5)) / 2 + 1


def ease_out_back(t: float) -> float:
    """
    백 감속 (살짝 넘어갔다가 돌아옴) - 역동적!
    """
    c1 = 1.70158
    c3 = c1 + 1
    
    return 1 + c3 * math.pow(t - 1, 3) + c1 * math.pow(t - 1, 2)


def ease_in_out_back(t: float) -> float:
    """
    백 가속/감속
    """
    c1 = 1.70158
    c2 = c1 * 1.525
    
    if t < 0.5:
        return (math.pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    else:
        return (math.pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


# 이징 함수 매핑
EASING_FUNCTIONS = {
    "linear": linear,
    "ease_in_quad": ease_in_quad,
    "ease_out_quad": ease_out_quad,
    "ease_in_out_quad": ease_in_out_quad,
    "ease_in_cubic": ease_in_cubic,
    "ease_out_cubic": ease_out_cubic,
    "ease_in_out_cubic": ease_in_out_cubic,  # 추천
    "ease_in_quart": ease_in_quart,
    "ease_out_quart": ease_out_quart,
    "ease_in_out_quart": ease_in_out_quart,
    "ease_in_sine": ease_in_sine,
    "ease_out_sine": ease_out_sine,
    "ease_in_out_sine": ease_in_out_sine,  # 추천
    "ease_in_expo": ease_in_expo,
    "ease_out_expo": ease_out_expo,
    "ease_in_out_expo": ease_in_out_expo,
    "ease_in_elastic": ease_in_elastic,
    "ease_out_elastic": ease_out_elastic,
    "ease_in_out_elastic": ease_in_out_elastic,
    "ease_out_back": ease_out_back,  # 추천
    "ease_in_out_back": ease_in_out_back,
}


def get_easing_function(name: str):
    """
    이름으로 이징 함수 가져오기
    
    Args:
        name: 이징 함수 이름
    
    Returns:
        이징 함수
    """
    return EASING_FUNCTIONS.get(name, ease_in_out_cubic)
