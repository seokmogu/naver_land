# AWS EC2 배포 가이드

## 개요
네이버 부동산 데이터 수집기를 AWS EC2에 배포하기 위한 가이드입니다.

## 배포 방법

### 🚀 방법 1: 자동 배포 (권장)
AWS CLI를 사용한 완전 자동화 배포

#### 사전 요구사항
- AWS CLI 설치
- AWS 자격 증명 설정 (`aws configure`)
- jq 설치 (`sudo apt install jq` 또는 `brew install jq`)

#### 자동 배포 실행
```bash
# 스크립트 실행 권한 부여
chmod +x deploy_scripts/*.sh

# 자동 배포 시작 (EC2 생성부터 배포까지 자동)
./deploy_scripts/aws_auto_deploy.sh
```

인스턴스 타입 선택:
- `t2.micro` (무료 티어) - 1GB RAM, 기본 수집 가능
- `t3.small` (권장) - 2GB RAM, 안정적 수집
- `t3.medium` - 4GB RAM, 대량 수집용

#### 자동 배포 완료 후
```bash
# API 키 설정
./deploy_scripts/remote_ec2_commands.sh api

# 테스트 실행
./deploy_scripts/remote_ec2_commands.sh test
```

### 📋 방법 2: 수동 배포
직접 EC2 인스턴스를 생성하여 배포

#### 사전 요구사항
- **권장 OS**: Ubuntu 20.04 또는 22.04 LTS
- **인스턴스 타입**: t3.small 이상 권장 (t2.micro는 무료 티어)
- **스토리지**: 20GB 이상
- **Python**: 3.8 이상
- **보안 그룹**: SSH (포트 22) 허용
- **SSH 키 파일**: `.pem` 파일, 권한 400

## 설치 및 배포

### 1. 스크립트 설정

#### sync_to_ec2.sh 수정
```bash
EC2_HOST="your-ec2-public-ip"  # EC2 퍼블릭 IP
EC2_USER="ubuntu"               # Ubuntu는 ubuntu, Amazon Linux는 ec2-user
EC2_KEY="~/.ssh/your-key.pem"  # PEM 키 파일 경로
```

#### remote_ec2_commands.sh 수정
동일한 설정을 적용합니다.

### 2. 초기 배포

```bash
# 스크립트 실행 권한 부여
chmod +x deploy_scripts/*.sh

# 코드 동기화
./deploy_scripts/sync_to_ec2.sh

# 환경 설정
./deploy_scripts/remote_ec2_commands.sh setup

# API 키 설정
./deploy_scripts/remote_ec2_commands.sh api
```

### 3. 테스트

```bash
# Import 테스트
./deploy_scripts/remote_ec2_commands.sh test-simple

# DB 연결 테스트
./deploy_scripts/remote_ec2_commands.sh test-connection

# 수집 테스트 (1개 워커)
./deploy_scripts/remote_ec2_commands.sh test
```

### 4. 크론 스케줄 설정

```bash
# 매주 월요일 04:00 KST 실행
./deploy_scripts/remote_ec2_commands.sh cron
```

## 주요 명령어

### EC2 관리 명령어
```bash
# EC2 인스턴스 관리
./deploy_scripts/aws_manage_ec2.sh status    # 인스턴스 상태 확인
./deploy_scripts/aws_manage_ec2.sh start     # 인스턴스 시작
./deploy_scripts/aws_manage_ec2.sh stop      # 인스턴스 중지 (비용 절감)
./deploy_scripts/aws_manage_ec2.sh restart   # 인스턴스 재시작
./deploy_scripts/aws_manage_ec2.sh ssh       # SSH 접속
./deploy_scripts/aws_manage_ec2.sh cost      # 예상 비용 계산
./deploy_scripts/aws_manage_ec2.sh monitor   # 실시간 모니터링

# 리소스 정리
./deploy_scripts/aws_cleanup.sh              # 모든 AWS 리소스 삭제
```

