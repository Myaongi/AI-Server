# Gangajikimi FastAPI 서버용 멀티 스테이지, CPU 전용, 최소 런타임 이미지
# 1단계: 휠 파일들을 미리 다운로드해서 최종 이미지에 빌드 도구 없이 최소 레이어로 구성
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim AS wheels

# Python 환경 변수 설정 (캐시 비활성화, 바이트코드 생성 안함, 버퍼링 없음)
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /w

# 캐시 히트를 최대화하기 위해 requirements 파일만 복사
COPY requirements/requirements-base.txt requirements/requirements-base.txt
COPY requirements/requirements-cpu.txt requirements/requirements-cpu.txt

# PyTorch 등 모든 의존성의 휠 파일을 미리 다운로드 (CPU 버전)
RUN python -m pip install --upgrade pip && \
    pip wheel --wheel-dir /wheels \
      -r requirements/requirements-base.txt \
      -r requirements/requirements-cpu.txt

# 2단계: 실제 런타임 이미지 (최종 배포용)
FROM python:3.13-slim AS runtime

# Python 환경 변수 설정
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UVICORN_WORKERS=2 \
    HOST=0.0.0.0 \
    PORT=8000 \
    # Gemini API 설정 (배포 시 환경변수로 덮어쓰기)
    GEMINI_API_KEY="" \
    GEMINI_API_URL="https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
    # 모델 설정
    YOLO_WEIGHTS="yolov8s.pt" \
    CLIP_MODEL="ViT-B-32" \
    CLIP_PRETRAINED="laion2b_s34b_b79k" \
    # Hugging Face 캐시 경로 설정 (권한 문제 방지)
    HF_HOME="/app/.cache/huggingface" \
    TRANSFORMERS_CACHE="/app/.cache/huggingface" \
    HF_DATASETS_CACHE="/app/.cache/huggingface"

WORKDIR /app

# opencv-python-headless, numpy, torch에 필요한 최소 시스템 라이브러리만 설치
# 불필요한 개발 도구 및 GUI 라이브러리 제거로 이미지 크기 최소화
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      libglib2.0-0 \
      libgl1 \
      libsm6 \
      libxext6 \
      libxrender1 \
      libgomp1 \
      libgfortran5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# 1단계에서 다운로드한 휠 파일들을 복사해서 설치 후 삭제 (단일 레이어로 최적화)
COPY --from=wheels /wheels /tmp/wheels
RUN python -m pip install --no-index --find-links=/tmp/wheels /tmp/wheels/* && \
    rm -rf /tmp/wheels && \
    # PyTorch 관련 불필요한 패키지 제거
    find /usr/local/lib/python*/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python*/site-packages -name "__pycache__" -type d -exec rm -rf {} + || true

# 필요한 프로젝트 파일들만 복사
COPY app/ /app/app/
COPY yolov8s.pt /app/yolov8s.pt

# Hugging Face 캐시 디렉토리 생성
RUN mkdir -p /app/.cache/huggingface

# ⭐ CLIP 모델 사전 다운로드 (빌드 시 한 번만)
RUN python -c "import open_clip; open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')" && \
    echo "CLIP model downloaded and cached"

# 보안을 위해 비루트 사용자 생성 및 권한 설정
RUN useradd -m -u 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 포트 8000 노출
EXPOSE 8000

# 헬스체크: 3분마다 /openapi.json에 접근해서 서버 상태 확인
HEALTHCHECK --interval=180s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/openapi.json', timeout=3)"

# 프로덕션용 기본 명령어 (reload 비활성화). 필요시 CMD/args로 변경 가능
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


