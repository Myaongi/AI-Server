from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from . import schema
from .llm_opt import normalize_to_3_sentences  # Vertex AI 버전 사용
from .pipeline_embed import build_embeddings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["🔍 임베딩 생성"],
    prefix="/embed"
)

@router.post("/normalize", 
             response_model=schema.TextNormalizeOut,
             summary="텍스트 정제",
             description="Gemini AI를 사용하여 강아지 정보를 3개의 문장으로 정제합니다.")
def normalize_endpoint(
    payload: schema.TextNormalizeIn = Body(..., description="강아지 정보 (품종, 색상, 특징)")
):
    """
    텍스트 정제 API - 품종/색상/특징을 3개 문장으로 변환
    """
    try:
        logger.info(f"텍스트 정제 요청: breed={payload.breed}, colors={payload.colors}, features={payload.features}")
        
        sentences = normalize_to_3_sentences(payload.breed, payload.colors, payload.features)
        
        logger.info(f"텍스트 정제 완료: {len(sentences)}개 문장")
        
        return schema.TextNormalizeOut(sentences=sentences)
        
    except Exception as e:
        logger.error(f"텍스트 정제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"텍스트 정제 실패: {str(e)}")

@router.post("", 
             response_model=schema.EmbeddingOut,
             summary="임베딩 생성",
             description="CLIP과 YOLO를 사용하여 강아지 이미지와 텍스트를 임베딩으로 변환합니다.")
async def embed_endpoint(
    image: UploadFile = File(..., description="강아지 이미지 파일"),
    breed: str = Form("", description="강아지 품종"),
    colors: str = Form("", description="강아지 색상"),
    features: str = Form("", description="강아지 특징")
):
    """
    임베딩 생성 API - 이미지와 텍스트를 임베딩으로 변환
    """
    try:
        logger.info(f"임베딩 생성 요청: {image.filename}, breed={breed}")
        
        # 이미지 읽기
        image_bytes = await image.read()
        
        # 임베딩 생성
        result = build_embeddings(image_bytes, breed, colors, features)
        
        logger.info(f"임베딩 생성 완료: 이미지={len(result['image_embedding'])}, 텍스트={len(result['text_embedding'])}")
        
        return schema.EmbeddingOut(
            sentences=result["sentences"], 
            image=result["image_embedding"].tolist(), 
            text=result["text_embedding"].tolist()
        )
        
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"임베딩 생성 실패: {str(e)}")
