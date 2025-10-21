from pydantic import BaseModel, Field
from typing import List

class TextNormalizeIn(BaseModel):
    breed: str = Field("", description="강아지 품종")
    colors: str = Field("", description="강아지 색상")
    features: str = Field("", description="강아지 특징")

class TextNormalizeOut(BaseModel):
    sentences: List[str] = Field(default_factory=list, description="정제된 3개 문장")

class EmbeddingOut(BaseModel):
    sentences: List[str] = Field(..., description="정제된 문장들")
    image: List[float] = Field(..., description="이미지 임베딩 (512차원)")
    text: List[float] = Field(..., description="텍스트 임베딩 (512차원)")
