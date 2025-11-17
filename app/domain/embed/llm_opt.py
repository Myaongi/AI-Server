import vertexai
from vertexai.generative_models import (
    GenerativeModel, 
    FunctionDeclaration, 
    Tool
)
from typing import Dict, Any, List
import logging

from ...domain import config

logger = logging.getLogger(__name__)

# ----------------------------------------------------
# 1. 함수 선언 정의 (규칙 구조화) - 클래스 외부에서 정의하여 재사용
# ----------------------------------------------------

def get_normalize_declaration() -> FunctionDeclaration:
    """정규화 규칙을 담은 FunctionDeclaration 객체를 반환합니다."""
    
    # dict로 직접 정의 (최신 API 스타일)
    output_schema = {
        "type": "object",
        "properties": {
            "sentence1": {
                "type": "string",
                "description": "The Main Description (Rule 1). Max 25 words. Must include breed, colors, accessory summary (with color/uncolored), and temperament. DO NOT list specific marks from Sentence 2. CRITICAL: You must respond ONLY in English. All output sentences must be in English."
            },
            "sentence2": {
                "type": "string",
                "description": "The Distinctive Features sentence (Rule 2). Max 25 words. Must start with 'Special marks:' or 'Accessories/appearance:'. CRITICAL: You must respond ONLY in English. All output sentences must be in English."
            },
            "sentence3": {
                "type": "string",
                "description": "The Simple Summary sentence (Rule 3). Max 25 words. Format: '[Breed]; colors: [color1], [color2].' Use up to 3 normalized coat colors. CRITICAL: You must respond ONLY in English. All output sentences must be in English."
            },
        },
        "required": ["sentence1", "sentence2", "sentence3"]
    }

    return FunctionDeclaration(
        name="normalize_dog_data",
        description="Strictly normalize dog data into three structured sentences for CLIP encoding. CRITICAL: You must respond ONLY in English. All output sentences must be in English. Never use Korean or any other language.",
        parameters=output_schema,
    )


