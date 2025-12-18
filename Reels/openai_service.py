"""
OpenAI API를 활용한 AI 서비스
- 이미지 분석 (GPT-4 Vision)
- 스토리 및 캡션 생성 (GPT-4)
- 음성 나레이션 생성 (TTS)
- 비디오 생성 (Sora) - 제거됨
"""
import os
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
from PIL import Image
import io
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()


class OpenAIService:
    """OpenAI API 서비스"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 가져옴)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.vision_model = "gpt-4o"  # GPT-4 Turbo with Vision
        self.text_model = "gpt-4o"
        self.tts_model = "tts-1"  # 또는 "tts-1-hd" (고품질)
        self.tts_model = "tts-1"  # 또는 "tts-1-hd" (고품질)
    
    def encode_image(self, image_path: Path) -> str:
        """
        이미지를 base64로 인코딩
        
        Args:
            image_path: 이미지 파일 경로
            
        Returns:
            base64 인코딩된 이미지 문자열
        """
        # 이미지 크기 조정 (API 비용 절감)
        img = Image.open(image_path)
        
        # RGBA를 RGB로 변환 (PNG 투명도 처리)
        if img.mode == 'RGBA':
            # 흰색 배경 생성
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # 알파 채널을 마스크로 사용
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 최대 크기 제한 (긴 쪽 기준 1024px)
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # base64 인코딩
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def analyze_images(self, image_paths: List[Path]) -> Dict[str, Any]:
        """
        여러 이미지를 분석하여 여행 정보 추출
        
        Args:
            image_paths: 이미지 파일 경로 리스트
            
        Returns:
            분석 결과 딕셔너리
        """
        print(f"[AI] {len(image_paths)}장의 사진 분석 중...")
        
        # 최대 10장까지만 분석 (비용 절감)
        sample_images = image_paths[:10] if len(image_paths) > 10 else image_paths
        
        # 이미지를 base64로 인코딩
        image_contents = []
        for img_path in sample_images:
            try:
                base64_image = self.encode_image(img_path)
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "low"  # "low" 또는 "high" (비용 차이)
                    }
                })
            except Exception as e:
                print(f"이미지 인코딩 오류 ({img_path.name}): {e}")
        
        # GPT-4 Vision으로 분석
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """이 여행 사진들을 분석해주세요. 다음 정보를 JSON 형식으로 제공해주세요:

{
  "destination": "여행지 이름 (예: 제주도, 파리, 도쿄)",
  "theme": "여행 테마 (예: 자연, 도시, 음식, 문화, 휴양)",
  "mood": "전체적인 분위기 (예: 평화로운, 활기찬, 로맨틱, 모험적)",
  "highlights": ["주요 특징 1", "주요 특징 2", "주요 특징 3"],
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
}

여행 플랫폼의 홍보 릴스를 만들 예정이니, 매력적이고 감성적인 표현을 사용해주세요."""
                    },
                    *image_contents
                ]
            }
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content)
            print(f"[AI] 분석 완료: {analysis.get('destination', '알 수 없음')}")
            return analysis
            
        except Exception as e:
            print(f"[AI] 이미지 분석 오류: {e}")
            # 기본값 반환
            return {
                "destination": "여행지",
                "theme": "여행",
                "mood": "즐거운",
                "highlights": ["아름다운 풍경", "특별한 순간", "잊지 못할 추억"],
                "keywords": ["여행", "추억", "행복", "힐링", "모험"]
            }
    
    def generate_story(self, analysis: Dict[str, Any], photo_count: int) -> Dict[str, Any]:
        """
        분석 결과를 바탕으로 여행 스토리 생성
        
        Args:
            analysis: 이미지 분석 결과
            photo_count: 사진 개수
            
        Returns:
            스토리 및 캡션 딕셔너리
        """
        print("[AI] 여행 스토리 생성 중...")
        
        prompt = f"""여행 플랫폼의 홍보 릴스를 위한 스토리를 작성해주세요.

**여행 정보:**
- 여행지: {analysis.get('destination', '여행지')}
- 테마: {analysis.get('theme', '여행')}
- 분위기: {analysis.get('mood', '즐거운')}
- 주요 특징: {', '.join(analysis.get('highlights', []))}
- 사진 개수: {photo_count}장

**요구사항:**
1. 15-20초 분량의 짧은 나레이션 (약 50-70자)
2. 감성적이고 매력적인 문구
3. 여행을 떠나고 싶게 만드는 내용
4. 각 사진에 어울리는 짧은 캡션 {photo_count}개

