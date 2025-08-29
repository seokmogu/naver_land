# 네이버 부동산 DB 정규화 실행 가이드

## 🎯 개요

이 가이드는 현재 50개 컬럼의 단일 `properties` 테이블을 8개의 정규화된 테이블로 전환하는 완전한 실행 프로세스를 제공합니다.

## 📋 완성된 구성요소

### 📄 문서
1. **DATABASE_NORMALIZATION_PROJECT.md** - 전체 프로젝트 계획서
2. **NORMALIZED_SCHEMA_DESIGN.md** - 정규화된 스키마 상세 설계
3. **DB_NORMALIZATION_EXECUTION_GUIDE.md** - 이 실행 가이드

### 🛠️ 스크립트
1. **create_normalized_schema.sql** - 새로운 스키마 생성 SQL
2. **migrate_to_normalized_schema.py** - 데이터 마이그레이션 스크립트
3. **enhanced_data_collector.py** - 8섹션 완전 활용 수집기
4. **validate_normalized_data.py** - 데이터 검증 및 성능 테스트
5. **quick_db_analysis.py** - 현재 DB 구조 분석 도구

## 🚀 실행 단계

### Phase 1: 사전 분석 및 백업

#### 1.1 현재 시스템 분석
```bash
# 현재 데이터베이스 구조 분석
python3 quick_db_analysis.py

# 분석 결과 확인
cat current_db_analysis_*.json
```

#### 1.2 데이터 백업 (중요!)
```sql
-- Supabase 콘솔에서 실행하거나 pg_dump 사용
-- 전체 데이터베이스 백업
pg_dump -h db.project.supabase.co -U postgres database_name > backup_$(date +%Y%m%d).sql

-- 또는 중요 테이블만 백업
pg_dump -h db.project.supabase.co -U postgres -t properties -t areas -t price_history database_name > tables_backup_$(date +%Y%m%d).sql
```

### Phase 2: 새로운 스키마 생성

#### 2.1 정규화된 스키마 생성
```bash
# Supabase SQL Editor에서 실행하거나
psql -h db.project.supabase.co -U postgres -d database_name -f create_normalized_schema.sql

# 또는 Python에서 실행
python3 -c "
from supabase import create_client
import os

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

with open('create_normalized_schema.sql', 'r') as f:
    sql_content = f.read()
    
# SQL 파일을 섹션별로 분리하여 실행
# (전체 파일을 한 번에 실행하면 오류 발생 가능)
print('새로운 스키마 생성을 Supabase 콘솔에서 수동으로 실행하세요.')
"
```

#### 2.2 스키마 생성 확인
```bash
# 새로운 테이블 생성 확인
python3 -c "
from supabase import create_client
import os

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

tables = ['properties_new', 'property_prices', 'property_locations', 'realtors']
for table in tables:
    try:
        result = client.table(table).select('*').limit(1).execute()
        print(f'✅ {table}: 생성됨')
    except:
        print(f'❌ {table}: 생성되지 않음')
"
```

### Phase 3: 데이터 마이그레이션

#### 3.1 마이그레이션 실행 (테스트)
```bash
# 소량 데이터로 테스트 마이그레이션
python3 migrate_to_normalized_schema.py --test-mode --limit 100

# 테스트 결과 확인
cat migration_report_*.json
```

#### 3.2 전체 데이터 마이그레이션
```bash
# 전체 데이터 마이그레이션 (시간 소요: 30분-2시간)
python3 migrate_to_normalized_schema.py

# 마이그레이션 중 모니터링
tail -f migration_report_*.json

# 중단된 경우 재시작
python3 migrate_to_normalized_schema.py --resume-from-backup
```

#### 3.3 마이그레이션 결과 확인
```bash
# 마이그레이션 통계 확인
python3 -c "
from supabase import create_client
import os

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

old_count = client.table('properties').select('*', count='exact').limit(1).execute().count
new_count = client.table('properties_new').select('*', count='exact').limit(1).execute().count

print(f'기존 매물: {old_count:,}개')
print(f'마이그레이션된 매물: {new_count:,}개')
print(f'마이그레이션 비율: {new_count/old_count*100:.1f}%')
"
```

