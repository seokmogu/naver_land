#!/usr/bin/env python3
"""
배포 환경 설정 도구
config.template.json을 복사하여 config.json 생성 및 API 키 설정
"""

import os
import json
import shutil

def setup_deployment_config():
    """배포 환경 설정"""
    print("🚀 배포 환경 설정")
    print("=" * 50)
    
    config_path = "config.json"
    template_path = "config.template.json"
    
    # 템플릿 파일 확인
    if not os.path.exists(template_path):
        print(f"❌ 템플릿 파일이 없습니다: {template_path}")
        return False
    
    # 기존 설정 파일 확인
    if os.path.exists(config_path):
        print(f"⚠️ 기존 설정 파일이 있습니다: {config_path}")
        choice = input("덮어쓰시겠습니까? (y/n): ").strip().lower()
        if choice != 'y':
            print("설정을 취소했습니다.")
            return False
    
    # 템플릿 복사
    try:
        shutil.copy2(template_path, config_path)
        print(f"✅ 템플릿 복사 완료: {template_path} → {config_path}")
    except Exception as e:
        print(f"❌ 템플릿 복사 실패: {e}")
        return False
    
    # API 키 입력
    api_key = input("\n카카오 REST API 키를 입력하세요: ").strip()
    
    if not api_key:
        print("⚠️ API 키를 입력하지 않았습니다. 나중에 config.json에서 수동으로 설정하세요.")
        return True
    
    # KakaoAK 접두사 제거
    if api_key.startswith("KakaoAK "):
        api_key = api_key[8:]
    
    # 설정 파일 업데이트
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['kakao_api']['rest_api_key'] = api_key
        
        # Supabase 설정도 추가
        print("\n📦 Supabase 설정")
        supabase_url = input("Supabase URL을 입력하세요 (선택사항): ").strip()
        supabase_key = input("Supabase Anon Key를 입력하세요 (선택사항): ").strip()
        
        if supabase_url and supabase_key:
            config['supabase'] = {
                'url': supabase_url,
                'anon_key': supabase_key
            }
            print("✅ Supabase 설정 완료")
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ API 키 설정 완료: {api_key[:10]}...")
        print(f"💾 설정 파일 저장: {config_path}")
        
        # 테스트
        choice = input("\nAPI 키를 테스트하시겠습니까? (y/n): ").strip().lower()
        if choice == 'y':
            test_config()
        
        return True
        
    except Exception as e:
        print(f"❌ 설정 파일 업데이트 실패: {e}")
        return False

def test_config():
    """설정 테스트"""
    print("\n🧪 설정 테스트 중...")
    
    try:
        from kakao_address_converter import KakaoAddressConverter
        
        converter = KakaoAddressConverter()
        
        # 테스트 좌표
        test_lat = "37.498095"
        test_lon = "127.027610"
        
        print(f"테스트 좌표: ({test_lat}, {test_lon})")
        result = converter.convert_coord_to_address(test_lat, test_lon)
        
        if result:
            print("✅ 설정 테스트 성공!")
            print(f"변환된 주소: {result.get('대표주소', 'N/A')}")
        else:
            print("❌ 설정 테스트 실패")
            
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")

def show_deployment_info():
    """배포 정보 안내"""
    print("\n📋 배포 시 주의사항:")
    print("1. config.json은 .gitignore에 포함되어 있어 버전 관리되지 않습니다")
    print("2. 새 환경에서는 setup_deployment.py를 실행하여 설정하세요")
    print("3. 또는 config.template.json을 복사하여 수동으로 config.json을 만드세요")
    print("\n📁 필수 파일 목록:")
    print("- config.template.json (템플릿)")
    print("- config.json (실제 설정, 자동 생성)")
    print("- .gitignore (config.json 제외)")

if __name__ == "__main__":
    success = setup_deployment_config()
    if success:
        show_deployment_info()
    else:
        print("❌ 배포 설정 실패")