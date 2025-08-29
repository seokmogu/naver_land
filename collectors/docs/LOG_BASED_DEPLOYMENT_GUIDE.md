# 로그 기반 수집기 EC2 배포 가이드

## 🎯 개요
`log_based_collector.py`와 `log_based_logger.py`를 활용한 실시간 모니터링 지원 수집기의 EC2 배포 및 운영 가이드입니다.

## 📋 주요 특징

### ✅ 완성된 기능들
- **로그 기반 진행 상황 추적**: JSON 로그 파일을 통한 실시간 모니터링
- **DB 업데이트 최소화**: 수집 시작/완료만 DB 기록
- **실제 네이버 API 연동**: 토큰 캐싱을 통한 효율적 수집
- **병렬 처리 지원**: 단일 또는 다중 프로세스 수집
- **안전한 오류 처리**: 개별 동별 오류 격리

### 📁 파일 구조
```
collectors/
├── log_based_collector.py         # 메인 수집기
├── log_based_logger.py            # 로깅 시스템
├── supabase_client.py             # DB 연결
├── fixed_naver_collector_v2_optimized.py  # 실제 수집 로직
├── playwright_token_collector.py   # 토큰 수집
├── config.json                    # 설정 파일
└── logs/                          # 로그 디렉토리
    ├── live_progress.jsonl        # 실시간 진행 로그
    ├── collection_data.jsonl     # 수집 데이터 로그
    └── status.json               # 현재 상태 요약
```

## 🚀 EC2 배포 단계

### 1단계: EC2 환경 준비

```bash
# 1. EC2 인스턴스 접속
ssh -i "naver-land-collector-v2-key.pem" ubuntu@<EC2-IP>

# 2. 프로젝트 디렉토리로 이동
cd /home/ubuntu/naver_land/collectors/

# 3. Python 패키지 설치 확인
pip3 install supabase playwright pytz requests

# 4. Playwright 브라우저 설치
playwright install chromium

# 5. 권한 설정
chmod +x log_based_collector.py
mkdir -p logs
chmod 755 logs
```

### 2단계: 설정 파일 확인

```bash
# config.json 확인 및 수정
cat config.json

# 필요시 Supabase 연결 정보 업데이트
nano config.json
```

**config.json 예시:**
```json
{
  "kakao_api": {
    "rest_api_key": "your-kakao-key"
  },
  "supabase": {
    "url": "https://your-project.supabase.co",
    "anon_key": "your-supabase-key"
  },
  "collection_settings": {
    "default_max_pages": 21,
    "detail_collection_delay": 0.8,
    "page_request_delay": 1.5,
    "memory_efficient_mode": true
  }
}
```

### 3단계: 테스트 실행

```bash
# 단일 동 테스트
python3 log_based_collector.py --test-single 역삼동

# 전체 수집 테스트 (1개 프로세스)
python3 log_based_collector.py --max-workers 1
```

### 4단계: 시스템 서비스 설정

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/naver-log-collector.service
```

**서비스 설정 파일:**
```ini
[Unit]
Description=Naver Real Estate Log-based Collector
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/naver_land/collectors
ExecStart=/usr/bin/python3 log_based_collector.py --max-workers 2
Restart=always
RestartSec=10

# 환경 변수
Environment=PYTHONPATH=/home/ubuntu/naver_land/collectors
Environment=DISPLAY=:0

# 로그 설정
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable naver-log-collector
sudo systemctl start naver-log-collector

# 상태 확인
sudo systemctl status naver-log-collector
```

### 5단계: 모니터링 설정

#### 실시간 로그 모니터링
```bash
# 진행 상황 실시간 확인
tail -f logs/live_progress.jsonl

# 상태 요약 확인
watch -n 5 'cat logs/status.json | python3 -m json.tool'

# 수집 데이터 확인
tail -n 100 logs/collection_data.jsonl
```

#### 간단한 웹 모니터링 서버
```python
# monitor_server.py 생성
import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

class LogMonitorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            try:
                with open('logs/status.json', 'r', encoding='utf-8') as f:
                    status = json.load(f)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(status, ensure_ascii=False, indent=2).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            super().do_GET()

if __name__ == '__main__':
    os.chdir('/home/ubuntu/naver_land/collectors')
    httpd = HTTPServer(('0.0.0.0', 8888), LogMonitorHandler)
    print("모니터링 서버 시작: http://EC2-IP:8888/status")
    httpd.serve_forever()
```

```bash
# 백그라운드로 모니터링 서버 실행
nohup python3 monitor_server.py &
```

### 6단계: 크론탭 설정 (정기 실행)

```bash
# 크론탭 편집
crontab -e

# 매일 오전 2시 실행
0 2 * * * cd /home/ubuntu/naver_land/collectors && python3 log_based_collector.py --max-workers 2 >> /var/log/naver-collector.log 2>&1

# 매 6시간마다 실행
0 */6 * * * cd /home/ubuntu/naver_land/collectors && python3 log_based_collector.py --max-workers 1 >> /var/log/naver-collector.log 2>&1
```

## 🔧 운영 명령어

### 기본 실행 명령어
```bash
# 기본 실행 (1개 프로세스)
python3 log_based_collector.py

# 병렬 실행 (2개 프로세스)
python3 log_based_collector.py --max-workers 2

# 단일 동 테스트
python3 log_based_collector.py --test-single 삼성동

# 도움말
python3 log_based_collector.py --help
```

### 서비스 관리 명령어
```bash
# 서비스 시작/중지/재시작
sudo systemctl start naver-log-collector
sudo systemctl stop naver-log-collector
sudo systemctl restart naver-log-collector