### Phase 4: 데이터 검증

#### 4.1 완전한 검증 실행
```bash
# 전체 검증 프로세스 (20-30분 소요)
python3 validate_normalized_data.py

# 검증 보고서 확인
cat validation_report_*.json
```

#### 4.2 성능 비교 테스트
```bash
# 성능 벤치마크 비교
python3 -c "
import time
from supabase import create_client
import os

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# 기존 시스템 성능
start = time.time()
old_result = client.table('properties').select('*').limit(100).execute()
old_time = time.time() - start

# 새로운 시스템 성능  
start = time.time()
new_result = client.table('properties_new').select('*').limit(100).execute()
new_time = time.time() - start

print(f'기존 시스템: {old_time*1000:.2f}ms')
print(f'새로운 시스템: {new_time*1000:.2f}ms')
print(f'성능 개선: {(old_time-new_time)/old_time*100:.1f}%')
"
```

### Phase 5: 수집 로직 업그레이드

#### 5.1 향상된 수집기 테스트
```bash
# 새로운 8섹션 수집기 테스트
python3 enhanced_data_collector.py

# 실제 매물 번호로 테스트 (예시)
python3 -c "
from enhanced_data_collector import EnhancedNaverCollector

collector = EnhancedNaverCollector()
# 실제 매물 번호 입력 필요
test_article = '2412345678'  # 실제 매물 번호로 교체
result = collector.collect_article_detail_enhanced(test_article)

if result:
    print('✅ 8섹션 데이터 수집 성공')
    collector.save_to_normalized_database(result)
else:
    print('❌ 수집 실패')
"
```

#### 5.2 기존 수집기와 통합
```bash
# 기존 log_based_collector.py 수정하여 새로운 DB 스키마 사용
# collectors/core/ 폴더의 파일들을 정규화된 DB 구조에 맞게 업데이트
```

### Phase 6: 운영 환경 전환

#### 6.1 점진적 전환 (권장)
```bash
# 1단계: 새로운 수집기로 신규 데이터만 정규화된 DB에 저장
# 2단계: 기존 API는 뷰(property_full_info)를 통해 호환성 유지  
# 3단계: 모든 기능이 정상 동작 확인 후 완전 전환

# property_full_info 뷰 사용 예제
python3 -c "
from supabase import create_client
import os

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# 뷰를 통한 조회 (기존 API 호환)
result = client.table('property_full_info').select('*').limit(10).execute()
print(f'뷰를 통한 조회: {len(result.data)}개 레코드')
"
```

#### 6.2 모니터링 시스템 업데이트
```bash
# 기존 모니터링 시스템을 새로운 테이블 구조에 맞게 수정
# collectors/monitoring/ 폴더의 파일들 업데이트

# simple_monitor.py 수정
sed -i 's/properties/properties_new/g' collectors/monitoring/simple_monitor.py
```

## 🔧 문제 해결

### 일반적인 문제

#### 1. 스키마 생성 실패
```sql
-- 권한 문제인 경우
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
GRANT USAGE, CREATE ON SCHEMA public TO your_user;

-- 테이블 이름 충돌인 경우  
DROP TABLE IF EXISTS properties_new CASCADE;
-- 다시 생성 스크립트 실행
```

#### 2. 마이그레이션 중단
```bash
# 백업에서 복구
psql -h db.project.supabase.co -U postgres -d database_name < backup_20250828.sql

# 부분 마이그레이션 재시작
python3 migrate_to_normalized_schema.py --start-from-batch 150
```

#### 3. 성능 문제
```sql
-- 인덱스 재생성
REINDEX INDEX idx_properties_new_article_no;
REINDEX INDEX idx_property_prices_property;

-- 통계 업데이트
ANALYZE properties_new;
ANALYZE property_prices;
ANALYZE property_locations;
```

