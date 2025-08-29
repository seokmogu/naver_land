#!/bin/bash
# DX Reset: 프로젝트를 깔끔한 작업 환경으로 리셋

echo "🔄 프로젝트 리셋 시작..."
echo "⚠️  이 작업은 현재 변경사항을 백업 후 진행합니다."

# 현재 작업 백업
BACKUP_DIR="archived/reset_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "📦 현재 작업 백업 중..."
# Git에서 변경된 파일들 백업
git status --porcelain | grep "^M" | cut -c4- | while read file; do
    if [ -f "$file" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp "$file" "$BACKUP_DIR/$file"
    fi
done

# 새 파일들도 백업
git status --porcelain | grep "^??" | cut -c4- | while read file; do
    if [ -f "$file" ]; then
        mkdir -p "$BACKUP_DIR/$(dirname "$file")"
        cp "$file" "$BACKUP_DIR/$file"
    fi
done

echo "✅ 백업 완료: $BACKUP_DIR"

# 핵심 파일만 남기고 정리
echo "🎯 핵심 구조로 리셋 중..."

# 1. 핵심 디렉토리 구조 정의
CORE_DIRS=("core" "config" "monitoring" "db" "scripts")
KEEP_FILES=("enhanced_data_collector.py" "run.sh" ".env" ".gitignore" "CLAUDE.md")

# 2. 불필요한 파일 정리 (안전하게)
echo "  🧹 임시 파일 정리..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.log" -delete 2>/dev/null || true

# 3. 결과 파일 정리
echo "  📊 결과 파일 정리..."
if [ -d "results" ]; then
    mv results archived/results_$(date +%Y%m%d) 2>/dev/null || true
fi

if [ -d "test_results" ]; then
    mv test_results archived/test_results_$(date +%Y%m%d) 2>/dev/null || true
fi

# 4. Git 상태 확인
echo ""
echo "📝 리셋 후 상태:"
git status --short
echo ""
echo "💡 다음 단계:"
echo "  1. git add . && git commit -m 'DX: 프로젝트 구조 정리' (선택사항)"
echo "  2. dx-init.sh 실행으로 개발 환경 설정"
echo "  3. core/collector.py 기반으로 작업 시작"

echo ""
echo "✅ 리셋 완료!"