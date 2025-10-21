from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import logging

from . import service, schema
from .service import dogbreed_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["🐕 강아지 품종 분류"],
    prefix="/dogbreed"
)

@router.post("/", 
             response_model=schema.DogBreedResult,
             summary="강아지 품종 분류",
             description="YOLO와 EfficientNet을 사용하여 강아지 이미지의 품종을 분류합니다.")
async def get_dogbreed_result(
    image: UploadFile = File(..., description="강아지 이미지 파일 (JPG, PNG 등)")
):
    """
    강아지 품종을 분류하여 텍스트로 반환하는 API
    
    - **image**: 강아지 이미지 파일 (JPG, PNG 등)
    - **반환**: 강아지 품종명 (한국어 텍스트)
    """
    try:
        logger.info(f"강아지 품종 분석 요청: {image.filename}")
        
        # 서비스의 get_dogbreed_result 함수 호출
        breed_text = await dogbreed_service.get_dogbreed_result(image)
        
        logger.info(f"강아지 품종 분석 완료: {breed_text}")
        
        # 단순 텍스트 반환
        return {"result": breed_text}
        
    except HTTPException as e:
        logger.error(f"HTTP 에러: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"예상치 못한 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")