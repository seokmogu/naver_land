# EC2 동일 환경 로컬 테스트 가이드

## 개요
AWS EC2에 배포하기 전에 로컬에서 동일한 환경으로 테스트할 수 있는 Docker 기반 테스트 환경입니다.

## 🎯 테스트 목적

### 1. 배포 전 검증
- EC2 배포 전 코드 동작 확인
- 메모리/CPU 제약 환경에서의 성능 테스트
- 의존성 및 패키지 설치 확인

### 2. 인스턴스 타입 선택 지원
- t2.micro (1GB) vs t3.small (2GB) 성능 비교
- 무료 티어 환경에서의 수집 성능 확인
- 메모리 사용량 최적화 검증

## 🐳 Docker 환경 구성

### 파일 구조
```
├── Dockerfile.ec2-test          # EC2 Ubuntu 22.04 환경 재현
├── docker-compose.ec2-test.yml  # 다양한 테스트 환경 정의
├── test_local_ec2.sh           # 통합 테스트 스크립트
└── deploy_scripts/
    └── docker_test_setup.sh    # 컨테이너 내 설정 스크립트
```

### 테스트 환경별 컨테이너

| 컨테이너 | 메모리 | CPU | 용도 |
|----------|--------|-----|------|
| ec2-test | 1GB | 1 vCPU | t2.micro 시뮬레이션 |
| t3-small-test | 2GB | 2 vCPU | t3.small 시뮬레이션 |
| performance-test | 제한없음 | 제한없음 | 성능 기준선 |

## 🚀 사용 방법

### 방법 1: 통합 테스트 스크립트 (권장)

```bash
# 스크립트 실행 권한 부여
chmod +x test_local_ec2.sh

# 통합 테스트 실행
./test_local_ec2.sh
```

**테스트 옵션:**
1. **대화형 모드** - 수동으로 다양한 명령어 테스트
2. **자동 Import 테스트** - 모듈 로딩 확인
3. **자동 수집 테스트** - 실제 데이터 수집 (1개 워커)
4. **메모리/성능 테스트** - 리소스 사용량 확인

### 방법 2: Docker Compose 사용

```bash
# t2.micro 환경 테스트
docker-compose -f docker-compose.ec2-test.yml run --rm ec2-test

# t3.small 환경 테스트  
docker-compose -f docker-compose.ec2-test.yml run --rm t3-small-test

# 성능 제한 없는 환경
docker-compose -f docker-compose.ec2-test.yml run --rm performance-test
```

### 방법 3: 직접 Docker 실행

```bash
# 이미지 빌드
docker build -f Dockerfile.ec2-test -t naver-collector-ec2-test .

# 대화형 모드로 실행
docker run -it --rm \
  -v "$(pwd)/collectors/cached_token.json:/home/ubuntu/naver_land/collectors/cached_token.json" \
  -v "$(pwd)/collectors/results:/home/ubuntu/naver_land/collectors/results" \
  --memory=1g \
  naver-collector-ec2-test
```

## 🧪 테스트 시나리오

### 1. 환경 설정 확인
```bash
# 컨테이너 내에서 실행
source venv/bin/activate
python3 --version
pip list | grep -E "(requests|supabase)"
```

### 2. Import 테스트
```bash
python3 -c "
from collectors.fixed_naver_collector import FixedNaverCollector
from collectors.supabase_client import SupabaseHelper
print('✅ 모든 모듈 import 성공')
"
```

### 3. 토큰 설정 (최초 1회)
```bash
python3 collectors/setup_deployment.py
```

### 4. 간단한 수집 테스트
```bash
cd collectors
python3 cached_token_collector.py
```

### 5. 배치 수집 테스트
```bash
cd collectors
python3 parallel_batch_collect_gangnam.py --max-workers 1
```

### 6. 메모리 사용량 확인
```bash
python3 -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'메모리 사용량: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## 📊 성능 기대치

### t2.micro (1GB RAM) 환경
- **메모리 사용량**: 200-400MB
- **수집 성능**: 시간당 500-800개 매물
- **권장 설정**: 단일 워커, 작은 배치

### t3.small (2GB RAM) 환경  
- **메모리 사용량**: 300-600MB
- **수집 성능**: 시간당 1000-2000개 매물
- **권장 설정**: 2-3 워커, 중간 배치

## 🔧 문제 해결

### 메모리 부족 오류
```bash
# 메모리 사용량 확인
free -m
cat /proc/meminfo | grep -E "MemTotal|MemAvailable"

# 해결방법: 워커 수 줄이기
python3 parallel_batch_collect_gangnam.py --max-workers 1
```

### 토큰 관련 오류
```bash
# 토큰 캐시 확인
ls -la collectors/cached_token.json

# 토큰 재설정
python3 collectors/setup_deployment.py
```

### 네트워크 연결 오류
```bash
# DNS 확인
nslookup new.land.naver.com

# Supabase 연결 확인
python3 -c "from collectors.supabase_client import SupabaseHelper; SupabaseHelper()"
```

### 패키지 설치 오류
```bash
# 패키지 재설치
pip install --upgrade pip
pip install -r requirements.txt
```

## 📈 성능 비교 방법

### 1. 메모리 사용량 비교
```bash
# 각 환경에서 실행
docker stats naver-collector-ec2-test
```

### 2. 수집 속도 비교
```bash
# 동일한 지역(역삼동)에서 수집 시간 측정
time python3 collectors/cached_token_collector.py
```

### 3. 안정성 테스트
```bash
# 장시간 실행 테스트
python3 collectors/parallel_batch_collect_gangnam.py --max-workers 1
```

## ✅ 테스트 체크리스트

### 배포 전 확인사항
- [ ] 모든 모듈 import 성공
- [ ] 토큰 인증 성공
- [ ] Supabase 연결 성공
- [ ] 카카오 API 연결 성공 (선택)
- [ ] 메모리 사용량 적정 범위
- [ ] 수집 기능 정상 동작
- [ ] 에러 처리 정상 동작

### 성능 검증
- [ ] t2.micro 환경에서 안정적 동작
- [ ] 메모리 사용량 800MB 이하
- [ ] CPU 사용률 적정 범위
- [ ] 수집 속도 만족스러운 수준

## 🎉 테스트 완료 후

로컬 테스트가 성공하면 실제 EC2 배포를 진행하세요:

```bash
# EC2 자동 배포
./deploy_scripts/aws_auto_deploy.sh

# EC2에서 동일한 테스트
./deploy_scripts/remote_ec2_commands.sh test
```

이 가이드를 통해 EC2 배포 전에 안전하게 테스트하고 최적의 인스턴스 타입을 선택할 수 있습니다.