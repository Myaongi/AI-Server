from pydantic import BaseModel, Field
from typing import List

class PairScoreIn(BaseModel):
    emb_a_image: List[float] = Field(..., description="게시물 A의 이미지 임베딩")
    emb_a_text: List[float] = Field(..., description="게시물 A의 텍스트 임베딩")
    emb_b_image: List[float] = Field(..., description="게시물 B의 이미지 임베딩")
    emb_b_text: List[float] = Field(..., description="게시물 B의 텍스트 임베딩")

class PairScoreOut(BaseModel):
    score: float = Field(..., description="최종 가중 평균 유사도 (0.0 ~ 1.0)")
