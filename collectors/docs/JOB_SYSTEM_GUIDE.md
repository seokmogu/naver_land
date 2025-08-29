# 🚀 라이트웨이트 Job 관리 시스템 사용 가이드

EC2 환경에 최적화된 초경량 Job 스케줄러 & 모니터링 시스템

## 📋 시스템 개요

### 🎯 주요 특징
- **메모리 효율성**: 전체 시스템 <100MB 사용
- **파일 기반**: DB 의존성 최소화, JSON 로그 활용
- **기존 시스템 호환**: 현재 네이버 수집기와 완벽 연동
- **웹 UI**: 직관적인 Job 생성/관리 인터페이스
- **CLI 도구**: 서버 관리용 명령줄 인터페이스

### 🏗️ 아키텍처
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  웹 대시보드     │    │  CLI 도구       │    │  현재 수집기     │
│  (8888 포트)    │    │  (job_cli.py)   │    │  (완벽 연동)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │          라이트웨이트 스케줄러                    │
         │        (lightweight_scheduler.py)              │
         │                                               │
         │  • JSON 파일 기반 상태 관리                     │
         │  • 메모리 <20MB 사용                          │
         │  • 동시 실행 제한: 3개                         │
         │  • 우선순위 기반 스케줄링                       │
         └─────────────────────────────────────────────────┘
                                 │
         ┌─────────────────────────────────────────────────┐
         │              파일 시스템                        │
         │                                               │
         │  scheduler_data/                              │
         │  ├── jobs.json         (Job 정의)              │
         │  ├── running_jobs.json (실행 상태)              │
         │  └── job_logs/         (실행 로그)              │
         └─────────────────────────────────────────────────┘
```

## 🛠️ 설치 및 배포

### 1. 자동 배포 (권장)
```bash
# 배포 스크립트 실행
chmod +x deploy_job_system.sh
./deploy_job_system.sh

# 테스트만 실행
./deploy_job_system.sh --test-only

# systemd 서비스 없이 배포 (권한 문제시)
./deploy_job_system.sh --no-systemd
```

### 2. 수동 배포
```bash
# 1. 의존성 설치
pip3 install --user requests pytz

# 2. 디렉토리 생성
mkdir -p scheduler_data/job_logs logs results

# 3. 권한 설정
chmod +x *.py
```

### 3. 시스템 요구사항
- **Python**: 3.7+ 
- **메모리**: 512MB 권장 (시스템은 <100MB 사용)
- **디스크**: 1GB 여유공간
- **포트**: 8888 (대시보드용)

## 🚀 빠른 시작

### 1단계: 기본 설정
```bash
# 권장 Job들 자동 생성
python3 job_cli.py setup

# 생성된 Job 확인
python3 job_cli.py list
```

### 2단계: 스케줄러 시작
```bash
# 데몬 모드로 시작 (백그라운드)
python3 job_cli.py start --daemon

# 상태 확인
python3 job_cli.py status
```

### 3단계: 웹 대시보드 시작
```bash
# 대시보드 시작
python3 job_dashboard.py

# 브라우저에서 접속
# 로컬: http://localhost:8888
# EC2: http://<EC2-PUBLIC-IP>:8888
```

## 💻 웹 대시보드 사용법

### 메인 화면
- **실시간 통계**: 총 Job 수, 실행 중, 완료, 실패 등
- **진행률 표시**: 현재 실행 중인 작업들의 진행률
- **동별 상태**: 강남구 14개 동 수집 현황
- **최근 결과**: 수집된 파일들 목록

### Job 생성
1. **➕ 새 Job 생성** 버튼 클릭
2. Job 정보 입력:
   - **Job 이름**: 식별하기 쉬운 이름
   - **수집 타입**: 단일 동 vs 전체 강남구
   - **대상 동**: 단일 동 수집시 선택
   - **스케줄**: 즉시 실행 vs 반복 실행
   - **우선순위**: 1(높음) ~ 10(낮음)
   - **재시도**: 실패시 재시도 횟수

### Job 관리
- **⏹️ 취소**: 실행 중인 Job 중지
- **🗑️ 제거**: 완료/실패한 Job 삭제
- **상태 모니터링**: 실시간 진행 상황 확인

## 🖥️ CLI 도구 사용법

### Job 목록 및 상태
```bash
# 모든 Job 목록
python3 job_cli.py list

