#!/bin/bash
# DX Init: 개발 환경 초기 설정

echo "🚀 네이버 부동산 수집기 개발 환경 설정"
echo "====================================="

# 1. 환경 변수 확인
echo "🔧 환경 설정 확인 중..."
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "  ✅ .env.template에서 .env 생성"
        echo "  ⚠️  .env 파일을 편집하여 실제 값을 설정해주세요"
    else
        echo "  ❌ .env 파일이 없습니다. 수동으로 생성해주세요"
    fi
else
    echo "  ✅ .env 파일 존재"
fi

# 2. Python 의존성 확인
echo ""
echo "📦 Python 환경 확인 중..."
if [ -f "requirements.txt" ]; then
    echo "  ✅ requirements.txt 존재"
    if command -v pip &> /dev/null; then
        echo "  💿 패키지 설치 중..."
        pip install -r requirements.txt
        echo "  ✅ 패키지 설치 완료"
    else
        echo "  ❌ pip이 설치되지 않았습니다"
    fi
else
    echo "  ❌ requirements.txt가 없습니다"
fi

# 3. 디렉토리 구조 확인 및 생성
echo ""
echo "🏗️ 디렉토리 구조 설정 중..."
REQUIRED_DIRS=("logs" "results" "tokens" "config")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "  📁 $dir/ 생성"
    else
        echo "  ✅ $dir/ 존재"
    fi
done

# 4. Git hooks 설정
echo ""
echo "⚙️ Git hooks 설정 중..."
if [ ! -f ".git/hooks/pre-commit" ]; then
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# 커밋 전 자동 정리
echo "🧹 커밋 전 정리 중..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
EOF
    chmod +x .git/hooks/pre-commit
    echo "  ✅ pre-commit hook 설정 완료"
else
    echo "  ✅ Git hooks 이미 설정됨"
fi

# 5. IDE 설정 (VS Code)
echo ""
echo "💻 VS Code 설정 중..."
mkdir -p .vscode
if [ ! -f ".vscode/settings.json" ]; then
    cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/logs": true,
        "**/results": true,
        "**/archived": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false
}
EOF
    echo "  ✅ VS Code 설정 완료"
else
    echo "  ✅ VS Code 설정 이미 존재"
fi

# 6. 개발용 aliases 설정
echo ""
echo "⚡ 개발 단축키 설정 중..."
cat > .claude/commands/aliases.sh << 'EOF'
# 개발 편의 aliases
alias run-collector="python enhanced_data_collector.py"
alias check-status="./dx-status.sh"
alias clean-logs="rm -f logs/*.log"
alias show-results="ls -la results/"
alias git-clean="git clean -fd"

echo "💡 사용 가능한 명령어:"
echo "  run-collector  : 수집기 실행"
echo "  check-status   : 프로젝트 상태 확인"
echo "  clean-logs     : 로그 파일 정리"
echo "  show-results   : 결과 파일 보기"
EOF

echo "  ✅ 개발 단축키 설정 완료"

# 7. 빠른 테스트 스크립트
echo ""
echo "🧪 테스트 환경 설정 중..."
cat > test_setup.py << 'EOF'
#!/usr/bin/env python3
"""환경 설정 테스트"""
import os
import sys

def test_environment():
    """기본 환경 테스트"""
    print("🧪 환경 설정 테스트")
    print("==================")
    
    # Python 버전
    print(f"Python: {sys.version}")
    
    # 핵심 모듈 import 테스트
    try:
        import requests
        print("✅ requests 모듈")
    except ImportError:
        print("❌ requests 모듈")
    
    try:
        from supabase import create_client
        print("✅ supabase 모듈")
    except ImportError:
        print("❌ supabase 모듈")
    
    # 환경 변수 확인
    if os.path.exists('.env'):
        print("✅ .env 파일")
    else:
        print("❌ .env 파일")
    
    # 디렉토리 확인
    dirs = ['core', 'config', 'logs', 'results']
    for dir_name in dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ 디렉토리")
        else:
            print(f"❌ {dir_name}/ 디렉토리")

if __name__ == "__main__":
    test_environment()
EOF

echo "  ✅ 테스트 스크립트 생성"

echo ""
echo "🎉 개발 환경 설정 완료!"
echo ""
echo "🚀 다음 단계:"
echo "  1. source .claude/commands/aliases.sh (단축키 활성화)"
echo "  2. python test_setup.py (환경 테스트)"
echo "  3. run-collector (수집기 실행)"
echo ""
echo "💡 유용한 명령어:"
echo "  ./dx-status.sh   : 프로젝트 상태 확인"
echo "  ./dx-cleanup.sh  : 불필요한 파일 정리"
echo "  ./dx-reset.sh    : 프로젝트 리셋"