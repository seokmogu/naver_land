# GCP Compute Engine 배포 가이드

## 🚀 배포 단계별 실행

### 1. GCP Console에서 VM 생성
- **머신 유형**: e2-micro (무료 티어)
- **지역**: us-west1, us-central1, us-east1 중 선택
- **OS**: Ubuntu 22.04 LTS
- **디스크**: 30GB (무료)

### 2. 로컬에서 GitHub에 업로드
```bash
# 현재 디렉토리에서 실행
git add .
git commit -m "Add GCP deployment scripts"
git push origin main
```

### 3. VM에 SSH 접속 후 실행
```bash
# 1. 시스템 환경 설정
wget https://raw.githubusercontent.com/your-username/naver_land/main/deploy_scripts/gcp_setup.sh
chmod +x gcp_setup.sh
./gcp_setup.sh

# 2. 프로젝트 클론
git clone https://github.com/your-username/naver_land.git
cd naver_land

# 3. 프로젝트 환경 설정
./deploy_scripts/setup_project.sh

# 4. API 키 설정
cd collectors
python3 setup_deployment.py

# 5. 자동 스케줄링 설정
cd ..
./deploy_scripts/setup_cron.sh

# 6. 수동 테스트 (선택사항)
cd collectors
source ../venv/bin/activate
python3 parallel_batch_collect_gangnam.py --max-workers 2
```

## 📊 모니터링 및 관리

### 로그 확인
```bash
# 최신 로그 확인
tail -f ~/naver_land/logs/daily_collection_*.log

# 모든 로그 목록
ls -la ~/naver_land/logs/
```

### Cron 작업 관리
```bash
# 현재 스케줄 확인
crontab -l

# 수동 실행 테스트
~/naver_land/deploy_scripts/daily_collection.sh

# Cron 서비스 상태 확인
sudo systemctl status cron
```

### 결과 파일 확인
```bash
# 수집 결과 확인
ls -la ~/naver_land/collectors/results/

# 최신 결과 파일 크기 확인
du -h ~/naver_land/collectors/results/*.json | tail -5
```

## 💰 비용 최적화

### 무료 티어 유지 조건
- **VM 유형**: e2-micro만 사용
- **지역**: us-west1, us-central1, us-east1
- **네트워크**: 월 1GB 아웃바운드 무료
- **디스크**: 30GB HDD 무료

### 용량 관리
```bash
# 오래된 파일 정리 (자동으로 설정됨)
find ~/naver_land/collectors/results -name "*.json" -mtime +7 -delete
find ~/naver_land/logs -name "*.log" -mtime +30 -delete

# 디스크 사용량 확인
df -h
du -sh ~/naver_land/
```

## 🔧 트러블슈팅

### 메모리 부족 시
```bash
# 스왑 파일 생성 (1GB)
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 수집 실패 시
```bash
# 로그 확인
tail -100 ~/naver_land/logs/daily_collection_*.log

# 수동 실행으로 디버깅
cd ~/naver_land/collectors
source ../venv/bin/activate
python3 parallel_batch_collect_gangnam.py --max-workers 1
```

## 📱 알림 설정 (선택사항)

### Slack/Discord 웹훅 알림
`daily_collection.sh`에 추가:
```bash
# 성공 시 알림
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"✅ 네이버 부동산 수집 완료"}' \
  YOUR_WEBHOOK_URL
```

## 🔄 업데이트 방법
```bash
cd ~/naver_land
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```