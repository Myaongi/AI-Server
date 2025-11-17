from fastapi import APIRouter, HTTPException, Response, Body
from fastapi.responses import StreamingResponse
import logging
from io import BytesIO

from . import schema
from .dog_image_gen_service import DogImageGenerator

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["🎨 강아지 이미지 생성"],
    prefix="/imagegen"
)


@router.post(
    "",
    summary="강아지 이미지 생성",
    description="Gemini AI를 사용하여 강아지 정보를 바탕으로 이미지를 생성합니다.",
    response_class=Response
)
async def generate_dog_image(
    payload: schema.DogImageGenIn = Body(..., description="강아지 정보 (품종, 색상, 특징)")
):
    """
    강아지 이미지 생성 API
    
    - **breed**: 강아지 품종 (한국어)
    - **colors**: 강아지 색상 (한국어)
    - **features**: 강아지 특징 및 기타 정보 (한국어)
    - **반환**: PNG 형식의 이미지 파일 (4:3 비율, 1600px 너비)
    """
    try:
        logger.info(f"이미지 생성 요청: breed={payload.breed}, colors={payload.colors}, features={payload.features}")
        
        # 이미지 생성기 인스턴스 생성
        generator = DogImageGenerator()
        
        # 이미지 생성 (bytes 반환)
        image_bytes = generator.generate_from_raw_ko(
            breed=payload.breed,
            colors=payload.colors,
            others=payload.features  # features를 others 파라미터로 매핑
        )
        
        logger.info(f"이미지 생성 완료: {len(image_bytes)} bytes")
        
        # PNG 이미지를 Response로 반환
        return Response(
            content=image_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "inline; filename=generated_dog_image.png"
            }
        )
        
    except RuntimeError as e:
        logger.error(f"이미지 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"예상치 못한 에러: {str(e)}")
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {str(e)}")

