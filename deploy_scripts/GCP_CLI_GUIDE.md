# 🚀 Google Cloud CLI 완전 자동화 배포 가이드

## 📋 생성된 스크립트 목록

### 🔧 핵심 배포 스크립트
- `install_gcloud.sh` - Google Cloud CLI 자동 설치
- `create_vm.sh` - VM 인스턴스 생성 (e2-micro 무료 티어)
- `deploy_to_gcp.sh` - 전체 배포 과정 자동화 (원클릭 배포)
- `manage_vm.sh` - VM 관리 도구 (시작/중지/SSH/로그확인 등)

### 📁 기존 스크립트 (VM 내부에서 사용)
- `setup_project.sh` - 프로젝트 환경 설정
- `setup_cron.sh` - 자동 스케줄링 설정

## 🎯 원클릭 배포 방법

### **단계 1: 로컬에서 전체 배포 실행**
```bash
# 현재 프로젝트 디렉토리에서 실행
./deploy_scripts/deploy_to_gcp.sh
```

이 명령어 하나로 다음이 모두 자동화됩니다:
1. ✅ Google Cloud CLI 설치/확인
2. ✅ Google 계정 인증
3. ✅ GCP 프로젝트 설정/생성
4. ✅ VM 인스턴스 생성 (e2-micro 무료 티어)
5. ✅ 방화벽 규칙 설정
6. ✅ 기본 환경 설정

### **단계 2: VM에서 프로젝트 설정**
SSH 접속 후:
```bash
# 프로젝트 클론
~/setup/clone_project.sh
# GitHub URL 입력: https://github.com/your-username/naver_land.git

# API 키 설정
cd ~/naver_land/collectors
python3 setup_deployment.py

# 자동 스케줄링 설정
cd ~/naver_land
./deploy_scripts/setup_cron.sh
```

## 🛠️ VM 관리 도구 사용법

로컬에서 VM을 원격 관리:

```bash
# VM 상태 확인
./deploy_scripts/manage_vm.sh status

# VM 시작/중지
./deploy_scripts/manage_vm.sh start
./deploy_scripts/manage_vm.sh stop

# SSH 접속
./deploy_scripts/manage_vm.sh ssh

# 수집 로그 확인
./deploy_scripts/manage_vm.sh logs

# 수집 결과 확인
./deploy_scripts/manage_vm.sh results

# 비용 확인
./deploy_scripts/manage_vm.sh cost
```

## 💰 무료 티어 최적화

### 자동 설정된 무료 티어 사양
- **VM**: e2-micro (0.25-1 vCPU, 1GB RAM)
- **디스크**: 30GB HDD (무료)
- **지역**: us-central1-a (무료 티어 지원)
- **네트워크**: 월 1GB 아웃바운드 무료

### 비용 절약 팁
```bash
# 사용하지 않을 때 VM 중지 (컴퓨팅 비용 0원)
./deploy_scripts/manage_vm.sh stop

# 필요할 때만 시작
./deploy_scripts/manage_vm.sh start
```

## 🔄 일일 자동 수집 스케줄

자동으로 설정되는 Cron 작업:
- **실행 시간**: 매일 오전 9시
- **수집 범위**: 강남구 전체
- **성능 최적화**: 4개 워커 병렬 처리
- **자동 정리**: 7일 이상된 결과 파일 삭제

## 📊 모니터링 대시보드

### 로그 실시간 모니터링
```bash
# VM에 SSH 접속하여 실시간 로그 확인
./deploy_scripts/manage_vm.sh ssh
tail -f ~/naver_land/logs/daily_collection_*.log
```

### 수집 결과 확인
```bash
# 최신 수집 결과 확인
./deploy_scripts/manage_vm.sh results

# 특정 날짜 결과 다운로드
gcloud compute scp --zone="us-central1-a" \
  naver-collector:~/naver_land/collectors/results/parallel_collection_*.json \
  ./local_results/
```

## 🚨 트러블슈팅

### 1. VM 생성 실패
```bash
# API 활성화 확인
gcloud services enable compute.googleapis.com

# 프로젝트 결제 계정 연결 확인
# https://console.cloud.google.com/billing
```

### 2. 메모리 부족 (1GB RAM 제한)
VM에서 스왑 파일 생성:
```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 3. 수집 실패 시 디버깅
```bash
# 로그 확인
./deploy_scripts/manage_vm.sh logs

# 수동 실행으로 문제 파악
./deploy_scripts/manage_vm.sh ssh
cd ~/naver_land/collectors
source ../venv/bin/activate
python3 parallel_batch_collect_gangnam.py --max-workers 1
```

## 🔧 고급 설정

### VM 사양 변경 (비용 발생 주의)
```bash
# VM 중지 후 사양 변경
gcloud compute instances stop naver-collector --zone=us-central1-a
gcloud compute instances set-machine-type naver-collector \
  --machine-type=e2-small --zone=us-central1-a
gcloud compute instances start naver-collector --zone=us-central1-a
```

### 다른 지역으로 이전
```bash
# 기존 VM 삭제
./deploy_scripts/manage_vm.sh delete

# create_vm.sh에서 ZONE 변수 수정 후 재실행
./deploy_scripts/create_vm.sh
```

## 📈 확장 계획

### 다른 구 추가 수집
```bash
# VM에서 설정 파일 수정
vim ~/naver_land/collectors/gu_config.json
# 송파구, 서초구 등 추가

# 새로운 수집 스크립트 실행
python3 parallel_batch_collect_all_gu.py
```

### 수집 주기 변경
```bash
# Cron 설정 수정
crontab -e
# 0 9 * * * -> 0 */6 * * * (6시간마다)
```

## ✅ 배포 완료 체크리스트

- [ ] `./deploy_scripts/deploy_to_gcp.sh` 실행 완료
- [ ] VM SSH 접속 가능
- [ ] 프로젝트 클론 및 환경 설정 완료
- [ ] API 키 설정 완료 (Kakao, Supabase)
- [ ] Cron 자동 스케줄링 설정 완료
- [ ] 수동 수집 테스트 성공
- [ ] 로그 및 결과 파일 생성 확인

## 🎉 완료!

이제 매일 자동으로 네이버 부동산 데이터가 수집되며, 로컬에서 원격으로 모든 것을 관리할 수 있습니다.