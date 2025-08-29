# 네이버 부동산 수집기

로그 기반 실시간 모니터링을 지원하는 네이버 부동산 데이터 수집 시스템입니다. 실제 네이버 API 연동, 웹 대시보드, CLI 모니터링 도구를 제공합니다.

## 🎯 주요 완성 기능

- ✅ **실제 네이버 API 연동**: 토큰 기반 인증으로 실제 매물 데이터 수집
- ✅ **로그 기반 모니터링**: 실시간 JSON 로그로 진행 상황 추적  
- ✅ **웹 대시보드**: 브라우저에서 실시간 상태 확인 가능
- ✅ **CLI 모니터링 도구**: 터미널에서 빠른 상태 확인
- ✅ **Supabase 연동**: 안정적인 데이터베이스 저장
- ✅ **실제 검증 완료**: 강남구 14개 동, 580개 매물 수집 확인

## 📁 핵심 파일 구조

### 🚀 메인 실행 파일
- `log_based_collector.py` - **메인 수집기** (로그 기반, 실제 API 연동)
- `log_based_logger.py` - 실시간 JSON 로깅 시스템
- `fixed_naver_collector_v2_optimized.py` - 네이버 API 수집 로직

### 📊 모니터링 도구
- `simple_monitor.py` - **웹 대시보드** (실시간 모니터링)
- `check_collection_status.py` - **CLI 상태 확인 도구**

### 🔧 지원 모듈
- `playwright_token_collector.py` - JWT 토큰 수집기
- `supabase_client.py` - Supabase 데이터베이스 연동

### ⚙️ 설정 및 로그
- `config.json` - API 키 등 실제 설정 (git 제외)
- `logs/` - 실시간 로그 디렉토리
  - `live_progress.jsonl` - 실시간 진행 로그
  - `collection_data.jsonl` - 수집 매물 데이터 로그  
  - `status.json` - 현재 상태 요약

## 🏗️ 로그 기반 시스템 아키텍처

### 실시간 모니터링 파이프라인
```
1. 수집 실행 (log_based_collector.py)
   ↓ 동별 매물 수집
2. 실시간 로깅 (log_based_logger.py)  
   ↓ JSON 로그 실시간 기록
3. 다층 모니터링
   ├─ 웹 대시보드 (simple_monitor.py:8000)
   └─ CLI 도구 (check_collection_status.py)
4. 데이터 저장 (Supabase)
   └─ 매물 정보, 수집 통계, 실행 기록
```

### 실제 운영 환경
- **수집 서버**: AWS EC2 (ubuntu@인스턴스)
- **데이터베이스**: Supabase PostgreSQL  
- **모니터링**: 로그 파일 + 웹/CLI 인터페이스
- **검증 완료**: 강남구 14개 동, 580개 매물 실제 수집

## 💾 데이터 저장 전략

### Supabase 테이블 구조
```sql
-- 지역 마스터 정보
areas (cortar_no, gu_name, dong_name, boundary_points)

-- 매물 핵심 정보 (일별 업데이트)
properties (article_no, price, area, address, lat/lon)

-- 일별 통계 (대시보드용)
daily_stats (date, total_count, avg_price, changes)

-- 가격 변동 이력
price_history (article_no, price, change_date)
```

### 저장 용량 예상
- **일일**: 300,000개 매물 × 500 bytes = 150MB
- **월간**: 4.5GB (Supabase) + 4.5GB (GCS 압축)
- **비용**: 월 $5-30 (규모에 따라)

## 🚀 실제 사용법 (완성된 기능)

### 1. 메인 수집기 실행
```bash
# 강남구 전체 수집 (단일 프로세스)
python3 log_based_collector.py --single

# 강남구 전체 수집 (멀티프로세스)
python3 log_based_collector.py --parallel

# 특정 동만 수집
python3 log_based_collector.py --dong 역삼동
```

### 2. 실시간 모니터링 (웹 대시보드)
```bash
# 모니터링 서버 시작 (백그라운드)
python3 simple_monitor.py &

# 브라우저에서 확인 
open http://localhost:8000

# 또는 원격 서버에서
python3 simple_monitor.py --host 0.0.0.0 --port 8000
```

### 3. CLI 상태 확인
```bash
# 빠른 상태 확인
python3 check_collection_status.py --quick

# 상세 진행 상황
python3 check_collection_status.py --detailed

# 실시간 모니터링 모드
python3 check_collection_status.py --realtime

# DB 저장 상태 확인
python3 check_collection_status.py --db-status
```

## 📋 검증 완료된 주요 기능

### 실제 수집 엔진 (✅ 완성)
- ✅ **JWT 토큰 자동 수집**: Playwright 기반 토큰 캐싱
- ✅ **실제 네이버 API 연동**: 진짜 매물 데이터 수집 
- ✅ **동별 병렬/순차 수집**: 멀티프로세스 지원
- ✅ **안전한 오류 처리**: 개별 동 실패시에도 전체 진행 계속
- ✅ **Supabase 실시간 저장**: 매물 정보 즉시 DB 저장

