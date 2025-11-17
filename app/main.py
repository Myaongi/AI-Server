from fastapi import FastAPI
import logging

from app.domain.dogbreed import router as dogbreed_router
from app.domain.embed import router as embed_router
from app.domain.similarity import router as similarity_router
from app.domain.imagegen import router as imagegen_router
from app.domain.embed.llm_opt import initialize_normalizer_service

logger = logging.getLogger(__name__)

app = FastAPI(
    title="강아지킴이 AI",
    description="강아지 관련 AI 기능을 제공하는 통합 API 서버입니다. 강아지 품종 분류, 임베딩 생성, 유사도 계산 등의 기능을 제공합니다.",
    version="1.0.1",
    contact={
        "name": "강아지키미 팀",
        "email": "contact@gangajikimi.com"
    }
)

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 초기화 작업"""
    try:
        logger.info("서버 초기화 시작...")
        
        # Vertex AI 초기화 (Gemini REST Client)
        initialize_normalizer_service()
        
        logger.info("서버 초기화 완료")
    except Exception as e:
        logger.error(f"서버 초기화 실패: {str(e)}", exc_info=True)
        # 초기화 실패해도 서버는 시작하되, 해당 기능만 사용 불가
        logger.warning("Vertex AI 초기화 실패 - 텍스트 정제 기능이 제한될 수 있습니다.")

app.include_router(
    dogbreed_router.router,
    prefix = "/api/v1"
)

app.include_router(
    embed_router.router,
    prefix = "/api/v1"
)

app.include_router(
    similarity_router.router,
    prefix = "/api/v1"
)

app.include_router(
    imagegen_router.router,
    prefix = "/api/v1"
)