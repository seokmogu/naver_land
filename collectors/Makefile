# 네이버 부동산 수집기 - 개발자 경험 최적화
.PHONY: help init status clean reset dev test run

# 기본 명령어
help:
	@echo "🛠️  네이버 부동산 수집기 - 개발 명령어"
	@echo "========================================"
	@echo ""
	@echo "📋 기본 명령어:"
	@echo "  make init      : 개발 환경 초기 설정"
	@echo "  make status    : 프로젝트 상태 확인"
	@echo "  make clean     : 불필요한 파일 정리"
	@echo "  make reset     : 프로젝트 구조 리셋"
	@echo ""
	@echo "⚡ 개발 워크플로우:"
	@echo "  make dev       : 개발 세션 시작"
	@echo "  make test      : 환경 테스트"
	@echo "  make run       : 수집기 실행"
	@echo "  make monitor   : 실시간 모니터링"
	@echo ""
	@echo "🔧 유지보수:"
	@echo "  make commit    : 스마트 커밋"
	@echo "  make archive   : 오래된 파일 아카이브"

# 개발 환경 설정
init:
	@echo "🚀 개발 환경 초기화..."
	@./.claude/commands/dx-init.sh

# 프로젝트 상태 확인
status:
	@./.claude/commands/dx-status.sh

# 정리 작업
clean:
	@echo "🧹 프로젝트 정리 중..."
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.log" -size +10M -delete 2>/dev/null || true
	@echo "✅ 정리 완료"

# 프로젝트 리셋
reset:
	@./.claude/commands/dx-reset.sh

# 개발 워크플로우
dev:
	@./.claude/commands/dx-dev.sh start

test:
	@python test_setup.py

run:
	@echo "🚀 네이버 부동산 수집기 실행..."
	@python enhanced_data_collector.py

monitor:
	@./.claude/commands/dx-dev.sh monitor

# Git 관련
commit:
	@./.claude/commands/dx-dev.sh commit

# 아카이브
archive:
	@./.claude/commands/dx-cleanup.sh

# 가상환경 설정
venv:
	@echo "🐍 Python 가상환경 설정..."
	@python3 -m venv venv
	@echo "✅ 가상환경 생성 완료"
	@echo "💡 실행: source venv/bin/activate"

# 의존성 설치
deps:
	@echo "📦 의존성 패키지 설치..."
	@pip install -r requirements.txt
	@echo "✅ 설치 완료"

# 문서 생성 (요청시에만)
docs:
	@echo "📚 개발 문서 생성..."
	@echo "# 네이버 부동산 수집기" > DEVELOPMENT.md
	@echo "## 빠른 시작" >> DEVELOPMENT.md
	@echo "\`\`\`bash" >> DEVELOPMENT.md
	@echo "make init  # 환경 설정" >> DEVELOPMENT.md
	@echo "make run   # 수집기 실행" >> DEVELOPMENT.md
	@echo "\`\`\`" >> DEVELOPMENT.md
	@echo "✅ DEVELOPMENT.md 생성 완료"

# 전체 설정
setup: venv deps init
	@echo "🎉 전체 설정 완료!"
	@echo "💡 다음 단계: make dev