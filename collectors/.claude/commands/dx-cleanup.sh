#!/bin/bash
# DX Cleanup: 개발자 경험 개선을 위한 정리 스크립트

echo "🧹 개발자 경험 개선을 위한 프로젝트 정리 시작..."

# 1. 아카이브 디렉토리 생성
mkdir -p archived/{docs,sql,experiments,backups}

# 2. 분석 문서 아카이브 (root에 있는 MD 파일들)
echo "📚 분석 문서 아카이브 중..."
find .. -maxdepth 1 -name "*.md" -not -name "README.md" -exec mv {} archived/docs/ \;

# 3. SQL 파일 아카이브 (root에 있는 SQL 파일들)
echo "🗃️ SQL 파일 아카이브 중..."
find .. -maxdepth 1 -name "*.sql" -exec mv {} archived/sql/ \;

# 4. 중복 collector 백업 정리
echo "🔄 중복 collector 파일 정리 중..."
find .. -name "*enhanced_data_collector*backup*" -exec mv {} archived/backups/ \;
find .. -name "*enhanced_data_collector*v2*" -exec mv {} archived/backups/ \;
find .. -name "*enhanced_data_collector*null_fixed*" -exec mv {} archived/backups/ \;

# 5. 실험적 Python 파일들 아카이브 (root에 있는)
echo "🧪 실험 파일 아카이브 중..."
find .. -maxdepth 1 -name "test_*.py" -exec mv {} archived/experiments/ \;
find .. -maxdepth 1 -name "debug_*.py" -exec mv {} archived/experiments/ \;
find .. -maxdepth 1 -name "analyze_*.py" -exec mv {} archived/experiments/ \;

echo "✅ 정리 완료!"
echo "📊 정리 결과:"
echo "  - 아카이브된 MD 파일: $(find archived/docs -name "*.md" | wc -l)개"
echo "  - 아카이브된 SQL 파일: $(find archived/sql -name "*.sql" | wc -l)개" 
echo "  - 백업 파일: $(find archived/backups -name "*" -type f | wc -l)개"
echo "  - 실험 파일: $(find archived/experiments -name "*" -type f | wc -l)개"