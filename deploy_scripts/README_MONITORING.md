# 네이버 수집 모니터링 도구 배포 가이드

## 🚀 빠른 시작

### 1. 모니터링 도구 EC2 배포
```bash
cd /home/hackit/projects/naver_land/deploy_scripts
./deploy_monitoring.sh
```

### 2. 배포 후 사용법

#### 📊 빠른 상태 확인
```bash
ssh -i your-key.pem ubuntu@EC2-IP
./naver_land/monitoring/quick_check.sh
```

#### 🖥️ CLI 라이브 모니터링  
```bash
ssh -i your-key.pem ubuntu@EC2-IP
./naver_land/monitoring/start_cli_monitor.sh
```

#### 🌐 웹 대시보드
```bash
# EC2에서 실행
./naver_land/monitoring/start_dashboard.sh

# 브라우저에서 접속
http://EC2-PUBLIC-IP:8000
```

## 📋 배포되는 모니터링 도구들

### 1. **quick_status.py** - 빠른 상태 확인 ⚡
- **용도**: 현재 수집 상황 즉시 확인
- **실행**: `./monitoring/quick_check.sh`
- **특징**: 
  - 진행 중인 수집 현황
  - 오늘의 성공/실패 통계
  - 최근 완료된 작업들

### 2. **live_monitor.py** - CLI 라이브 대시보드 📊
- **용도**: 터미널에서 실시간 모니터링
- **실행**: `./monitoring/start_cli_monitor.sh`  
- **특징**:
  - 3초마다 자동 새로고침
  - 풀스크린 대시보드
  - 시스템 리소스 상태
  - Ctrl+C로 종료

### 3. **monitor_dashboard.py** - 웹 대시보드 🌐
- **용도**: 브라우저에서 예쁜 실시간 대시보드
- **실행**: `./monitoring/start_dashboard.sh`
- **접속**: `http://EC2-IP:8000`
- **특징**:
  - WebSocket 실시간 업데이트
  - 반응형 디자인
  - 시각적 차트 및 통계
  - 모바일 친화적

## 🛠️ 관리 명령어

### 모니터링 시작
```bash
# 웹 대시보드 시작
./naver_land/monitoring/start_dashboard.sh

# CLI 모니터링 시작  
./naver_land/monitoring/start_cli_monitor.sh

# 빠른 상태 확인
./naver_land/monitoring/quick_check.sh
```

### 모니터링 중지
```bash
# 모든 모니터링 서비스 중지
./naver_land/monitoring/stop_monitoring.sh
```

### 로그 확인
```bash
# 웹 대시보드 로그
tail -f /home/ubuntu/naver_land/logs/dashboard.log

# 수집 로그
tail -f /home/ubuntu/naver_land/logs/collector.log
```

## 🎯 사용 시나리오별 권장사항

### 💼 일상적인 확인
```bash
./monitoring/quick_check.sh
```
- 5초 내 현재 상황 파악
- 스크립트 실행 전후 상태 확인

### 📊 지속적인 모니터링  
```bash
./monitoring/start_cli_monitor.sh
```
- SSH 세션에서 계속 켜둠
- 수집 작업 진행 상황 실시간 추적

### 👥 팀 공유 및 원격 모니터링
```bash
./monitoring/start_dashboard.sh
# http://EC2-IP:8000 브라우저 접속
```
- 여러 명이 동시에 모니터링 가능
- 스마트폰에서도 접속 가능
- 시각적으로 이해하기 쉬움

## 🔧 트러블슈팅

### 포트 8000 접속 안 됨
```bash
# 보안 그룹 확인
aws ec2 describe-security-groups --group-ids sg-xxxxx

# 수동으로 포트 열기
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 8000 \
  --cidr 0.0.0.0/0
```

### 웹 대시보드 작동 안 함
```bash
# 프로세스 확인
ps aux | grep monitor_dashboard

# 로그 확인
tail -f /home/ubuntu/naver_land/logs/dashboard.log

# 재시작
./monitoring/stop_monitoring.sh
./monitoring/start_dashboard.sh
```

### 패키지 설치 오류
```bash
# 파이썬 패키지 재설치
pip3 install --upgrade fastapi uvicorn websockets psutil

# 시스템 패키지 업데이트
sudo apt update && sudo apt upgrade
```

## 📊 모니터링 정보 상세

### 실시간 추적 정보
- 🔄 **진행 중인 수집**: 현재 실행 중인 동별 수집 작업
- ⏱️ **경과 시간**: 각 작업의 시작부터 현재까지 소요 시간
- 📈 **진행률**: 단계별 진행 상황 (토큰 수집 → 데이터 수집 → DB 저장)
- 💾 **수집 성과**: 실시간 매물 개수 집계

### 통계 및 성과 지표
- 📊 **오늘의 요약**: 총 작업 수, 성공률, 수집된 매물 수
- 🏆 **성과 순위**: 동별 수집 성과 비교
- ⚡ **성능 지표**: 평균 소요 시간, 처리 속도
- 🔥 **시스템 상태**: CPU, 메모리, 디스크 사용률

### 문제 진단 정보
- ❌ **실패 원인**: 상세한 에러 메시지 및 스택 트레이스
- ⏰ **타임아웃**: 장시간 진행되는 작업 감지
- 🔧 **리소스 상태**: 시스템 리소스 병목 지점 파악
- 📋 **작업 이력**: 최근 완료된 작업들의 상세 정보

## 🎉 활용 팁

1. **대시보드를 항상 켜두기**: 웹 대시보드를 백그라운드로 실행하고 브라우저 탭을 열어두면 언제든 확인 가능

2. **알림 설정**: 브라우저 알림을 허용하면 수집 완료 시 알림 받기 가능

3. **모바일 접속**: 스마트폰 브라우저로도 접속하여 이동 중에도 모니터링 가능

4. **로그 분석**: 문제 발생 시 로그 파일을 통해 상세한 원인 분석 가능

이제 네이버 수집 작업을 **언제 어디서든** 실시간으로 모니터링할 수 있습니다! 🚀