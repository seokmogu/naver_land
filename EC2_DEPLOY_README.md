# EC2 배포 가이드

## 1. 배포 전 준비사항

### EC2 인스턴스 요구사항
- **OS**: Ubuntu 20.04 LTS 이상
- **인스턴스 타입**: t3.medium 이상 권장 (Playwright 브라우저 실행 위해)
- **보안그룹**: SSH(22) 포트 열기
- **스토리지**: 최소 20GB

### 로컬 환경 설정
1. `deploy_to_ec2.sh` 파일 상단에 EC2 정보 입력:
```bash
EC2_HOST="your-ec2-public-ip"
EC2_KEY_PATH="/path/to/your/key.pem"
```

## 2. 배포 실행

```bash
# 배포 스크립트 실행
./deploy_to_ec2.sh
```

배포 스크립트가 자동으로 다음을 수행합니다:
- EC2 연결 테스트
- 프로젝트 파일 압축 및 전송
- Python 환경 설정
- 의존성 설치
- Playwright 브라우저 설치

## 3. 수집기 실행

### EC2 접속
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
cd ~/naver_land
```

### 수집 실행 방법

#### 3.1 테스트 수집
```bash
./run_collection.sh test
```

#### 3.2 강남구 전체 수집
```bash
./run_collection.sh gangnam
```

#### 3.3 특정 지역 수집
```bash
./run_collection.sh area 1168010700 20  # 논현동 20개 매물
```

#### 3.4 특정 매물 수집
```bash
./run_collection.sh article 2390390123
```

## 4. 환경변수 설정

EC2에 처음 배포 후 `.env` 파일 생성:
```bash
cd ~/naver_land
cat > .env << 'EOF'
# 카카오 API
KAKAO_REST_API_KEY=640ac7eb1709ff36aa818f09e8dfbe7d

# Supabase 연결 정보
SUPABASE_URL=https://eslhavjipwbyvbbknixv.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE
SUPABASE_PASSWORD=SFHjy2PqCcMaMjVe

# PostgreSQL 직접 연결 (DDL 실행용)
DATABASE_URL=postgresql://postgres:SFHjy2PqCcMaMjVe@db.eslhavjipwbyvbbknixv.supabase.co:5432/postgres
EOF
```

## 5. 모니터링

### 실행 로그 확인
```bash
# 실시간 로그 확인
tail -f ~/naver_land/logs/collection.log

# 최근 에러 확인
grep "ERROR" ~/naver_land/logs/collection.log | tail -10
```

### 시스템 리소스 확인
```bash
# CPU/메모리 사용량
htop

# 디스크 사용량
df -h

# 프로세스 확인
ps aux | grep python
```

## 6. 문제해결

### 일반적인 문제들

1. **Playwright 브라우저 에러**
   ```bash
   cd ~/naver_land
   source venv/bin/activate
   playwright install chromium
   playwright install-deps
   ```

2. **메모리 부족**
   - EC2 인스턴스 타입을 더 큰 것으로 변경
   - 스왑 파일 생성으로 임시 해결

3. **권한 문제**
   ```bash
   chmod +x run_collection.sh
   chmod +x main.py
   ```

## 7. 자동화 (선택사항)

### Cron으로 주기적 실행
```bash
# crontab 편집
crontab -e

# 매일 오전 9시에 강남구 수집 실행
0 9 * * * cd ~/naver_land && ./run_collection.sh gangnam >> logs/cron.log 2>&1
```