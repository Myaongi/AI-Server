from fastapi import FastAPI

from app.domain.dogbreed import router as dogbreed_router
from app.domain.embed import router as embed_router
from app.domain.similarity import router as similarity_router

app = FastAPI(
    title="강아지킴이 AI",
    description="강아지 관련 AI 기능을 제공하는 통합 API 서버입니다. 강아지 품종 분류, 임베딩 생성, 유사도 계산 등의 기능을 제공합니다.",
    version="1.0.0",
    contact={
        "name": "강아지키미 팀",
        "email": "contact@gangajikimi.com"
    }
)

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
