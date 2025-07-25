"""
토큰을 수동으로 입력받아 테스트하는 간단한 버전
"""
import urllib.request
import urllib.parse
import json
from datetime import datetime


def test_api_with_token(token):
    """주어진 토큰으로 API 테스트"""
    
    # API URL과 파라미터
    base_url = "https://new.land.naver.com/api/articles"
    params = {
        "cortarNo": "1168010100",
        "order": "rank", 
        "realEstateType": "SMS",
        "tradeType": "",
        "tag": "::::::::",
        "rentPriceMin": "0",
        "rentPriceMax": "900000000",
        "priceMin": "0",
        "priceMax": "900000000",
        "areaMin": "0",
        "areaMax": "900000000",
        "showArticle": "false",
        "sameAddressGroup": "false",
        "priceType": "RETAIL",
        "page": "1",
        "articleState": ""
    }
    
    # URL 생성
    url = base_url + "?" + urllib.parse.urlencode(params)
    
    # 헤더 설정
    headers = {
        "authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://new.land.naver.com/offices"
    }
    
    # 요청 생성
    req = urllib.request.Request(url, headers=headers)
    
    try:
        # API 호출
        print("API 호출 중...")
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        
        # 결과 출력
        print(f"\n✓ API 호출 성공!")
        print(f"총 매물 수: {len(data.get('articleList', []))}")
        print(f"추가 데이터 여부: {data.get('isMoreData', False)}")
        
        # 첫 번째 매물 정보 출력
        if data.get('articleList'):
            first = data['articleList'][0]
            print(f"\n첫 번째 매물:")
            print(f"  - 매물명: {first.get('articleName')}")
            print(f"  - 거래타입: {first.get('tradeTypeName')}")
            print(f"  - 가격: {first.get('dealOrWarrantPrc')}")
            print(f"  - 월세: {first.get('rentPrc')}")
            print(f"  - 면적: {first.get('area1')}㎡")
            print(f"  - 주소: {first.get('roadAddress', first.get('address'))}")
        
        # 데이터 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_result_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n결과가 {filename}에 저장되었습니다.")
        
        return True
        
    except urllib.error.HTTPError as e:
        print(f"\n✗ HTTP 에러: {e.code}")
        if e.code == 401:
            print("토큰이 유효하지 않거나 만료되었습니다.")
        return False
    except Exception as e:
        print(f"\n✗ 에러: {e}")
        return False


def get_token_from_browser():
    """브라우저에서 토큰을 가져오는 방법 안내"""
    print("\n=== 브라우저에서 토큰 가져오기 ===")
    print("\n1. Chrome에서 https://new.land.naver.com/offices 접속")
    print("2. F12를 눌러 개발자 도구 열기")
    print("3. Network 탭 선택")
    print("4. 페이지 새로고침 (F5)")
    print("5. 'articles' 요청 찾기")
    print("6. Request Headers에서 'authorization: Bearer ...' 찾기")
    print("7. Bearer 다음의 긴 문자열이 토큰입니다.")
    print("\n또는 Console 탭에서 다음 코드 실행:")
    print("-" * 50)
    print("""
// 모든 XHR 요청 모니터링
(function() {
    const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
    XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
        if (header.toLowerCase() === 'authorization' && value.includes('Bearer')) {
            console.log('토큰 발견:', value.substring(7));
            navigator.clipboard.writeText(value.substring(7));
            console.log('클립보드에 복사되었습니다!');
        }
        return originalSetRequestHeader.apply(this, arguments);
    };
    console.log('모니터링 시작. 페이지를 새로고침하세요.');
})();
""")
    print("-" * 50)


if __name__ == "__main__":
    print("=== 네이버 부동산 API 테스트 ===")
    
    # 토큰 가져오기 방법 안내
    get_token_from_browser()
    
    # 토큰 입력받기
    print("\n토큰을 입력하세요 (엔터만 누르면 종료):")
    token = input().strip()
    
    if token:
        test_api_with_token(token)
    else:
        print("종료합니다.")