# 서비스 상태 확인
sudo systemctl status naver-log-collector

# 서비스 로그 확인
sudo journalctl -u naver-log-collector -f

# 서비스 비활성화/활성화
sudo systemctl disable naver-log-collector
sudo systemctl enable naver-log-collector
```

### 로그 관리 명령어
```bash
# 실시간 진행 상황 모니터링
tail -f logs/live_progress.jsonl | jq '.'

# 상태 요약 확인
cat logs/status.json | jq '.'

# 수집 데이터 확인
tail -n 10 logs/collection_data.jsonl | jq '.'

# 로그 파일 크기 확인
du -sh logs/*

# 오래된 로그 정리 (7일 이상)
find logs/ -name "*.jsonl" -mtime +7 -delete
```

## 📊 모니터링 및 알람

### 1. 진행 상황 체크 스크립트
```bash
# check_progress.sh 생성
#!/bin/bash
STATUS_FILE="/home/ubuntu/naver_land/collectors/logs/status.json"

if [ -f "$STATUS_FILE" ]; then
    ACTIVE_TASKS=$(cat $STATUS_FILE | jq -r 'to_entries[] | select(.value.status == "in_progress") | .key' | wc -l)
    COMPLETED_TASKS=$(cat $STATUS_FILE | jq -r 'to_entries[] | select(.value.status == "completed") | .key' | wc -l)
    
    echo "활성 작업: $ACTIVE_TASKS"
    echo "완료 작업: $COMPLETED_TASKS"
    
    if [ $ACTIVE_TASKS -eq 0 ] && [ $COMPLETED_TASKS -gt 0 ]; then
        echo "✅ 수집 완료"
    elif [ $ACTIVE_TASKS -gt 0 ]; then
        echo "🔄 수집 진행 중"
    else
        echo "⚠️ 수집 상태 불명"
    fi
else
    echo "❌ 상태 파일 없음"
fi

chmod +x check_progress.sh
```

### 2. 슬랙 알람 설정 (선택사항)
```python
# slack_alert.py
import json
import requests
from datetime import datetime

def send_slack_alert(message):
    webhook_url = "your-slack-webhook-url"
    payload = {
        "text": f"[네이버 수집기] {message}",
        "username": "collector-bot",
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print("슬랙 알림 전송 완료")
        else:
            print(f"슬랙 알림 실패: {response.status_code}")
    except Exception as e:
        print(f"슬랙 알림 오류: {e}")

# 수집 완료 시 호출
if __name__ == '__main__':
    with open('logs/status.json', 'r') as f:
        status = json.load(f)
    
    completed = len([v for v in status.values() if v['status'] == 'completed'])
    send_slack_alert(f"수집 완료: {completed}개 동")
```

## 🚨 트러블슈팅

### 자주 발생하는 문제들

1. **토큰 만료 오류**
   ```bash
   # 캐시된 토큰 삭제
   rm cached_token.json
   
   # 수집기 재시작
   sudo systemctl restart naver-log-collector
   ```

2. **메모리 부족**
   ```bash
   # 메모리 사용량 확인
   free -h
   
   # 프로세스 수 줄이기
   python3 log_based_collector.py --max-workers 1
   ```

3. **로그 파일 권한 오류**
   ```bash
   # 권한 재설정
   sudo chown -R ubuntu:ubuntu logs/
   chmod -R 755 logs/
   ```

4. **네트워크 연결 오류**
   ```bash
   # DNS 확인
   nslookup land.naver.com
   
   # 방화벽 확인
   sudo ufw status
   ```

### 로그 분석 도구
```bash
# 오류 발생 확인
grep -i "error\|fail" logs/live_progress.jsonl

# 수집 통계
grep "complete" logs/live_progress.jsonl | jq '.total_collected' | awk '{sum+=$1} END {print "총 수집:", sum}'

# 평균 수집 시간
grep "complete" logs/live_progress.jsonl | jq -r '.timestamp' | head -n 2 | tail -n 1
```

## 📈 성능 최적화

### 권장 설정
- **EC2 인스턴스**: t3.medium 이상 (2 vCPU, 4GB RAM)
- **병렬 프로세스**: 2-4개 (CPU 코어 수에 따라)
- **수집 간격**: 최소 1초 (rate limiting 고려)
- **로그 로테이션**: 주간 단위 정리

### 모니터링 지표
- CPU 사용률 < 80%
- 메모리 사용률 < 70%
- 네트워크 응답시간 < 5초
- 수집 성공률 > 90%

## 🔄 업데이트 방법

```bash
# 1. 서비스 중지
sudo systemctl stop naver-log-collector

# 2. 코드 백업
cp -r /home/ubuntu/naver_land/collectors /home/ubuntu/backup_$(date +%Y%m%d)

# 3. 새 코드 업데이트
# (git pull 또는 파일 복사)

# 4. 설정 확인
python3 log_based_collector.py --test-single 역삼동

# 5. 서비스 재시작
sudo systemctl start naver-log-collector
sudo systemctl status naver-log-collector
```

---

## 📞 지원 정보

- **로그 파일 위치**: `/home/ubuntu/naver_land/collectors/logs/`
- **설정 파일**: `/home/ubuntu/naver_land/collectors/config.json`
- **모니터링 URL**: `http://EC2-IP:8888/status`
- **서비스 로그**: `sudo journalctl -u naver-log-collector`

이 가이드를 통해 로그 기반 수집기를 안정적으로 EC2에서 운영할 수 있습니다.