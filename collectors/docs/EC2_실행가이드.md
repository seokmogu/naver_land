# EC2 안전한 수집기 실행 가이드

## 🚀 배포 및 실행 순서

### 1단계: 로컬에서 EC2 배포

```bash
# 스크립트 실행 권한 부여
chmod +x *.sh

# EC2에 배포
./deploy.sh
```

### 2단계: EC2에서 안전 테스트

```bash
# EC2 접속
ssh naver-ec2

# 작업 디렉토리 이동
cd /home/ubuntu/naver_land/collectors

# 종합 안전 테스트 실행
./ec2_safe_test.sh
```

### 3단계: 단계별 수동 테스트

#### A. 데이터베이스 상태 확인
```bash
python3 emergency_recovery.py
```

#### B. 테스트 모드 수집 (DB 저장 안함)
```bash
python3 final_safe_collector.py 1168010100 --test --max-pages 2
```

#### C. 실제 안전 수집 (소규모)
```bash
python3 final_safe_collector.py 1168010100 --max-pages 2
```

#### D. 안전성 재확인
```bash
python3 emergency_recovery.py
```

## 📊 예상 결과

### 정상 작동시 출력
```
🛡️ 최종 안전한 수집기 v1.1
🎯 지역: 1168010100, 페이지: 2
💾 DB 저장: True, 테스트: False
⚠️ 기존 매물 삭제 절대 없음!

✅ Supabase 연결 성공
✅ DB 상태 확인: 테이블 접근 가능

🔄 1단계: 안전한 데이터 수집...
✅ 수집 완료: 50개 매물

🔄 2단계: DB 형식 변환...
✅ 변환 완료: 50개 매물

📊 데이터 품질: A (우수) (92.3%)
   📍 주소 완성도: 94.5%
   🌍 좌표 완성도: 91.2%
   📝 데이터 무결성: 91.2%

🔒 안전성 검증 통과: DB 접근 가능

🔄 3단계: 안전한 DB 저장...
🔒 안전 저장 모드: 50개 매물 처리
💾 저장 결과: 신규 2개, 업데이트 48개, 오류 0개
✅ 기존 매물 삭제 절대 안함 (최고 안전 모드)
✅ 일일 통계 저장 완료

🎯 최종 결과: success
📊 수집 개수: 50개
📈 품질 점수: 92.3% (A (우수))
💾 저장 통계: 신규 2개, 업데이트 48개, 오류 0개
🛡️ 안전성: 기존 매물 삭제 절대 없음
```

## 🔒 안전성 보장 요소

### 1. 삭제 로직 완전 제거
- 기존 매물 절대 삭제하지 않음
- is_active 필드 변경하지 않음
- last_seen_date만 업데이트

### 2. 다중 안전성 검증
- DB 연결 상태 확인
- 데이터 품질 검증 (50% 미만시 중단)
- 최종 안전성 검증

### 3. 오류 처리
- 각 단계별 예외 처리
- 상세한 오류 메시지
- 안전한 종료

## ⚠️ 주의사항

### 현재 85,107개 매물 보호
```bash
# 사전/사후 매물 수 확인
python3 -c "
from supabase_client import SupabaseHelper
helper = SupabaseHelper()
count = helper.client.table('properties').select('article_no', count='exact').eq('is_active', True).execute()
print(f'현재 활성 매물: {count.count}개')
"
```

### 테스트 지역 코드
- `1168010100`: 강남구 신사동 (테스트 추천)
- `1168010500`: 강남구 삼성동
- `1168010800`: 강남구 논현동

## 🔧 문제해결

### 연결 오류시
```bash
# config.json 확인
cat config.json

# Python 패키지 확인
python3 -c "import supabase, requests, json"
```

### 품질 낮음시
```bash
# 최대 페이지 수 증가
python3 final_safe_collector.py 1168010100 --max-pages 5
```

### 권한 오류시
```bash
chmod +x *.sh *.py
```

## 📈 다음 단계

1. **정기 수집 설정**
   ```bash
   # crontab 설정
   crontab -e
   # 매일 새벽 2시 실행
   0 2 * * * cd /home/ubuntu/naver_land/collectors && python3 final_safe_collector.py 1168010100
   ```

2. **모니터링 시스템**
   - 로그 파일 모니터링
   - 품질 점수 추적
   - 오류 알림

3. **백업 시스템**
   - daily_stats 테이블 활용
   - JSON 파일 백업
   - DB 정기 백업

## 🎯 성공 기준

- ✅ 85,107개 매물 유지
- ✅ 품질 점수 90% 이상 (A급)
- ✅ 오류 없는 안전한 저장
- ✅ 삭제 로직 완전 비활성화