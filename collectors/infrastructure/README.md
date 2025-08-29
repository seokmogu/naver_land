# Infrastructure Support

인프라 지원 모듈들입니다.

## 파일 구조

### 인증 및 토큰
- `playwright_token_collector.py` - JWT 토큰 수집기 (Playwright 기반)
- `cached_token_collector.py` - 캐시된 토큰 수집기

### 데이터베이스
- `supabase_client.py` - Supabase 데이터베이스 클라이언트

### 데이터 변환
- `kakao_address_converter.py` - 카카오 API 기반 주소 변환
- `json_to_supabase.py` - JSON 데이터를 Supabase로 변환

### 기타 도구
- `enhanced_logger.py` - 고급 로깅 시스템
- `progress_logger.py` - 진행 상황 로거
- `integrated_logger.py` - 통합 로깅 시스템

## 사용법

```bash
# JWT 토큰 수집
python3 playwright_token_collector.py

# JSON 데이터 업로드
python3 json_to_supabase.py --file data.json
```