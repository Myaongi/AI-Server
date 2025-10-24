# GCP VM 배포 가이드

이 문서는 GitHub Actions를 통해 FastAPI 서버를 GCP VM에 자동 배포하는 방법을 설명합니다.

## 사전 준비사항

### 1. Docker Hub 계정 준비

1. [Docker Hub](https://hub.docker.com/)에서 계정 생성
2. Access Token 생성
   - Docker Hub → Account Settings → Security → New Access Token
   - 생성된 토큰을 안전하게 보관

### 2. GCP 프로젝트 설정

1. **GCP 프로젝트 생성**
   - [GCP Console](https://console.cloud.google.com/)에서 새 프로젝트 생성
   - 프로젝트 ID를 메모해둡니다

2. **필요한 API 활성화**
```bash
gcloud services enable compute.googleapis.com
```

### 3. GCP VM 인스턴스 생성

```bash
# Compute Engine VM 인스턴스 생성 (예시)
gcloud compute instances create gangajikimi-vm \
  --zone=asia-northeast3-a \
  --machine-type=e2-standard-4 \
  --boot-disk-size=50GB \
  --boot-disk-type=pd-standard \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    # Docker 설치
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io
    
    # gcloud 설정
    apt-get install -y google-cloud-sdk
    
    # Docker 그룹에 사용자 추가
    usermod -aG docker $USER
  '

# 방화벽 규칙 생성 (포트 8000 개방)
gcloud compute firewall-rules create allow-fastapi \
  --allow=tcp:8000 \
  --target-tags=http-server \
  --description="Allow FastAPI traffic on port 8000"
```

### 4. SSH 키 생성 및 설정

```bash
# SSH 키 생성 (로컬에서)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/gangajikimi-deploy -C "github-actions"

# 공개 키를 VM에 추가
gcloud compute ssh gangajikimi-vm --zone=asia-northeast3-a

# VM 내부에서 공개 키 추가
mkdir -p ~/.ssh
echo "여기에_공개키_내용_붙여넣기" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit

# Private 키 확인 (이 내용을 GitHub Secret에 추가)
cat ~/.ssh/gangajikimi-deploy
```

## GitHub Repository 설정

### GitHub Secrets 추가

Repository Settings → Secrets and variables → Actions에서 다음 secrets를 추가합니다:

1. **DOCKERHUB_USERNAME**
   - Docker Hub 사용자 이름

2. **DOCKERHUB_TOKEN**
   - Docker Hub Access Token

3. **SSH_PRIVATE_KEY**
   - SSH Private 키 파일의 전체 내용
   - `cat ~/.ssh/gangajikimi-deploy` 명령어로 확인한 내용

4. **VM_HOST**
   - VM의 외부 IP 주소
   - 예: `34.64.123.456`
   - `gcloud compute instances list`로 확인

5. **VM_USER**
   - VM 사용자 이름
   - 예: `ubuntu`, `user`, 또는 GCP 계정 이름

6. **GEMINI_API_KEY**
   - Google Gemini API 키

7. **CONFIG_PY**
   - `app/domain/config.py` 파일의 전체 내용
   - `app/domain/config.py.example`을 참고하여 작성

## 배포 워크플로우

### 자동 배포 트리거

- `develop` 브랜치에 push할 때 자동 배포
- GitHub Actions 탭에서 수동 실행 (`workflow_dispatch`)

### 배포 과정

1. **코드 체크아웃**
2. **config.py 생성** (GitHub Secret에서)
3. **Docker Hub 로그인**
4. **Docker 이미지 빌드**
5. **Docker Hub에 푸시**
6. **SSH 키 설정**
7. **VM에 SSH 접속하여 배포**
   - 기존 컨테이너 중지
   - 최신 이미지 pull (Docker Hub에서)
   - 새 컨테이너 실행

## 배포 후 확인

### VM 접속

```bash
gcloud compute ssh gangajikimi-vm --zone=asia-northeast3-a
```

### 컨테이너 상태 확인

```bash
# 실행 중인 컨테이너 확인
docker ps

# 로그 확인
docker logs gangajikimi-api

# 실시간 로그 스트리밍
docker logs -f gangajikimi-api
```

### API 엔드포인트 확인

```bash
# VM 외부 IP 가져오기
VM_IP=$(gcloud compute instances describe gangajikimi-vm \
  --zone=asia-northeast3-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# API 문서 접속
curl http://$VM_IP:8000/docs

# OpenAPI 스키마 확인
curl http://$VM_IP:8000/openapi.json
```

브라우저에서 접속:
- API 문서: `http://[VM_IP]:8000/docs`
- ReDoc: `http://[VM_IP]:8000/redoc`

## 문제 해결

### Docker 권한 오류

VM에서 Docker 권한 오류가 발생하면:

```bash
sudo usermod -aG docker $USER
sudo systemctl restart docker
```

### 컨테이너 재시작

```bash
docker restart gangajikimi-api
```

### 컨테이너 삭제 및 재배포

```bash
docker stop gangajikimi-api
docker rm gangajikimi-api
docker pull YOUR_DOCKERHUB_USERNAME/gangajikimi-fastapi:latest
docker run -d \
  --name gangajikimi-api \
  --restart unless-stopped \
  -p 8000:8000 \
  -e GEMINI_API_KEY=YOUR_KEY \
  -e UVICORN_WORKERS=4 \
  YOUR_DOCKERHUB_USERNAME/gangajikimi-fastapi:latest
```

## 보안 고려사항

1. **방화벽 설정**: 필요한 포트만 개방
2. **HTTPS 설정**: 프로덕션에서는 HTTPS 사용 권장 (Load Balancer 또는 Nginx 프록시)
3. **환경 변수 관리**: 민감한 정보는 Secret Manager 사용 권장
4. **정기적인 업데이트**: 보안 패치 및 의존성 업데이트

## 비용 최적화

- **VM 크기 조정**: 트래픽에 맞춰 적절한 머신 타입 선택
- **예약 VM**: 장기 사용 시 예약 VM으로 비용 절감
- **자동 종료**: 개발/테스트 환경은 사용하지 않을 때 자동 종료 설정

## 참고 자료

- [GCP Compute Engine 문서](https://cloud.google.com/compute/docs)
- [Docker Hub 문서](https://docs.docker.com/docker-hub/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)

