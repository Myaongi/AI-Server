from fastapi import APIRouter, HTTPException, Body
from . import schema
from .pipeline_similarity import score_pair
from ...domain import config
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["📊 유사도 계산"],
    prefix="/similarity"
)

@router.post("/score", 
             response_model=schema.PairScoreOut,
             summary="유사도 계산",
             description="두 강아지 임베딩 간의 유사도를 계산하여 매칭 가능성을 판단합니다.")
def score_endpoint(
    payload: schema.PairScoreIn = Body(..., description="두 강아지의 임베딩 데이터")
):
    """
    유사도 계산 API - 두 임베딩 간의 유사도 계산
    """
    try:
        logger.info("유사도 계산 요청")
        
        result = score_pair(
            payload.emb_a_image, payload.emb_a_text,
            payload.emb_b_image, payload.emb_b_text
        )
        
        logger.info(f"유사도 계산 완료: score={result['score']:.3f}")
        
        return schema.PairScoreOut(**result)
        
    except Exception as e:
        logger.error(f"유사도 계산 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"유사도 계산 실패: {str(e)}")
