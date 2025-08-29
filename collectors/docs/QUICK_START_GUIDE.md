# ⚡ 로그 기반 수집기 빠른 시작 가이드

## 🎯 완성된 시스템 즉시 사용법

### 1. EC2 접속 및 기본 설정
```bash
ssh -i "your-key.pem" ubuntu@<EC2-IP>
cd /home/ubuntu/naver_land/collectors
```

### 2. 시스템 상태 확인 (CLI 도구)
```bash
# 빠른 전체 상태 확인
python3 check_collection_status.py --quick

# 상세 현황 (로그, DB, 파일 상태)
python3 check_collection_status.py --detailed

# DB 연결 및 데이터 상태
python3 check_collection_status.py --db-status

# 최근 로그 확인
python3 check_collection_status.py --recent-logs
```

### 3. 메인 수집기 실행 (검증 완료)
```bash
# 강남구 전체 수집 (단일 프로세스 - 안정적)
python3 log_based_collector.py --single

# 강남구 전체 수집 (멀티프로세스 - 빠름)
python3 log_based_collector.py --parallel

# 특정 동만 수집 테스트
python3 log_based_collector.py --dong 역삼동

# 백그라운드 실행 (권장)
nohup python3 log_based_collector.py --single > collection.log 2>&1 &
```

### 4. 실시간 모니터링 시작 (웹 대시보드)
```bash
# 모니터링 웹서버 시작 (별도 터미널)
python3 simple_monitor.py

# 원격 접속 허용 (EC2 환경)
python3 simple_monitor.py --host 0.0.0.0 --port 8000

# 백그라운드 실행
nohup python3 simple_monitor.py --host 0.0.0.0 > monitor.log 2>&1 &

# 브라우저에서 접속
# 로컬: http://localhost:8000
# EC2: http://<EC2-IP>:8000
```

### 5. 실시간 진행 상황 모니터링
```bash
# 실시간 모드 (진행중일 때)
python3 check_collection_status.py --realtime

# 또는 로그 파일 직접 확인
tail -f logs/live_progress.jsonl
tail -f logs/status.json

# 수집된 매물 데이터 확인
tail -f logs/collection_data.jsonl
```

### 6. 완성된 시스템 특징 요약
```bash
✅ 실제 검증 완료: 강남구 14개 동, 580개 매물 수집 성공
✅ 로그 기반 모니터링: 모든 진행상황 실시간 추적  
✅ 웹 대시보드: 브라우저에서 실시간 모니터링
✅ CLI 도구: 터미널에서 즉시 상태 확인
✅ 안전한 오류 처리: 개별 동 실패시에도 전체 진행
✅ DB 자동 저장: Supabase에 실시간 매물 정보 저장

# 시스템 상태 확인
ps aux | grep python
```

---

## 📊 핵심 지표
- **현재 매물**: 85,107개 (안전하게 보호됨)
- **수집 품질**: A급 (90점 이상)
- **데이터 무결성**: 25/100 (개선 중)

## 🚨 주의사항
- 기존 85,107개 매물 삭제 절대 금지
- 모든 변경사항은 --test 모드로 먼저 확인
- 문제 발생시 즉시 응급 중단 스크립트 실행