# app/pipeline_similarity.py
from typing import Tuple, Optional, Dict
import numpy as np

from .similarity import four_sims, weighted_score  # (I-I, I-T, T-I, T-T) + 가중합
from ...domain import config

def score_pair(
    emb_img_a: np.ndarray, emb_txt_a: np.ndarray,
    emb_img_b: np.ndarray, emb_txt_b: np.ndarray
) -> Dict[str, float]:
    """
    [파이프라인 #2] 게시물 A vs B (1:1)
      - 4유형(I-I, I-T, T-I, T-T) 코사인 유사도 계산
      - 가중합으로 최종 score 계산 (config.W_II, W_IT, W_TI, W_TT 사용)
    반환:
      {
        "score": float  # 최종 가중 평균 유사도 (0.0 ~ 1.0)
      }
    """
    s_ii, s_it, s_ti, s_tt = four_sims(emb_img_a, emb_txt_a, emb_img_b, emb_txt_b)
    score = weighted_score((s_ii, s_it, s_ti, s_tt), weights=None)  # None이면 config 값 사용
    return {
        "score": float(score)
    }

__all__ = ["score_pair"]
