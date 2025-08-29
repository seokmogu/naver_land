# Monitoring System

실시간 모니터링 도구들입니다.

## 파일 구조

### 웹 대시보드
- `simple_monitor.py` - 실시간 웹 대시보드 (포트 8000)
- `live_monitor.py` - 라이브 모니터링 도구

### CLI 도구
- `check_collection_status.py` - CLI 상태 확인 도구

## 사용법

```bash
# 웹 대시보드 실행 (백그라운드)
python3 simple_monitor.py &

# CLI 상태 확인
python3 check_collection_status.py --quick

# 실시간 모니터링
python3 check_collection_status.py --realtime
```