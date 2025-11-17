import asyncio
from typing import Dict, Any, List
from fastapi import UploadFile, HTTPException
from PIL import Image
import io
import logging

from .models import predictor
from .models.classifier import _STATE as classifier_state

logger = logging.getLogger(__name__)


class DogBreedService:
    """강아지 품종 분석 서비스
    
    AI/dogbreed 모델을 사용하여 강아지 이미지의 품종을 분석합니다.
    """
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self) -> None:
        """모델 초기화
        
        predictor 모델을 초기화하고 warmup을 수행합니다.
        
        Raises:
            HTTPException: 모델 초기화 실패 시
        """
        if self.initialized:
            return
        
        try:
            logger.info("모델 초기화 시작...")
            predictor.init(warmup=True)
            self.initialized = True
            logger.info("모델 초기화 완료")
        except Exception as e:
            logger.error(f"모델 초기화 실패: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"모델 초기화 실패: {str(e)}"
            )
    
    async def get_dogbreed_result(self, image_file: UploadFile) -> str:
        """강아지 품종 분석
        
        이미지 파일을 받아 강아지 품종을 분석하고 한글 품종명을 반환합니다.
        
        Args:
            image_file: 업로드된 이미지 파일
            
        Returns:
            강아지 품종명 (한국어) 또는 "믹스"
            
        Raises:
            HTTPException: 
                - 400: 이미지 로드 실패, 강아지 미감지
                - 500: 모델 초기화 실패, 모델 실행 오류
        """
        # 모델 초기화 확인
        if not self.initialized:
            await self.initialize()
        
        # 이미지 로드
        try:
            image_bytes = await image_file.read()
            image = Image.open(io.BytesIO(image_bytes))
            image.load()  # 이미지 데이터 완전 로드
        except Exception as e:
            logger.error(f"이미지 로드 실패: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail=f"이미지 파일을 읽을 수 없습니다: {str(e)}"
            )
        
        # 모델 추론 (동기 함수를 비동기 스레드에서 실행)
        try:
            breed_text = await asyncio.to_thread(self._predict_breed, image)
            return breed_text
        except ValueError as e:
            logger.warning(f"품종 분석 실패: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except RuntimeError as e:
            logger.error(f"모델 런타임 오류: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"모델 실행 중 오류가 발생했습니다: {str(e)}"
            )
        except Exception as e:
            logger.error(f"품종 분석 중 예상치 못한 오류: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"품종 분석 중 오류가 발생했습니다: {str(e)}"
            )
    
    def _predict_breed(self, image: Image.Image) -> str:
        """모델을 사용하여 품종 예측
        
        Args:
            image: PIL Image 객체
            
        Returns:
            강아지 품종명 (한국어) 또는 "믹스"
            
        Raises:
            ValueError: 강아지 미감지 시
            RuntimeError: 모델 실행 오류 시
        """
        result = predictor.predict(image, return_topk=1)
        
        # 강아지 미감지 시 예외 발생
        if not result["boxes"]["detected"]:
            raise ValueError(
                "이미지에서 강아지를 감지할 수 없습니다. "
                "강아지가 포함된 이미지를 업로드해주세요."
            )
        
        # 품종 결정값 반환 (믹스 판정 시 "믹스" 문자열 반환)
        breed_decision = result["prediction"]["decision"]
        
        # 믹스 판정인 경우 로깅
        if result["prediction"]["decision_type"] == "mixed":
            mix_info = result["prediction"]["reasons"]["mix_rules"]
            logger.info(
                f"믹스 판정: H_norm={mix_info['H_norm']:.3f}, "
                f"p1={mix_info['p1']:.3f}, margin={mix_info['margin']:.3f}"
            )
        
        return breed_decision
    
    def get_breed_mappings(self) -> List[Dict[str, str]]:
        """견종 매핑 목록 조회
        
        현재 로드된 영어-한글 견종 매핑 목록을 반환합니다.
        
        Returns:
            [{"en": "Chihuahua", "ko": "치와와"}, ...] 형태의 리스트
            
        Raises:
            Exception: 모델이 초기화되지 않았거나 조회 실패 시
        """
        if not classifier_state.get("ready"):
            raise Exception("모델이 초기화되지 않았습니다. 먼저 모델을 초기화해주세요.")
        
        try:
            ko_map = classifier_state.get("ko_map", {})
            labels = classifier_state.get("labels", [])
            
            mappings = [
                {"en": en_breed, "ko": ko_map.get(en_breed, en_breed)}
                for en_breed in labels
            ]
            
            return mappings
        except Exception as e:
            logger.error(f"견종 매핑 목록 조회 실패: {str(e)}", exc_info=True)
            raise Exception(f"매핑 목록 조회 실패: {str(e)}")
    
    def update_breed_mapping(self, en: str, ko: str) -> bool:
        """견종 매핑 업데이트
        
        영어-한글 견종 매핑을 동적으로 업데이트합니다.
        
        Args:
            en: 영어 견종명
            ko: 한글 견종명
            
        Returns:
            업데이트 성공 여부 (존재하지 않는 영어 견종명인 경우 False)
            
        Raises:
            Exception: 모델이 초기화되지 않았거나 업데이트 실패 시
        """
        if not classifier_state.get("ready"):
            raise Exception("모델이 초기화되지 않았습니다. 먼저 모델을 초기화해주세요.")
        
        try:
            ko_map = classifier_state.get("ko_map", {})
            
            if en not in ko_map:
                logger.warning(f"존재하지 않는 영어 견종명: {en}")
                return False
            
            old_ko = ko_map[en]
            ko_map[en] = ko.strip()
            logger.info(f"견종 매핑 업데이트: {en} ({old_ko} -> {ko.strip()})")
            return True
            
        except Exception as e:
            logger.error(f"견종 매핑 업데이트 실패: {str(e)}", exc_info=True)
            raise Exception(f"매핑 업데이트 실패: {str(e)}")

# 싱글톤 인스턴스
dogbreed_service = DogBreedService()