### 원격 명령어
| 명령어 | 설명 |
|--------|------|
| `setup` | Python 환경 설정 |
| `api` | Supabase API 키 설정 |
| `test` | 수집 테스트 실행 |
| `status` | 프로젝트 상태 확인 |
| `logs` | 로그 확인 |
| `error-logs` | 에러 로그만 확인 |
| `debug` | 디버그 정보 수집 |
| `shell` | EC2 SSH 접속 |
| `cron` | 크론탭 설정 |
| `results` | 수집 결과 확인 |

## 모니터링

### 상태 확인
```bash
./deploy_scripts/remote_ec2_commands.sh status
```

### 로그 확인
```bash
# 전체 로그
./deploy_scripts/remote_ec2_commands.sh logs

# 에러 로그
./deploy_scripts/remote_ec2_commands.sh error-logs
```

### 시스템 정보
```bash
./deploy_scripts/remote_ec2_commands.sh system-info
```

## 문제 해결

### SSH 연결 실패
1. EC2 인스턴스가 실행 중인지 확인
2. 보안 그룹에서 SSH 포트(22)가 열려있는지 확인
3. PEM 키 파일 권한이 400인지 확인
4. 퍼블릭 IP가 올바른지 확인

### 패키지 설치 오류
```bash
# 패키지 재설치
./deploy_scripts/remote_ec2_commands.sh install-packages
```

### 수집 프로세스 중단
```bash
# 실행 중인 프로세스 종료
./deploy_scripts/remote_ec2_commands.sh kill-processes
```

## 보안 권고사항

1. **SSH 키 관리**
   - PEM 키 파일은 안전한 곳에 보관
   - 절대 Git에 커밋하지 않음

2. **API 키 관리**
   - .env 파일로 관리
   - 환경변수로만 사용

3. **보안 그룹**
   - SSH는 필요한 IP에서만 접근 허용
   - 불필요한 포트는 모두 차단

4. **정기 업데이트**
   ```bash
   # EC2에서 실행
   sudo apt update && sudo apt upgrade -y
   ```

## 💰 비용 최적화

### 무료 티어 활용
- **t2.micro**: 월 750시간 무료 (약 31일)
- **스토리지**: 30GB EBS 무료
- **데이터 전송**: 1GB/월 무료

### 비용 절감 팁
```bash
# 사용하지 않을 때 인스턴스 중지
./deploy_scripts/aws_manage_ec2.sh stop

# 비용 확인
./deploy_scripts/aws_manage_ec2.sh cost

# 완전 삭제 (모든 요금 중지)
./deploy_scripts/aws_cleanup.sh
```

### 인스턴스 타입별 비용 (서울 리전 기준)
- **t2.micro**: 무료 티어 (750시간/월)
- **t3.small**: 시간당 $0.0208 (월 약 $15)
- **t3.medium**: 시간당 $0.0416 (월 약 $30)

> ⚠️ **중요**: 인스턴스를 중지(stop)하면 컴퓨트 비용이 발생하지 않습니다. 종료(terminate)하면 모든 데이터가 삭제됩니다.

## 📊 성능 가이드

### 무료 티어 (t2.micro) 사용 시
- **메모리**: 1GB (Playwright 브라우저 실행에 제한적)
- **권장 설정**: 단일 워커, 작은 배치 사이즈
- **수집 성능**: 시간당 약 100-200개 매물

### 권장 사양 (t3.small) 사용 시
- **메모리**: 2GB (안정적인 브라우저 실행)
- **권장 설정**: 2-3 워커, 중간 배치 사이즈
- **수집 성능**: 시간당 약 500-1000개 매물

## 백업

### 데이터 백업
```bash
# EC2에서 실행
cd ~/naver_land
tar -czf backup_$(date +%Y%m%d).tar.gz collectors/ logs/ results/
```

### S3로 백업 (선택사항)
```bash
# AWS CLI 설치 후
aws s3 cp backup_*.tar.gz s3://your-bucket/backups/
```