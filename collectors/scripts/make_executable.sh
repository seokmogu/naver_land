#!/bin/bash
chmod +x *.sh *.py
echo "실행 권한 설정 완료"

# 새로 추가된 파일들도 실행 권한 부여
chmod +x comprehensive_system_test.py
chmod +x run_comprehensive_test.sh

echo "종합 테스트 파일 실행 권한 설정 완료"