class DogDataNormalizerService:
    """
    Vertex AI Gemini를 사용하여 반려견 데이터를 정규화하는 서비스 클래스.
    초기화 (vertexai.init)는 서버 실행 시 딱 한 번만 수행됩니다.
    """
    # 클래스 변수: 초기화 상태와 모델 객체를 저장
    is_initialized = False
    llm_model: GenerativeModel = None
    llm_tools: list[Tool] = None

    @classmethod
    def initialize(cls, project_id: str, location: str):
        """서버 실행 시 Vertex AI 환경을 딱 한 번만 초기화합니다."""
        if cls.is_initialized:
            logger.info("Vertex AI는 이미 초기화되었습니다. 스킵합니다.")
            return

        try:
            logger.info(f"Vertex AI 초기화 시작: Project={project_id}, Location={location}")
            # 1. Vertex AI 초기화 (API 인증 및 리전 설정)
            vertexai.init(project=project_id, location=location)

            # 2. 모델 및 도구 설정
            normalize_declaration = get_normalize_declaration()
            cls.llm_tools = [Tool(function_declarations=[normalize_declaration])]
            
            # 3. 모델 객체 로드 및 저장
            cls.llm_model = GenerativeModel("gemini-2.5-flash")

            cls.is_initialized = True
            logger.info("Vertex AI 초기화 완료.")

        except Exception as e:
            logger.error(f"Vertex AI 초기화 실패: {e}")
            # 초기화 실패 시 서버 시작을 중단하거나 적절히 처리해야 합니다.
            raise

    def __init__(self):
        """서비스 인스턴스 생성 시, 초기화가 되었는지 확인합니다."""
        if not self.__class__.is_initialized:
            raise RuntimeError(
                "DogDataNormalizerService가 사용되기 전에 initialize() 메서드를 호출해야 합니다."
            )

    def _extract_function_call_from_response(self, response) -> Dict[str, Any]:
        """
        Vertex AI 응답에서 normalize_dog_data 함수 호출 결과를 추출합니다.
        
        Returns:
            함수 호출 인자 딕셔너리
        
        Raises:
            ValueError: 함수 호출을 찾을 수 없는 경우
        """
        # 최신 API: response.candidates[0].content.parts에서 function_call 찾기
        if not (hasattr(response, 'candidates') and response.candidates):
            raise ValueError("응답에 candidates가 없습니다.")
        
        candidate = response.candidates[0]
        if not (hasattr(candidate, 'content') and candidate.content):
            raise ValueError("candidate에 content가 없습니다.")
        
        if not (hasattr(candidate.content, 'parts') and candidate.content.parts):
            raise ValueError("content에 parts가 없습니다.")
        
        # parts에서 function_call 찾기
        for part in candidate.content.parts:
            # 단수형 function_call 확인
            func_call = getattr(part, 'function_call', None)
            if func_call:
                if getattr(func_call, 'name', None) == "normalize_dog_data":
                    return dict(getattr(func_call, 'args', {}))
                continue
            
            # 복수형 function_calls 확인
            func_calls = getattr(part, 'function_calls', None)
            if func_calls:
                for fc in func_calls:
                    if getattr(fc, 'name', None) == "normalize_dog_data":
                        return dict(getattr(fc, 'args', {}))
        
        # 하위 호환성: response.function_calls 직접 확인
        func_calls = getattr(response, 'function_calls', None)
        if func_calls and len(func_calls) > 0:
            call = func_calls[0]
            if getattr(call, 'name', None) == "normalize_dog_data":
                return dict(getattr(call, 'args', {}))
            raise ValueError(f"예상치 못한 함수 호출: {getattr(call, 'name', 'unknown')}")
        
        # 디버깅 정보 로깅
        logger.error(f"예상치 못한 응답 구조: response type={type(response)}")
        logger.error(f"response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
        raise ValueError("모델이 함수 호출 대신 일반 텍스트를 반환했습니다.")

    # 실제 요청을 보내는 함수
    def normalize_data(self, user_input_message: str) -> Dict[str, Any]:
        """
        초기화된 모델을 사용하여 텍스트 정규화 API를 호출합니다.
        """
        model = self.__class__.llm_model 
        tools = self.__class__.llm_tools

        try:
            response = model.generate_content(
                contents=[user_input_message],
                tools=tools
            )
            
            return self._extract_function_call_from_response(response)

        except Exception as e:
            logger.error(f"정규화 호출 중 오류 발생: {e}")
            raise


# ----------------------------------------------------
# 2. 싱글톤 서비스 인스턴스 (서버 전체에서 공유)
# ----------------------------------------------------
_normalizer_service: DogDataNormalizerService = None


def _get_normalizer_service() -> DogDataNormalizerService:
    """서비스 인스턴스를 반환합니다. (싱글톤 패턴)"""
    global _normalizer_service
    if _normalizer_service is None:
        _normalizer_service = DogDataNormalizerService()
    return _normalizer_service


# ----------------------------------------------------
# 3. 공개 API 함수 (llm_client.py의 normalize_to_3_sentences와 동일한 시그니처)
# ----------------------------------------------------

def normalize_to_3_sentences(breed: str, colors: str, features: str) -> List[str]:
    """
    Vertex AI를 사용하여 강아지 정보를 3개의 문장으로 정규화합니다.
    
    Args:
        breed: 강아지 품종
        colors: 강아지 색상
        features: 강아지 특징 (자유 텍스트)
    
    Returns:
        3개의 정규화된 문장 리스트 (모두 영어)
    """
    # 사용자 입력 메시지 구성 (영어로 명시)
    user_input = f"""
Normalize the following dog information into 3 structured English sentences for CLIP encoding.
You must respond ONLY in English. Never use Korean or any other language.

Breed: {breed or "unknown"}
Colors: {colors or "unknown"}
Free Text Description: {features or "none"}
"""
    
    try:
        # 서비스 인스턴스 가져오기
        service = _get_normalizer_service()
        
        # Vertex AI 호출
        result = service.normalize_data(user_input.strip())
        
        # 결과에서 문장 추출
        sentences = [
            result.get("sentence1", "").strip(),
            result.get("sentence2", "").strip(),
            result.get("sentence3", "").strip()
        ]
        
        # 유효성 검증
        sentences = [s for s in sentences if s]
        
        if len(sentences) < 3:
            logger.warning(f"Insufficient sentences: expected 3, got {len(sentences)}. Using fallback.")
            raise ValueError(f"Insufficient sentences: expected 3, got {len(sentences)}")
        
        return sentences[:3]
        
    except Exception as e:
        logger.error(f"Vertex AI 정규화 실패: {type(e).__name__}: {str(e)}")
        # 폴백 반환 (llm_client.py와 동일한 형식, 모두 영어)
        cs = ", ".join([c.strip() for c in (colors or "").split(",") if c.strip()])
        s1 = f"A {breed or 'unknown'} dog" + (f" with {cs} coat." if cs else ".")
        s2 = "Appearance summary: " + (f"{breed or 'unknown'} with {cs} coat." if cs else "unknown")
        s3 = f"{breed or 'unknown'}; colors: {cs or 'unknown'}."
        return [s1, s2, s3]