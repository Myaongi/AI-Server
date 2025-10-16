# Gangajikimi FastAPI Server

강아지 관련 AI 기능을 제공하는 통합 FastAPI 서버입니다. 강아지 품종 분류, 임베딩 생성, 유사도 계산 등의 기능을 제공합니다.

## 🚀 주요 기능

- **🐕 강아지 품종 분류**: YOLO + EfficientNet을 사용한 120개 품종 분류
- **🔍 임베딩 생성**: CLIP + YOLO를 사용한 이미지/텍스트 임베딩 생성
- **📊 유사도 계산**: 두 임베딩 간의 유사도 계산 (유실견/발견견 매칭용)
- **🌏 한글 지원**: 한국어 견종명 매핑

## 📁 프로젝트 구조

```
Gangajikimi-FastAPI-Server/
├── app/
│   ├── main.py                     # FastAPI 앱 진입점
│   ├── domain/                     # 도메인별 기능 모듈
│   │   ├── config.py              # 공통 설정 (LLM, YOLO, CLIP 등)
│   │   ├── dogbreed/              # 강아지 품종 분류 도메인
│   │   │   ├── router.py          # API 라우터
│   │   │   ├── schema.py          # Pydantic 모델들
│   │   │   ├── service.py         # 비즈니스 로직
│   │   │   ├── assets/            # AI 모델 가중치
│   │   │   └── models/            # AI 모델 코드들
│   │   ├── embed/                 # 임베딩 생성 도메인
│   │   │   ├── router.py          # API 라우터
│   │   │   ├── schema.py          # Pydantic 모델들
│   │   │   ├── pipeline_embed.py  # 메인 임베딩 파이프라인
│   │   │   ├── llm_client.py      # LLM 텍스트 정제
│   │   │   ├── yolo_crop.py       # YOLO 이미지 크롭
│   │   │   └── clipper.py         # CLIP 임베딩
│   │   └── similarity/            # 유사도 계산 도메인
│   │       ├── router.py          # API 라우터
│   │       ├── schema.py          # Pydantic 모델들
│   │       ├── pipeline_similarity.py # 메인 유사도 파이프라인
│   │       └── similarity.py      # 유사도 계산 함수들
│   └── response/                  # 응답 유틸리티
├── requirements/                  # 의존성 관리
│   ├── requirements-base.txt      # 기본 패키지
│   ├── requirements-cpu.txt       # CPU 버전 PyTorch
│   └── requirements-gpu-cu128.txt # GPU 버전 PyTorch
├── Dockerfile                     # Docker 컨테이너 설정
└── yolov8s.pt                     # YOLO 모델 가중치
```

## 🛠️ 설치 및 실행

### 1. 시스템 요구사항

- Python 3.8 이상
- 최소 4GB RAM (모델 로딩용)
- 디스크 공간 2GB 이상

### 2. 가상환경 생성 및 활성화

```bash
# 프로젝트 디렉토리로 이동
cd Gangajikimi-FastAPI-Server

# 가상환경 생성
python -m venv fastapi_env

# 가상환경 활성화
source fastapi_env/bin/activate  # Linux/Mac
# 또는
fastapi_env\Scripts\activate     # Windows
```

### 3. 패키지 설치

```bash
# 기본 패키지 설치
pip install -r requirements/requirements-base.txt

# PyTorch 설치 (CPU 버전)
pip install -r requirements/requirements-cpu.txt

# 또는 GPU 버전 (CUDA 12.8)
pip install -r requirements/requirements-gpu-cu128.txt
```

### 4. 설정 파일 생성

**로컬 개발 환경:**

```bash
# config.py.example을 복사하여 config.py 생성
cp app/domain/config.py.example app/domain/config.py

# config.py를 열어서 GEMINI_API_KEY 수정
# GEMINI_API_KEY = "YOUR_ACTUAL_API_KEY_HERE"
```

