#!/bin/bash

# Job 관리 시스템 실행 권한 설정 스크립트

echo "🔧 라이트웨이트 Job 관리 시스템 권한 설정"
echo "============================================="

# 메인 시스템 파일들
chmod +x lightweight_scheduler.py
chmod +x job_dashboard.py  
chmod +x job_cli.py
chmod +x deploy_job_system.sh

# 기존 수집기 파일들  
chmod +x log_based_collector.py
chmod +x simple_monitor.py
chmod +x log_based_logger.py

# 기타 필요한 파일들
if [ -f "supabase_client.py" ]; then
    chmod +x supabase_client.py
fi

if [ -f "fixed_naver_collector_v2_optimized.py" ]; then
    chmod +x fixed_naver_collector_v2_optimized.py
fi

echo "✅ 모든 파일 실행 권한 설정 완료"
echo ""
echo "🚀 빠른 시작:"
echo "   1. python3 job_cli.py setup"
echo "   2. python3 job_cli.py start --daemon"  
echo "   3. python3 job_dashboard.py"
echo ""
echo "📊 브라우저에서 http://localhost:8888 접속"