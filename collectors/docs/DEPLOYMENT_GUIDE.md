# 🚀 EC2 배포 가이드

네이버 부동산 수집기 개선 사항을 EC2에 안전하게 배포하는 가이드입니다.

## 📋 준비사항

### 1. EC2 접속 정보 확인
```bash
# deploy_to_ec2.sh 파일에서 다음 정보 수정
EC2_HOST="your-ec2-instance.amazonaws.com"
EC2_USER="hackit" 
EC2_PATH="/home/hackit/naver_land"
KEY_PATH="~/.ssh/your-key.pem"
```

### 2. 로컬 개선 파일 확인
다음 파일들이 준비되어 있는지 확인:
- ✅ `emergency_recovery.py` - 응급 데이터 복구
- ✅ `json_to_db_converter.py` - JSON→DB 안전 변환  
- ✅ `enhanced_collector_with_direct_save.py` - 직접 저장 수집기
- ✅ `ec2_emergency_stop.sh` - EC2 응급 중단 스크립트
- ✅ `deploy_to_ec2.sh` - 자동 배포 스크립트

## 🚨 단계별 배포 실행

### Phase 1: 응급 중단 및 배포 준비

```bash
# 1. 배포 스크립트 실행
./deploy_to_ec2.sh
```

**자동 실행되는 작업들**:
1. EC2 연결 테스트
2. EC2에서 응급 중단 실행 (크론탭 비활성화, 프로세스 중단)
3. 현재 코드 백업 생성
4. 개선된 파일들 EC2로 전송
5. 파일 권한 설정

### Phase 2: 응급 복구 실행

EC2에 접속하여 응급 복구 실행:
```bash
# EC2 접속
ssh -i ~/.ssh/your-key.pem hackit@your-ec2-instance.amazonaws.com

# 작업 디렉토리로 이동
cd /home/hackit/naver_land/collectors

# 응급 복구 실행
python3 emergency_recovery.py
```

**예상 결과**:
```
🚨 네이버 부동산 수집기 응급 데이터 복구
==================================================
🔄 응급 복구 시작: 20250827_110000
📅 복구 대상 기간: 2025-08-16 이후
📊 복구 대상: 245개 매물
✅ 복구: 2542368337 - 강남구 역삼동 오피스텔...
...
🎯 복구 완료: 240/245 매물 (98.0% 성공률)
```

### Phase 3: 새로운 수집기 테스트

```bash
# 테스트 모드로 실행 (DB 저장하지 않음)
python3 enhanced_collector_with_direct_save.py 11680102 --max-pages 2 --test

# 정상 작동 확인되면 실제 저장 모드로 실행
python3 enhanced_collector_with_direct_save.py 11680102 --max-pages 5
```

**예상 결과**:
```
🚀 11680102 지역 수집 및 직접 저장 시작
✅ 수집 완료: 45개 매물
✅ 변환 완료: 45개 매물
📊 데이터 품질: A (우수)
💾 저장 결과: 신규 12개, 업데이트 33개, 오류 0개
✅ DB 저장 완료
```

### Phase 4: 정상화 및 자동화

```bash
# 1. 기존 크론탭 복구 (필요시)
crontab /tmp/backup_crontab_*.txt

# 2. 새로운 자동화 설정 (개선된 수집기 사용)
crontab -e

# 예시 크론탭 (30분마다 역삼동 수집)
*/30 * * * * cd /home/hackit/naver_land/collectors && python3 enhanced_collector_with_direct_save.py 11680102 >> /tmp/collector.log 2>&1
```

## ✅ 검증 체크리스트

### 즉시 확인사항
- [ ] EC2에서 json_to_supabase.py 관련 프로세스가 모두 중단됨
- [ ] 응급 복구로 50개 이상 매물이 복구됨
- [ ] 새로운 수집기 테스트가 성공함

### 품질 확인사항  
- [ ] 수집된 매물의 주소 정보가 90% 이상 완전함
- [ ] 위도/경도 좌표가 정확하게 수집됨
- [ ] 기존 매물이 잘못 삭제되지 않음

### 시스템 안정성
- [ ] 메모리 사용량이 정상 범위임
- [ ] 에러 로그가 없거나 최소화됨
- [ ] 5회 이상 연속 성공 실행됨

## 🚨 문제 발생시 롤백

### 즉시 롤백
```bash
# 1. 새 프로세스 중단
pkill -f enhanced_collector
pkill -f emergency_recovery

# 2. 백업에서 원본 복구
BACKUP_DIR="/home/hackit/backups/backup_20250827_*"
cp -r $BACKUP_DIR/collectors/* /home/hackit/naver_land/collectors/

# 3. 원본 크론탭 복구
crontab /tmp/backup_crontab_*.txt
```

### 데이터 롤백
```sql
-- 응급 복구 취소 (필요시)
UPDATE properties 
SET is_active = false, deleted_at = NOW(), recovered_at = NULL
WHERE recovery_reason = 'Emergency recovery - wrong deletion logic';
```

## 📊 성공 지표

### Phase 1 성공 지표
- ✅ 추가 데이터 손실 0건
- ✅ EC2 프로세스 안전 중단
- ✅ 백업 파일 생성 완료

### Phase 2 성공 지표  
- ✅ 50개 이상 매물 복구
- ✅ 복구 성공률 90% 이상
- ✅ 활성 매물 수 정상 증가

### Phase 3 성공 지표
- ✅ 새 수집기 정상 작동
- ✅ 주소 완성도 90% 이상
- ✅ 품질 점수 B등급 이상

### Final 성공 지표
- ✅ 24시간 무중단 운영
- ✅ 데이터 품질 지속 향상
- ✅ 자동화 시스템 정상 작동

## 📞 문제 발생시 대응

### 심각한 문제 (즉시 중단)
- 대량 데이터 손실 감지
- 시스템 오버로드 발생  
- DB 연결 장애

### 경고 수준 (모니터링 강화)
- 품질 점수 70% 미만
- 수집 실패율 10% 초과
- 메모리 사용량 80% 초과

### 정상 범위
- 품질 점수 80% 이상
- 수집 성공률 95% 이상  
- 시스템 리소스 정상

---

## 💡 배포 완료 후 권장사항

1. **모니터링 강화**: 첫 1주일간 일일 품질 체크
2. **점진적 확장**: 역삼동 → 강남구 → 서울 전체
3. **백업 자동화**: 일일 자동 백업 시스템 구축
4. **경고 시스템**: 품질 저하시 자동 알림