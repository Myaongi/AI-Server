from pydantic import BaseModel, Field
from typing import Dict, List

class ImageAnalysisResponse(BaseModel):
    fileName: str
    contentType: str
    analysisTime: str
    resultMessage: str

class DogBreedResult(BaseModel):
    result: str = Field(..., description="분류된 강아지 품종명 (한국어)")

class BreedMappingUpdate(BaseModel):
    """견종 매핑 업데이트 요청"""
    en: str  # 영어 견종명
    ko: str  # 한글 견종명

class BreedMappingList(BaseModel):
    """견종 매핑 목록 응답"""
    mappings: List[Dict[str, str]]  # [{"en": "Chihuahua", "ko": "치와와"}, ...]

class BreedMappingUpdateResponse(BaseModel):
    """견종 매핑 업데이트 응답"""
    success: bool
    message: str
    