import base64
import json
from datetime import datetime

def decode_jwt(token):
    """JWT 토큰을 디코딩하여 분석"""
    try:
        # JWT는 header.payload.signature 형식
        parts = token.split('.')
        
        if len(parts) != 3:
            print("유효하지 않은 JWT 형식입니다.")
            return
        
        # Base64 디코딩을 위한 패딩 추가 함수
        def add_padding(base64_string):
            missing_padding = len(base64_string) % 4
            if missing_padding:
                base64_string += '=' * (4 - missing_padding)
            return base64_string
        
        # Header 디코딩
        header = json.loads(base64.urlsafe_b64decode(add_padding(parts[0])))
        print("=== JWT Header ===")
        print(json.dumps(header, indent=2, ensure_ascii=False))
        
        # Payload 디코딩
        payload = json.loads(base64.urlsafe_b64decode(add_padding(parts[1])))
        print("\n=== JWT Payload ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        # 시간 정보 해석
        if 'iat' in payload:
            iat_datetime = datetime.fromtimestamp(payload['iat'])
            print(f"\n발급 시간: {iat_datetime}")
        
        if 'exp' in payload:
            exp_datetime = datetime.fromtimestamp(payload['exp'])
            print(f"만료 시간: {exp_datetime}")
            
            # 유효 기간 계산
            if 'iat' in payload:
                duration = payload['exp'] - payload['iat']
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                print(f"유효 기간: {hours}시간 {minutes}분")
        
        print(f"\n서명: {parts[2]}")
        
    except Exception as e:
        print(f"JWT 디코딩 중 오류 발생: {e}")

# 네이버 부동산 JWT 분석
naver_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTMzNDcyMjMsImV4cCI6MTc1MzM1ODAyM30.vUgyFI8PGfUDRl_pzFthR2PxHPNglBoPMQz16kfdAYo"

print("네이버 부동산 JWT 토큰 분석")
print("=" * 50)
decode_jwt(naver_jwt)