JSON 형식으로 응답해주세요:
{{
  "title": "릴스 제목 (10자 이내)",
  "narration": "나레이션 텍스트",
  "captions": ["캡션1", "캡션2", ...],
  "hashtags": ["#해시태그1", "#해시태그2", ...]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": "당신은 여행 콘텐츠 전문 카피라이터입니다. 감성적이고 매력적인 문구를 작성합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            import json
            story = json.loads(response.choices[0].message.content)
            print(f"[AI] 스토리 생성 완료: {story.get('title', '')}")
            return story
            
        except Exception as e:
            print(f"[AI] 스토리 생성 오류: {e}")
            # 기본값 반환
            return {
                "title": f"{analysis.get('destination', '여행')} 여행",
                "narration": f"{analysis.get('destination', '이곳')}에서의 특별한 순간들. 당신의 여행을 시작하세요.",
                "captions": [f"순간 {i+1}" for i in range(photo_count)],
                "hashtags": ["#여행", "#힐링", "#추억"]
            }
    
    def generate_narration_audio(
        self, 
        text: str, 
        output_path: Path,
        voice: str = "nova"  # alloy, echo, fable, onyx, nova, shimmer
    ) -> bool:
        """
        텍스트를 음성으로 변환
        
        Args:
            text: 변환할 텍스트
            output_path: 출력 오디오 파일 경로
            voice: 음성 종류
            
        Returns:
            성공 여부
        """
        print(f"[AI] 음성 나레이션 생성 중... (음성: {voice})")
        
        try:
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice,
                input=text,
                speed=1.0  # 0.25 ~ 4.0
            )
            
            # 오디오 파일 저장
            output_path.parent.mkdir(parents=True, exist_ok=True)
            response.stream_to_file(str(output_path))
            
            print(f"[AI] 나레이션 생성 완료: {output_path.name}")
            return True
            
        except Exception as e:
            print(f"[AI] TTS 생성 오류: {e}")
            return False
    
    def analyze_single_image(self, image_path: Path, style: str = "descriptive") -> str:
        """
        개별 이미지를 분석하여 짧은 설명 텍스트 생성
        
        Args:
            image_path: 이미지 파일 경로
            style: 텍스트 스타일 (descriptive/poetic/simple)
            
        Returns:
            생성된 캡션 텍스트 (10-15자 이내)
        """
        try:
            # 이미지를 base64로 인코딩
            base64_image = self.encode_image(image_path)
            
            # 스타일별 프롬프트
            style_prompts = {
                "descriptive": "이 사진의 주요 내용을 10-15자 이내의 한글로 간결하게 설명해주세요. (예: '해변의 석양', '도심 야경', '맛있는 음식')",
                "poetic": "이 사진의 분위기를 10-15자 이내의 감성적인 한글 문구로 표현해주세요. (예: '황금빛 추억', '별이 빛나는 밤', '행복한 순간')",
                "simple": "이 사진을 10-15자 이내의 짧은 한글 단어로 표현해주세요. (예: '여유로운 오후', '특별한 하루', '평화로운 시간')"
            }
            
            prompt = style_prompts.get(style, style_prompts["descriptive"])
            
            # GPT-4 Vision으로 분석
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "low"  # 비용 절감
                                }
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            caption = response.choices[0].message.content.strip()
            # 따옴표 제거
            caption = caption.strip('"\'')
            
            return caption
            
        except Exception as e:
            print(f"[AI] 이미지 분석 오류 ({image_path.name}): {e}")
            # 기본값 반환
            return "특별한 순간"
    
    def generate_captions_for_images(
        self, 
        image_paths: List[Path], 
        analysis: Dict[str, Any]
    ) -> List[str]:
        """
        각 이미지에 맞는 개별 캡션 생성
        
        Args:
            image_paths: 이미지 파일 경로 리스트
            analysis: 전체 여행 분석 결과
            
        Returns:
            캡션 리스트
        """
        print(f"[AI] {len(image_paths)}장의 사진에 대한 캡션 생성 중...")
        
        # 간단한 캡션 생성 (비용 절감)
        captions = []
        theme = analysis.get('theme', '여행')
        mood = analysis.get('mood', '즐거운')
        
        # 미리 정의된 캡션 템플릿
        templates = [
            f"{mood} 순간",
            f"{theme}의 아름다움",
            "특별한 추억",
            "잊지 못할 순간",
            "완벽한 하루",
            "행복한 시간",
            "평화로운 순간",
            "설레는 여행",
            "감동의 순간",
            "힐링 타임"
        ]
        
        for i in range(len(image_paths)):
            caption = templates[i % len(templates)]
            captions.append(caption)
        
        return captions
    



# 편의 함수
def create_ai_reels_content(
    image_paths: List[Path],
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    AI를 사용하여 릴스 콘텐츠 생성 (원스톱 함수)
    
    Args:
        image_paths: 이미지 파일 경로 리스트
        api_key: OpenAI API 키
        
    Returns:
        릴스 콘텐츠 딕셔너리
    """
    service = OpenAIService(api_key)
    
    # 1. 이미지 분석
    analysis = service.analyze_images(image_paths)
    
    # 2. 스토리 생성
    story = service.generate_story(analysis, len(image_paths))
    
    # 3. 개별 캡션 생성
    captions = service.generate_captions_for_images(image_paths, analysis)
    
    return {
        "analysis": analysis,
        "story": story,
        "captions": captions
    }
