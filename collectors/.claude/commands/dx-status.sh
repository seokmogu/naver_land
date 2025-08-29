#!/bin/bash
# DX Status: 개발자 경험 상태 체크

echo "📊 네이버 부동산 수집기 프로젝트 상태"
echo "=================================="

# Git 상태
echo "🔄 Git 상태:"
git status --porcelain | wc -l | xargs echo "  변경된 파일 수:"
git status --porcelain | grep "^??" | wc -l | xargs echo "  새 파일 수:"
git status --porcelain | grep "^M" | wc -l | xargs echo "  수정된 파일 수:"
git status --porcelain | grep "^D" | wc -l | xargs echo "  삭제된 파일 수:"

# 파일 현황
echo ""
echo "📁 파일 현황:"
find .. -name "*.md" | wc -l | xargs echo "  MD 파일:"
find .. -name "*.sql" | wc -l | xargs echo "  SQL 파일:"
find .. -name "*enhanced_data_collector*" | wc -l | xargs echo "  Enhanced Collector 버전:"
find . -name "*.py" | wc -l | xargs echo "  Python 파일 (collectors/):"

# 디렉토리 구조
echo ""
echo "🏗️ 주요 디렉토리:"
ls -la | grep "^d" | wc -l | xargs echo "  하위 디렉토리 수:"
if [ -d "core" ]; then echo "  ✅ core/"; else echo "  ❌ core/"; fi
if [ -d "config" ]; then echo "  ✅ config/"; else echo "  ❌ config/"; fi  
if [ -d "monitoring" ]; then echo "  ✅ monitoring/"; else echo "  ❌ monitoring/"; fi
if [ -d "archived" ]; then echo "  ✅ archived/"; else echo "  ❌ archived/"; fi

# 핵심 파일 존재 여부
echo ""
echo "🎯 핵심 파일:"
if [ -f "enhanced_data_collector.py" ]; then
    echo "  ✅ enhanced_data_collector.py ($(wc -l < enhanced_data_collector.py) lines)"
else
    echo "  ❌ enhanced_data_collector.py"
fi

if [ -f "core/collector.py" ]; then
    echo "  ✅ core/collector.py ($(wc -l < core/collector.py) lines)"  
else
    echo "  ❌ core/collector.py"
fi

# 최근 커밋
echo ""
echo "📝 최근 작업:"
git log --oneline -3

echo ""
echo "💡 권장 사항:"
if [ $(find .. -name "*.md" | wc -l) -gt 10 ]; then
    echo "  🧹 분석 문서가 너무 많습니다. dx-cleanup.sh 실행을 권장합니다."
fi

if [ $(git status --porcelain | wc -l) -gt 50 ]; then
    echo "  🔄 변경된 파일이 너무 많습니다. 커밋 또는 스태시를 권장합니다."
fi