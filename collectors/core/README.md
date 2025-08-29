# Core Collection System

네이버 부동산 수집기의 핵심 모듈들입니다.

## 파일 구조

### 메인 수집기
- `log_based_collector.py` - 로그 기반 메인 수집기 (최신 최적화 버전)
- `unified_collector.py` - 통합 수집기
- `fixed_naver_collector_v2_optimized.py` - 네이버 API 수집 엔진

### 로깅 시스템
- `log_based_logger.py` - 실시간 JSON 로깅 시스템

## 사용법

```bash
# 메인 수집기 실행
python3 log_based_collector.py --single

# 통합 수집기 실행  
python3 unified_collector.py
```