# 상태별 필터링
python3 job_cli.py list --status running
python3 job_cli.py list --status completed

# 시스템 전체 상태
python3 job_cli.py status
```

### Job 생성
```bash
# 단일 동 수집 Job
python3 job_cli.py create single --dong 역삼동 --name "역삼동_정기수집"

# 전체 강남구 수집 Job  
python3 job_cli.py create full --workers 2 --name "전체수집_2프로세스"

# 반복 실행 Job (6시간마다)
python3 job_cli.py create single --dong 삼성동 \
    --schedule interval --interval 21600 --name "삼성동_정기"

# 높은 우선순위 Job
python3 job_cli.py create single --dong 논현동 \
    --priority 1 --retries 2 --name "논현동_중요"
```

### Job 관리
```bash
# Job 취소
python3 job_cli.py cancel <job_id>

# Job 제거
python3 job_cli.py remove <job_id>

# 로그 확인
python3 job_cli.py logs
python3 job_cli.py logs --job-id <job_id> --lines 50
```

### 스케줄러 관리
```bash
# 스케줄러 시작 (포그라운드)
python3 job_cli.py start

# 스케줄러 시작 (백그라운드)
python3 job_cli.py start --daemon

# 스케줄러 중지
python3 job_cli.py stop
```

## ⚙️ 고급 설정

### 스케줄 타입 설명
- **once**: 즉시 1회 실행
- **interval**: 지정 시간 간격으로 반복 실행

### 반복 주기 예제
```bash
# 1시간마다: --interval 3600
# 6시간마다: --interval 21600  
# 12시간마다: --interval 43200
# 24시간마다: --interval 86400
```

### 우선순위 전략
- **1-2**: 긴급/중요한 수집 작업
- **3-5**: 일반적인 정기 수집
- **6-8**: 낮은 우선순위 백그라운드 작업
- **9-10**: 시스템 부하가 적을 때만 실행

### 메모리 최적화
```json
{
    "system": {
        "max_memory_mb": 100,
        "max_concurrent_jobs": 3,
        "cleanup_interval_hours": 24
    }
}
```

## 🔧 시스템 관리

### systemd 서비스 (권장)
```bash
# 서비스 시작
sudo systemctl start job-scheduler
sudo systemctl start job-dashboard

# 자동 시작 설정
sudo systemctl enable job-scheduler  
sudo systemctl enable job-dashboard

# 상태 확인
sudo systemctl status job-scheduler
```

### 수동 관리
```bash
# 프로세스 확인
ps aux | grep "job_cli.py\|job_dashboard.py"

# 포트 사용 확인  
netstat -tlnp | grep 8888

# 로그 실시간 확인
tail -f scheduler_data/scheduler.log
tail -f logs/live_progress.jsonl
```

### 디스크 정리
```bash
# 오래된 로그 파일 정리 (7일 이상)
find scheduler_data/job_logs -name "*.log" -mtime +7 -delete
find logs -name "*.jsonl" -mtime +7 -delete

# 완료된 Job 결과 정리
find results -name "naver_optimized_*.json" -mtime +30 -delete
```

## 📊 모니터링 & 문제 해결

### 성능 모니터링
```bash
# 메모리 사용량 확인
python3 -c "
import psutil
import os
for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
    if 'python' in proc.info['name'].lower():
        print(f'{proc.info[\"pid\"]}: {proc.info[\"name\"]} - {proc.info[\"memory_info\"].rss/1024/1024:.1f}MB')
"

# 디스크 사용량
df -h .
du -sh scheduler_data logs results
```

### 일반적인 문제들

#### 1. Job이 실행되지 않음
**원인**: 스케줄러가 실행되지 않음
```bash
# 해결방법
python3 job_cli.py status  # 스케줄러 상태 확인
python3 job_cli.py start --daemon  # 스케줄러 시작
```

#### 2. 웹 대시보드 접속 불가
**원인**: 포트 8888이 차단됨
```bash
# 해결방법 (AWS EC2)
# 보안 그룹에서 포트 8888 허용