### 실시간 모니터링 (✅ 완성)  
- ✅ **JSON 로그 시스템**: 모든 진행상황 실시간 로깅
- ✅ **웹 대시보드**: 브라우저에서 실시간 상태 확인
- ✅ **CLI 모니터링 도구**: 터미널에서 빠른 상태 점검
- ✅ **다층 모니터링**: 로그/웹/CLI 3가지 방법 제공
- ✅ **API 엔드포인트**: REST API로 상태 조회 가능

### 실제 운영 성과 (✅ 검증 완료)
- ✅ **강남구 14개 동 수집**: 모든 동 100% 성공
- ✅ **580개 매물 확인**: 실제 매물 데이터 수집 검증  
- ✅ **EC2 배포 완료**: AWS EC2에서 실제 운영
- ✅ **안정성 확인**: 오류 없이 전체 수집 완료
- ✅ **모니터링 검증**: 웹/CLI 모니터링 정상 작동

## ⚙️ 환경 설정

### 카카오 API 키 설정
1. https://developers.kakao.com 에서 REST API 키 발급
2. `python setup_deployment.py` 실행하여 설정
3. 또는 `config.json`에서 직접 수정

### Supabase 설정
1. https://supabase.com 에서 프로젝트 생성
2. 환경변수 설정:
```bash
export SUPABASE_URL="your-project-url"
export SUPABASE_KEY="your-anon-key"
```

### Google Cloud 설정
1. GCS 버킷 생성 (백업용)
2. 서비스 계정 키 다운로드
3. 환경변수 설정:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
```

## 🚀 실제 운영 가이드 (검증 완료)

### 완전 자동화된 수집 프로세스
```bash
# 1. 메인 수집기 실행 (모든 과정 자동)
python3 log_based_collector.py --single

# 2. 실시간 모니터링 (별도 터미널)
python3 simple_monitor.py &

# 3. CLI로 진행상황 확인 (언제든지)
python3 check_collection_status.py --quick
```

### 실시간 로그 기반 데이터 흐름 (완성)
```
실제 네이버 API → 토큰 인증 → 매물 수집
                     ↓
            ┌─────────────────┐
            │  실시간 로깅    │ ← JSON 로그 (live_progress.jsonl)
            └─────────────────┘
                     ↓
        ┌─────────────┴─────────────┐
        │                           │
   웹 대시보드 ← 로그 파일 → CLI 모니터링
   (실시간)                    (즉시 확인)
        │                           │
        └───────── Supabase ────────┘
              (매물 정보 저장)
```

### EC2 실제 운영 명령어
```bash
# SSH로 EC2 접속
ssh -i "key.pem" ubuntu@<EC2-IP>

# 수집 실행 (백그라운드)
cd /home/ubuntu/naver_land/collectors
nohup python3 log_based_collector.py --single > collection.log 2>&1 &

# 모니터링 서버 실행
nohup python3 simple_monitor.py --host 0.0.0.0 > monitor.log 2>&1 &

# 상태 확인
python3 check_collection_status.py --quick
```

## 📊 검증된 운영 방법론

### 로그 기반 모니터링 방법론 (✅ 완성)
- **실시간 투명성**: 모든 진행 상황을 JSON 로그로 실시간 기록
- **DB 부하 최소화**: 시작/완료만 DB 업데이트, 상세 진행은 로그 파일
- **다층 모니터링**: 웹 대시보드, CLI 도구, 직접 로그 파일 확인
- **검증 완료**: 강남구 14개 동 수집에서 100% 안정적 동작

### 실시간 웹 대시보드 운영 (✅ 완성)
- **웹 기반 접근성**: 브라우저에서 언제든 실시간 상태 확인
- **REST API 제공**: 프로그래매틱 상태 조회 지원  
- **모바일 지원**: 반응형 웹 인터페이스
- **검증 완료**: simple_monitor.py로 실제 운영 중

### CLI 자동화 도구 활용 (✅ 완성)
- **즉시 상태 확인**: check_collection_status.py로 빠른 점검
- **스크립트 친화적**: 자동화 스크립트와 연동 가능
- **다양한 모드**: quick, detailed, realtime, db-status 모드 지원
- **검증 완료**: EC2 환경에서 실제 운영 도구로 활용

### 실제 운영에서 검증된 안정성
- **오류 격리**: 개별 동 실패시에도 전체 프로세스 계속 진행
- **완전 자동화**: 토큰 수집부터 DB 저장까지 수동 개입 불필요
- **실시간 피드백**: 로그를 통한 즉시 문제 파악 및 대응
- **성과 검증**: 580개 매물 실제 수집으로 시스템 안정성 확인