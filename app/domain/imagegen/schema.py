from pydantic import BaseModel, Field

class DogImageGenIn(BaseModel):
    """강아지 이미지 생성 요청"""
    breed: str = Field(..., description="강아지 품종 (한국어)")
    colors: str = Field(..., description="강아지 색상 (한국어)")
    features: str = Field(..., description="강아지 특징 및 기타 정보 (한국어)")


