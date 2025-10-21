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
    """강아지 품종 분석 서비스 - models 함수들만 활용"""
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self):
        """models/predictor.py의 init 함수 호출"""
        if not self.initialized:
            try:
                logger.info("모델 초기화 시작...")
                # models/predictor.py의 init 함수 호출
                predictor.init(warmup=True)
                self.initialized = True
                logger.info("모델 초기화 완료")
            except Exception as e:
                logger.error(f"모델 초기화 실패: {str(e)}")
                raise HTTPException(status_code=500, detail=f"모델 초기화 실패: {str(e)}")
    
    async def get_dogbreed_result(self, image_file: UploadFile) -> str:
        """
        models/predictor.py의 predict 함수만 호출하는 간단한 버전
        
        Args:
            image_file (UploadFile): 이미지 파일
            
        Returns:
            str: 강아지 품종명 (한국어)
        """
        try:
            # 모델 초기화 확인
            if not self.initialized:
                await self.initialize()
            
            # 이미지 로드
            image_bytes = await image_file.read()
            image = Image.open(io.BytesIO(image_bytes))
            
            # models/predictor.py의 predict 함수 호출
            breed_text = await asyncio.to_thread(self._call_predict_model, image)
            
            return breed_text
            
        except Exception as e:
            logger.error(f"품종 분석 실패: {str(e)}")
            # 분석 실패시 '믹스' 반환
            return {"result": "믹스"}
    
    def _call_predict_model(self, image: Image.Image) -> str:
        """
        models/predictor.py의 predict 함수 호출
        
        Args:
            image (PIL.Image): 이미지
            
        Returns:
            str: 강아지 품종명 (한국어) - 실패시 '믹스' 반환
        """
        try:
            # models/predictor.py의 predict 함수 호출
            result = predictor.predict(image, return_topk=1)
            
            # 결과에서 품종명 추출
            breed_decision = result["prediction"]["decision"]
            dog_detected = result["boxes"]["detected"]
            
            # 강아지 미감지시 '믹스' 반환
            if not dog_detected:
                return "믹스"
            
            return breed_decision
            
        except Exception as e:
            logger.error(f"predictor.predict 함수 호출 실패: {str(e)}")
            # 예외 발생시 '믹스' 반환
            return "믹스"
    
    def get_breed_mappings(self) -> List[Dict[str, str]]:
        """
        현재 견종 매핑 목록을 반환
        
        Returns:
            List[Dict[str, str]]: [{"en": "Chihuahua", "ko": "치와와"}, ...]
        """
        try:
            if not classifier_state.get("ready"):
                raise Exception("모델이 초기화되지 않았습니다")
            
            ko_map = classifier_state.get("ko_map", {})
            labels = classifier_state.get("labels", [])
            
            mappings = []
            for en_breed in labels:
                ko_breed = ko_map.get(en_breed, en_breed)
                mappings.append({"en": en_breed, "ko": ko_breed})
            
            return mappings
            
        except Exception as e:
            logger.error(f"견종 매핑 목록 조회 실패: {str(e)}")
            raise Exception(f"매핑 목록 조회 실패: {str(e)}")
    
    def update_breed_mapping(self, en: str, ko: str) -> bool:
        """
        견종 매핑을 동적으로 업데이트
        
        Args:
            en (str): 영어 견종명
            ko (str): 한글 견종명
            
        Returns:
            bool: 성공 여부
        """
        try:
            if not classifier_state.get("ready"):
                raise Exception("모델이 초기화되지 않았습니다")
            
            # ko_map 업데이트
            ko_map = classifier_state.get("ko_map", {})
            if en in ko_map:
                old_ko = ko_map[en]
                ko_map[en] = ko.strip()
                logger.info(f"견종 매핑 업데이트: {en} ({old_ko} -> {ko.strip()})")
                return True
            else:
                logger.warning(f"존재하지 않는 영어 견종명: {en}")
                return False
                
        except Exception as e:
            logger.error(f"견종 매핑 업데이트 실패: {str(e)}")
            raise Exception(f"매핑 업데이트 실패: {str(e)}")

# 싱글톤 인스턴스
dogbreed_service = DogBreedService()
