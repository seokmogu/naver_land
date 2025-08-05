# Naver Land Collector

네이버 부동산 매물 데이터를 수집하고 분석하는 도구입니다.

## 주요 기능

- 네이버 부동산 API를 활용한 매물 데이터 수집
- JWT 토큰 자동 획득 (Playwright 사용)
- 좌표 기반 지역별 매물 수집
- 카카오 API를 통한 주소 변환
- Supabase 데이터베이스 연동
- 배치 수집 및 스케줄링 지원

## 프로젝트 구조

```
naver_land/
├── collectors/          # 메인 수집 모듈
│   ├── fixed_naver_collector.py      # 핵심 수집기
│   ├── playwright_token_collector.py # JWT 토큰 수집
│   ├── supabase_client.py           # DB 클라이언트
│   ├── batch_collect_gangnam.py     # 강남구 배치 수집
│   └── ...
├── docs/               # API 문서 및 가이드
├── analyzers/          # 데이터 분석 도구
└── requirements.txt    # 의존성 패키지
```

## 설치 방법

1. 의존성 설치:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. 설정 파일 준비:
```bash
cp collectors/config.template.json collectors/config.json
# config.json에 API 키 입력
```

## 사용법

### 단일 지역 수집
```bash
cd collectors
python fixed_naver_collector.py
```

### 강남구 전체 배치 수집
```bash
cd collectors
python batch_collect_gangnam.py
```

### JWT 토큰 수집
```bash
cd collectors
python playwright_token_collector.py
```

## 설정

`config.json` 파일에 다음 정보를 설정해야 합니다:

- Kakao API Key (주소 변환용)
- Supabase URL 및 Key (DB 연동용)

## 데이터베이스 스키마

Supabase 데이터베이스 스키마는 `collectors/supabase_schema.sql`을 참조하세요.

## 라이선스

이 프로젝트는 개인 학습 및 연구 목적으로만 사용하세요.