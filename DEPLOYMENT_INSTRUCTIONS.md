
🚀 네이버 부동산 수집기 - 스키마 수정 배포 가이드
================================================================

📋 배포해야 할 SQL 파일들:
1. create_missing_tables.sql
2. add_missing_columns.sql
3. create_indexes.sql
4. create_views.sql
5. create_triggers.sql

🎯 배포 방법 1: Supabase Dashboard 사용 (권장)
----------------------------------------------------------------
1. https://supabase.com/dashboard 로그인
2. 프로젝트 선택: eslhavjipwbyvbbknixv
3. SQL Editor 메뉴 선택
4. 위 SQL 파일들을 순서대로 복사-붙여넣기 실행

🎯 배포 방법 2: psql 명령줄 사용
----------------------------------------------------------------
psql 연결 정보가 있다면:
psql -h <host> -d <database> -U <username> -f create_missing_tables.sql
psql -h <host> -d <database> -U <username> -f add_missing_columns.sql
psql -h <host> -d <database> -U <username> -f create_indexes.sql
psql -h <host> -d <database> -U <username> -f create_views.sql
psql -h <host> -d <database> -U <username> -f create_triggers.sql

⚠️ 주의사항:
----------------------------------------------------------------
- 파일 순서대로 실행해야 합니다 (의존성 문제)
- 오류가 발생해도 대부분 "이미 존재함" 오류이므로 무시 가능
- 실행 후 test_schema_deployment.py로 검증 필수

✅ 배포 후 검증:
----------------------------------------------------------------
python test_schema_deployment.py

🎉 성공하면 데이터 수집기 시작:
----------------------------------------------------------------
python enhanced_data_collector.py