#### 4. 참조 무결성 오류
```sql
-- 고아 레코드 정리
DELETE FROM property_prices 
WHERE property_id NOT IN (SELECT id FROM properties_new);

DELETE FROM property_locations 
WHERE property_id NOT IN (SELECT id FROM properties_new);
```

### 롤백 계획

#### 긴급 롤백
```sql
-- 1. 새로운 테이블 비활성화
ALTER TABLE properties_new RENAME TO properties_new_backup;
ALTER TABLE property_prices RENAME TO property_prices_backup;

-- 2. 기존 시스템으로 복귀
-- 기존 properties 테이블 사용 계속

-- 3. 수집기 설정 되돌리기
git checkout HEAD~1 collectors/
```

#### 점진적 롤백
```bash
# 1. 신규 데이터 수집 중단
systemctl stop naver-collector

# 2. 기존 시스템으로 트래픽 재라우팅
# API에서 properties 테이블 사용하도록 변경

# 3. 문제 해결 후 재전환
```

## 📊 성과 측정

### 성능 지표
```sql
-- 쿼리 성능 비교
EXPLAIN ANALYZE SELECT * FROM properties WHERE cortar_no = '1168010100';
EXPLAIN ANALYZE SELECT * FROM property_full_info WHERE cortar_no = '1168010100';

-- 저장 공간 비교
SELECT 
    pg_size_pretty(pg_total_relation_size('properties')) as old_size,
    pg_size_pretty(pg_total_relation_size('properties_new')) as new_size;
```

### 데이터 품질 지표
```python
# 데이터 완전성 측정
from supabase import create_client
import os

client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# 가격 정보 완전성
total_properties = client.table('properties_new').select('*', count='exact').execute().count
properties_with_price = client.table('property_prices').select('property_id', count='exact').execute().count

print(f'가격 정보 완전성: {properties_with_price/total_properties*100:.1f}%')

# 위치 정보 완전성  
properties_with_location = client.table('property_locations').select('property_id', count='exact').execute().count
print(f'위치 정보 완전성: {properties_with_location/total_properties*100:.1f}%')
```

## 🎯 성공 기준

### 필수 요구사항 (Pass/Fail)
- ✅ 데이터 손실 없음 (99.9% 이상 마이그레이션)
- ✅ 기존 API 호환성 유지
- ✅ 성능 저하 없음 (기준 이하)
- ✅ 참조 무결성 보장

### 목표 지표
- 🎯 쿼리 성능: 80% 향상
- 🎯 저장 공간: 30% 절약  
- 🎯 데이터 품질: 95% 완전성
- 🎯 개발 효율성: 60% 향상

## 📅 예상 일정

### 총 소요 시간: 3-5일

- **Day 1**: Phase 1-2 (분석, 스키마 생성) - 4시간
- **Day 2**: Phase 3 (데이터 마이그레이션) - 6-8시간  
- **Day 3**: Phase 4 (검증, 테스트) - 4-6시간
- **Day 4**: Phase 5-6 (수집기 업그레이드, 전환) - 6시간
- **Day 5**: 모니터링, 최적화, 문서화 - 4시간

### 크리티컬 패스
1. 데이터 백업 (필수)
2. 스키마 생성 (필수)
3. 데이터 마이그레이션 (필수)
4. 검증 완료 (필수)

## 📞 지원 및 문의

### 문제 발생 시
1. **로그 확인**: `tail -f migration_report_*.json`
2. **백업 복구**: `psql < backup_20250828.sql`
3. **문서 참조**: 이 가이드의 문제 해결 섹션
4. **점진적 롤백**: 단계별로 이전 상태로 복구

### 추가 자료
- DATABASE_NORMALIZATION_PROJECT.md - 프로젝트 전체 개요
- NORMALIZED_SCHEMA_DESIGN.md - 스키마 상세 설계
- validation_report_*.json - 검증 결과 상세
- migration_report_*.json - 마이그레이션 로그

---

**🎉 성공적인 데이터베이스 정규화를 위한 완전한 가이드입니다. 각 단계를 신중하게 실행하여 안전하고 효율적인 전환을 달성하세요!**