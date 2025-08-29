# 로그 기반 수집기 모니터링 가이드

## 🎯 완성된 3가지 모니터링 방법

### 방법 1: CLI 상태 확인 도구 (가장 편리)
```bash
# 빠른 전체 상태 확인
python3 check_collection_status.py --quick

# 상세 진행 현황 (로그, DB, 파일 상태)  
python3 check_collection_status.py --detailed

# 실시간 모니터링 모드 (수집 중일 때)
python3 check_collection_status.py --realtime

# DB 연결 및 저장 상태 확인
python3 check_collection_status.py --db-status

# 최근 로그만 빠르게 확인
python3 check_collection_status.py --recent-logs

# 주기적 업데이트 (30초마다)
watch -n 30 'python3 check_collection_status.py --quick'
```

### 방법 2: 웹 대시보드 (시각적 모니터링)
```bash
# 모니터링 웹서버 시작
python3 simple_monitor.py

# 백그라운드 실행 (8888번 포트)
nohup python3 simple_monitor.py --host 0.0.0.0 --port 8888 > monitor.log 2>&1 &

# 브라우저에서 실시간 확인  
open http://localhost:8888

# REST API로 상태 조회 (8888번 포트)
curl http://localhost:8888/api/status | jq
curl http://localhost:8888/api/logs | jq  
curl http://localhost:8888/api/results | jq
```

### 방법 3: 로그 파일 직접 모니터링 (개발자용)
```bash
# 실시간 진행 상황 로그
tail -f logs/live_progress.jsonl

# JSON 예쁘게 보기 (jq 필요)
tail -f logs/live_progress.jsonl | jq '.'

# 현재 전체 상태 요약
cat logs/status.json | python3 -m json.tool

# 수집된 매물 데이터 실시간 확인
tail -f logs/collection_data.jsonl | jq '.properties[0].article_name'

# 에러나 특정 키워드 검색
grep "error\|ERROR" logs/live_progress.jsonl
grep "completed" logs/live_progress.jsonl
```

### 프로세스 및 시스템 상태 확인
```bash
# 수집기 프로세스 확인
ps aux | grep log_based_collector

# 모니터링 웹서버 확인  
ps aux | grep simple_monitor

# CPU/메모리 사용량 실시간 확인
top -p $(pgrep -f log_based_collector)

# 네트워크 연결 확인 (토큰 수집 등)
netstat -an | grep :443
```

## 🎯 핵심 확인 포인트

### ✅ 정상 동작 신호들
1. **로그 파일이 계속 업데이트됨**
   ```bash
   # 10초마다 파일 크기 변화 확인
   watch -n 10 'ls -la logs/*.jsonl'
   ```

2. **heartbeat 로그가 10초마다 기록됨**
   ```bash
   # heartbeat 확인
   tail -f logs/live_progress.jsonl | grep heartbeat
   ```

3. **새로운 매물 데이터가 계속 추가됨**
   ```bash
   # 데이터 로그 증가 확인
   watch -n 5 'wc -l logs/collection_data.jsonl'
   ```

### ⚠️ 문제 신호들
1. **로그가 10분 이상 멈춤** → 토큰 만료 또는 네트워크 오류
2. **heartbeat만 있고 데이터가 없음** → API 호출 실패
3. **JSON 구문 오류** → 파일 저장 과정에서 오류

## 🛠 문제 해결 방법

### 1. 수집 멈춤 해결
```bash
# 프로세스 강제 종료
pkill -f log_based_collector

# 캐시된 토큰 삭제
rm -f cached_token.json

# 재시작
python log_based_collector.py --test-single 역삼동
```

### 2. JSON 오류 수정
```bash
# 오류 파일 찾기
python -m json.tool results/naver_optimized_*.json > /dev/null

# 오류 있는 파일 백업 후 수동 수정
cp problematic_file.json problematic_file.json.backup
# 마지막 쉼표 제거 또는 괄호 닫기 추가
```

### 3. 디스크 용량 관리
```bash
# 로그 파일 크기 확인
du -sh logs/*

# 오래된 로그 정리 (7일 이상)
find logs/ -name "*.jsonl" -mtime +7 -delete

# 결과 파일 압축
gzip results/*.json
```

## 📈 수집 성능 모니터링

### 실시간 통계
```bash
# 분당 수집 매물 수 계산
grep '"type": "property"' logs/collection_data.jsonl | tail -n 60 | wc -l

# 동별 수집 현황
grep '"type": "complete"' logs/live_progress.jsonl | jq -r '.dong_name + ": " + (.total_collected|tostring) + "개"'

# 평균 수집 시간 (동당)
grep '"type": "complete"' logs/live_progress.jsonl | jq -r '.timestamp' | while read start; do echo "처리 중..."; done
```

### 데이터 품질 확인
```bash
# 중복 매물 확인
grep "매물번호" results/*.json | cut -d'"' -f4 | sort | uniq -d

# 빈 매물명 확인
grep '"매물명": ""' results/*.json | wc -l

# 가격 분포 확인
grep '"매매가격"' results/*.json | head -n 20
```

## 🔄 일상적인 모니터링 루틴

### 매일 체크리스트
1. **아침 (9시)**
   ```bash
   python check_collection_status.py
   du -sh logs/ results/
   ```

2. **점심 (12시)**
   ```bash
   tail -n 5 logs/live_progress.jsonl
   ps aux | grep log_based_collector
   ```

3. **저녁 (18시)**
   ```bash
   # 하루 수집 요약
   grep '"type": "complete"' logs/live_progress.jsonl | grep $(date +%Y-%m-%d)
   ```

### 주간 정리 작업
```bash
# 주말마다 실행
# 1. 오래된 로그 정리
find logs/ -name "*.jsonl" -mtime +7 -delete

# 2. 결과 파일 압축
gzip results/*$(date -d "1 week ago" +%Y%m%d)*.json

# 3. 상태 파일 초기화
echo '{}' > logs/status.json
```

## 🚨 알람 설정 (선택사항)

### 간단한 슬랙 알람
```bash
# 수집 완료시 알람
grep '"type": "complete"' logs/live_progress.jsonl | tail -n 1 | \
jq -r '"✅ " + .dong_name + " 수집 완료: " + (.total_collected|tostring) + "개 매물"' | \
curl -X POST -H 'Content-type: application/json' \
--data '{"text":"'"$(cat -)"'"}' \
YOUR_SLACK_WEBHOOK_URL
```

### 에러 감지 알람
```bash
# 30분간 heartbeat 없으면 알람
if [ $(find logs/live_progress.jsonl -mmin +30) ]; then
    echo "⚠️ 수집기 30분간 응답 없음" | \
    curl -X POST -H 'Content-type: application/json' \
    --data '{"text":"'"$(cat -)"'"}' \
    YOUR_SLACK_WEBHOOK_URL
fi
```

---

이 가이드를 통해 로컬에서 수집기 상태를 완벽하게 모니터링할 수 있습니다!