# 로컬 방화벽 (Ubuntu/CentOS)
sudo ufw allow 8888/tcp
```

#### 3. Job 실행 실패
**원인**: 명령어 오류 또는 권한 문제
```bash
# 해결방법
python3 job_cli.py logs --job-id <실패한_job_id>  # 로그 확인
chmod +x log_based_collector.py  # 실행 권한 확인
```

#### 4. 메모리 부족
**원인**: 동시 실행 Job 너무 많음
```bash
# 해결방법 (job_system_config.json 수정)
{
    "system": {
        "max_concurrent_jobs": 2  # 기본 3에서 2로 줄임
    }
}
```

### 로그 위치
```
scheduler_data/
├── scheduler.log          # 스케줄러 메인 로그
├── job_logs/              # 개별 Job 실행 로그
│   ├── job_id_1.log
│   └── job_id_2.log
└── running_jobs.json      # 현재 실행 중인 Job 정보

logs/
├── live_progress.jsonl    # 수집 진행 상황 로그
└── status.json           # 현재 수집 상태
```

## 🔐 보안 설정

### 기본 보안
- 웹 대시보드는 HTTP (프로덕션에서는 nginx + SSL 권장)
- 기본적으로 모든 IP에서 접근 가능 (--host 0.0.0.0)

### 접근 제한 (권장)
```bash
# 특정 IP에서만 접근 허용
python3 job_dashboard.py --host 127.0.0.1  # 로컬만
python3 job_dashboard.py --host <내부IP>    # 내부망만

# nginx 프록시 설정 (선택사항)
# /etc/nginx/sites-available/job-dashboard
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8888;
        proxy_set_header Host $host;
    }
}
```

## 📈 성능 최적화

### EC2 인스턴스 권장사양
- **t3.micro**: 1GB RAM, 2 vCPU (개발/테스트)
- **t3.small**: 2GB RAM, 2 vCPU (프로덕션)
- **스토리지**: 8GB+ EBS

### 최적화 팁
1. **동시 실행 제한**: 최대 2-3개 Job
2. **메모리 모니터링**: 80% 이상시 알림 설정
3. **로그 순환**: 일주일마다 오래된 로그 삭제
4. **결과 파일 관리**: 30일 이상된 수집 결과 아카이빙

### 비용 최적화 (AWS)
- **예약 인스턴스**: 1년 약정으로 비용 절약
- **자동 스케일링**: 사용량에 따른 인스턴스 조정
- **CloudWatch 알림**: 비정상 상황 조기 감지

## 🎯 사용 시나리오

### 시나리오 1: 정기 수집
```bash
# 매일 새벽 2시에 전체 수집
python3 job_cli.py create full --workers 2 \
    --schedule interval --interval 86400 \
    --name "일일_전체수집"
```

### 시나리오 2: 인기 지역 집중 모니터링  
```bash
# 인기 동네 6시간마다 개별 수집
for dong in 역삼동 삼성동 논현동 대치동; do
    python3 job_cli.py create single --dong $dong \
        --schedule interval --interval 21600 \
        --priority 3 --name "정기수집_${dong}"
done
```

### 시나리오 3: 응급 데이터 수집
```bash
# 높은 우선순위로 즉시 실행
python3 job_cli.py create single --dong 역삼동 \
    --priority 1 --retries 3 --name "응급수집_역삼동"
```

### 시나리오 4: 시스템 부하 분산
```bash
# 낮은 우선순위로 시스템 여유시에만 실행
python3 job_cli.py create full --workers 1 \
    --priority 8 --name "백그라운드_수집"
```

---

## 📞 지원 및 문의

### 문제 보고
- GitHub Issues 또는 개발팀 연락
- 로그 파일과 함께 상세한 증상 기술

### 추가 기능 요청
- 새로운 스케줄 타입 (cron 표현식 등)
- 알림 기능 (이메일, 슬랙 등)
- 성능 대시보드 확장

이 시스템은 현재 완벽히 작동하는 네이버 수집기를 기반으로 설계되었으며, 기존 워크플로우를 방해하지 않으면서 강력한 자동화 기능을 제공합니다. 🚀