**Gemini API 키 발급 방법:**
1. [Google AI Studio](https://makersuite.google.com/app/apikey)에 접속
2. "Create API Key" 클릭하여 API 키 생성
3. `app/domain/config.py` 파일에서 `GEMINI_API_KEY` 값을 수정

**주의사항:**
- ⚠️ `config.py`는 `.gitignore`에 포함되어 있어 GitHub에 업로드되지 않습니다
- 운영/배포 환경에서는 GitHub Actions가 환경변수로 자동 생성합니다
- 환경변수로도 설정 가능: `export GEMINI_API_KEY="your_key"`

### 5. 서버 실행

```bash
# 개발 모드 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션 모드 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. API 문서 확인

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📚 API 사용 가이드

### 🐕 DogBreed 도메인 (`/api/v1/dogbreed`)

#### 강아지 품종 분류

**엔드포인트**: `POST /api/v1/dogbreed/`

**요청**:
- **Content-Type**: `multipart/form-data`
- **image**: 강아지 이미지 파일 (JPG, PNG 등)

**요청 예시**:
```bash
curl -X POST "http://localhost:8000/api/v1/dogbreed/" \
     -H "accept: application/json" \
     -F "image=@/path/to/dog_image.jpg"
```

**응답**:
```json
{
  "result": "골든 리트리버"
}
```

### 🔍 Embed 도메인 (`/api/v1/embed`)

#### 1. 텍스트 정제

**엔드포인트**: `POST /api/v1/embed/normalize`

**요청**:
```json
{
  "breed": "골든 리트리버",
  "colors": "골드, 흰색",
  "features": "큰 귀, 긴 털"
}
```

**응답**:
```json
{
  "sentences": [
    "골든 리트리버 견종입니다.",
    "골드와 흰색 색상의 강아지입니다.",
    "큰 귀와 긴 털이 특징입니다."
  ]
}
```

#### 2. 임베딩 생성

**엔드포인트**: `POST /api/v1/embed/embed`

**요청**:
- **Content-Type**: `multipart/form-data`
- **image**: 강아지 이미지 파일
- **breed**: 품종 (선택사항)
- **colors**: 색상 (선택사항)
- **features**: 특징 (선택사항)

**요청 예시**:
```bash
curl -X POST "http://localhost:8000/api/v1/embed/embed" \
     -H "accept: application/json" \
     -F "image=@/path/to/dog_image.jpg" \
     -F "breed=골든 리트리버" \
     -F "colors=골드, 흰색" \
     -F "features=큰 귀, 긴 털"
```

**응답**:
```json
{
  "sentences": [
    "골든 리트리버 견종입니다.",
    "골드와 흰색 색상의 강아지입니다.",
    "큰 귀와 긴 털이 특징입니다."
  ],
  "image": [0.1, -0.2, 0.3, ...],  // 512차원 이미지 임베딩
  "text": [0.2, -0.1, 0.4, ...]    // 512차원 텍스트 임베딩
}
```

### 📊 Similarity 도메인 (`/api/v1/similarity`)

#### 유사도 계산

**엔드포인트**: `POST /api/v1/similarity/score`

**요청**:
```json
{
  "emb_a_image": [0.1, -0.2, 0.3, ...],  // 게시물 A의 이미지 임베딩
  "emb_a_text": [0.2, -0.1, 0.4, ...],   // 게시물 A의 텍스트 임베딩
  "emb_b_image": [0.3, -0.3, 0.2, ...],  // 게시물 B의 이미지 임베딩
  "emb_b_text": [0.1, -0.2, 0.3, ...],   // 게시물 B의 텍스트 임베딩
  "weights": [0.2, 0.0, 0.0, 0.8]        // 가중치 (선택사항)
}
```

**응답**:
```json
{
  "s_ii": 0.85,      // 이미지-이미지 유사도
  "s_it": 0.72,      // 이미지-텍스트 유사도
  "s_ti": 0.68,      // 텍스트-이미지 유사도
  "s_tt": 0.91,      // 텍스트-텍스트 유사도
  "score": 0.88,     // 최종 가중 평균 유사도
  "threshold": 0.35, // 임계값
  "pass": true       // 임계값 기준 매칭 여부
}
```

## 🔧 설정

### 환경 변수

다음 환경 변수를 설정할 수 있습니다:

```bash
# Gemini API 설정 (LLM 텍스트 정제용)
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent
GEMINI_API_KEY=your_gemini_api_key_here  # Gemini API 키를 여기에 입력
GEMINI_TEMPERATURE=0.1
LLM_TIMEOUT=20
LLM_MAX_RETRIES=3

# YOLO 설정
YOLO_WEIGHTS=yolov8s.pt
YOLO_CONF=0.30
YOLO_MARGIN=0.18
YOLO_IMGSZ=512
DOG_CLASS_ID=16

# CLIP 설정
CLIP_MODEL=ViT-B-32
CLIP_PRETRAINED=laion2b_s34b_b79k
TEXT_POOLING=avg

# 유사도 가중치
W_II=0.20  # 이미지-이미지 가중치
W_IT=0.00  # 이미지-텍스트 가중치
W_TI=0.00  # 텍스트-이미지 가중치
W_TT=0.80  # 텍스트-텍스트 가중치

# 유사도 임계값
SIM_THRESHOLD=0.35
```

## 🐳 Docker 실행

### 기본 실행

```bash
# Docker 이미지 빌드
docker build -t gangajikimi-api .

# Docker 컨테이너 실행 (환경변수 포함)
docker run -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  gangajikimi-api

# 또는 백그라운드 실행
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  --name gangajikimi-server \
  gangajikimi-api
```

### 볼륨 마운트 (선택사항)

모델 캐시를 재사용하려면 볼륨을 마운트할 수 있습니다:

```bash
docker run -d -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key_here" \
  -v $(pwd)/.cache:/app/.cache \
  --name gangajikimi-server \
  gangajikimi-api
```

**참고:** 
- Hugging Face 모델은 `/app/.cache/huggingface`에 다운로드됩니다
- 비루트 사용자(`appuser`, UID 10001)로 실행되므로 권한 문제가 없습니다

## 📝 사용 예시

### 강아지 매칭 워크플로우

1. **유실견 게시물 처리**:
   ```bash
   # 유실견 이미지와 설명으로 임베딩 생성
   curl -X POST "http://localhost:8000/api/v1/embed/embed" \
        -F "image=@lost_dog.jpg" \
        -F "breed=골든 리트리버" \
        -F "colors=골드, 흰색" \
        -F "features=큰 귀, 긴 털"
   ```

2. **발견견 게시물 처리**:
   ```bash
   # 발견견 이미지와 설명으로 임베딩 생성
   curl -X POST "http://localhost:8000/api/v1/embed/embed" \
        -F "image=@found_dog.jpg" \
        -F "breed=골든 리트리버" \
        -F "colors=골드, 흰색" \
        -F "features=큰 귀, 긴 털"
   ```

3. **유사도 계산**:
   ```bash
   # 두 게시물 간의 유사도 계산
   curl -X POST "http://localhost:8000/api/v1/similarity/score" \
        -H "Content-Type: application/json" \
        -d '{
          "emb_a_image": [...],
          "emb_a_text": [...],
          "emb_b_image": [...],
          "emb_b_text": [...]
        }'
   ```

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여

버그 리포트나 기능 제안은 이슈를 통해 알려주세요.

---

**Gangajikimi AI** - 강아지와 함께하는 더 나은 세상을 만들어갑니다. 🐕✨