"""
브라우저에서 네이버 부동산 JWT 토큰을 찾는 방법

1. Chrome 개발자 도구를 이용한 방법:
   - F12를 눌러 개발자 도구 열기
   - Network 탭으로 이동
   - 페이지 새로고침 (F5)
   - 'api/articles' 요청 찾기
   - Request Headers에서 'authorization' 확인

2. Console을 이용한 방법:
   브라우저 콘솔에 다음 코드 입력:
"""

console_script = """
// localStorage에서 토큰 찾기
console.log("=== LocalStorage ===");
for (let key in localStorage) {
    if (localStorage[key].includes("JWT") || 
        localStorage[key].includes("token") || 
        localStorage[key].includes("REALESTATE")) {
        console.log(key + ":", localStorage[key]);
    }
}

// sessionStorage에서 토큰 찾기
console.log("\n=== SessionStorage ===");
for (let key in sessionStorage) {
    if (sessionStorage[key].includes("JWT") || 
        sessionStorage[key].includes("token") || 
        sessionStorage[key].includes("REALESTATE")) {
        console.log(key + ":", sessionStorage[key]);
    }
}

// 모든 쿠키 확인
console.log("\n=== Cookies ===");
document.cookie.split(';').forEach(cookie => {
    console.log(cookie.trim());
});

// XMLHttpRequest 후킹하여 토큰 캡처
(function() {
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
    
    XMLHttpRequest.prototype.open = function(method, url) {
        this._url = url;
        return originalOpen.apply(this, arguments);
    };
    
    XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
        if (header.toLowerCase() === 'authorization') {
            console.log("\n=== Authorization Header Captured ===");
            console.log("URL:", this._url);
            console.log("Authorization:", value);
            
            // JWT 토큰만 추출
            if (value.startsWith('Bearer ')) {
                const token = value.substring(7);
                console.log("JWT Token:", token);
                
                // 클립보드에 복사 (선택사항)
                navigator.clipboard.writeText(token).then(() => {
                    console.log("토큰이 클립보드에 복사되었습니다!");
                });
            }
        }
        return originalSetRequestHeader.apply(this, arguments);
    };
    
    console.log("Authorization 헤더 모니터링 시작... 페이지를 다시 로드하거나 매물을 클릭해보세요.");
})();

// Fetch API 후킹
(function() {
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        const [url, options] = args;
        if (options && options.headers && options.headers.authorization) {
            console.log("\n=== Fetch Authorization Captured ===");
            console.log("URL:", url);
            console.log("Authorization:", options.headers.authorization);
        }
        return originalFetch.apply(this, args);
    };
})();
"""

print("브라우저 콘솔에 다음 스크립트를 붙여넣으세요:")
print("=" * 60)
print(console_script)
print("=" * 60)

# 추가 분석용 스크립트
analysis_script = """
import base64
import json
from datetime import datetime

def analyze_token_generation():
    '''
    네이버 부동산 JWT 토큰 생성 패턴 분석
    
    관찰된 패턴:
    1. 토큰은 페이지 로드 시 자동 생성
    2. Payload: {"id": "REALESTATE", "iat": 발급시간, "exp": 만료시간}
    3. 유효기간: 약 3시간 (10800초)
    4. 알고리즘: HS256 (HMAC SHA256)
    '''
    
    # 토큰 생성 시간 패턴
    # iat (issued at): 현재 시간의 Unix timestamp
    # exp (expiration): iat + 10800 (3시간)
    
    current_time = int(datetime.now().timestamp())
    token_payload = {
        "id": "REALESTATE",
        "iat": current_time,
        "exp": current_time + 10800
    }
    
    print("예상 토큰 Payload:")
    print(json.dumps(token_payload, indent=2))
    
    # 서명에 사용되는 secret key는 서버측에서만 알 수 있음
    # 클라이언트에서는 토큰을 생성할 수 없고, 서버에서 받아와야 함
    
    return token_payload

analyze_token_generation()
"""

# 파일로 저장
with open("browser_console_script.js", "w", encoding="utf-8") as f:
    f.write(console_script)

print("\n스크립트가 'browser_console_script.js' 파일로도 저장되었습니다.")