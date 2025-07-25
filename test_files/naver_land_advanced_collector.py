import time
import json
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import re


class NaverLandAdvancedCollector:
    """네이버 부동산 고급 수집기 - 화면 제어를 통한 확장 수집"""
    
    def __init__(self, headless=False, slow_mode=False):
        self.headless = headless
        self.slow_mode = slow_mode  # True면 동작을 천천히 보여줌
        self.driver = None
        self.wait = None
        self.collected_articles = {}  # 중복 제거용
        self.setup_driver()
        
    def setup_driver(self):
        """드라이버 설정"""
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        else:
            # 화면 크기 설정 (지도가 잘 보이도록)
            options.add_argument('--window-size=1920,1080')
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 로그 레벨 설정
        options.add_argument('--log-level=3')  # 경고만 표시
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
        if not self.headless:
            self.driver.maximize_window()
            
    def slow_action(self, seconds=1):
        """느린 모드일 때 대기"""
        if self.slow_mode:
            time.sleep(seconds)
            
    def go_to_page(self, url=None):
        """페이지 이동"""
        if url is None:
            url = "https://new.land.naver.com/offices"
        
        print(f"페이지 이동: {url}")
        self.driver.get(url)
        time.sleep(3)  # 초기 로딩 대기
        
    def select_region(self, region_name):
        """지역 선택"""
        try:
            print(f"\n지역 선택: {region_name}")
            
            # 지역 버튼 클릭
            region_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.filter_btn"))
            )
            region_btn.click()
            self.slow_action()
            
            # 검색창에 지역명 입력
            search_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.search_input"))
            )
            search_input.clear()
            search_input.send_keys(region_name)
            self.slow_action()
            
            # 검색 결과 클릭
            result = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li.area_item"))
            )
            result.click()
            self.slow_action(2)
            
            return True
            
        except Exception as e:
            print(f"지역 선택 실패: {e}")
            return False
            
    def apply_filters(self, filters):
        """필터 적용"""
        print("\n필터 적용 중...")
        
        try:
            # 필터 버튼 클릭
            filter_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_filter"))
            )
            filter_btn.click()
            self.slow_action()
            
            # 거래 유형 선택
            if 'trade_type' in filters:
                trade_types = {
                    '매매': 'label[for="tradeType1"]',
                    '전세': 'label[for="tradeType2"]',
                    '월세': 'label[for="tradeType3"]'
                }
                for trade in filters['trade_type']:
                    if trade in trade_types:
                        elem = self.driver.find_element(By.CSS_SELECTOR, trade_types[trade])
                        elem.click()
                        self.slow_action(0.5)
                        
            # 가격 범위 설정
            if 'price_min' in filters or 'price_max' in filters:
                # 가격 입력 필드 찾기
                price_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.input_price")
                if len(price_inputs) >= 2:
                    if 'price_min' in filters:
                        price_inputs[0].clear()
                        price_inputs[0].send_keys(str(filters['price_min']))
                    if 'price_max' in filters:
                        price_inputs[1].clear()
                        price_inputs[1].send_keys(str(filters['price_max']))
                    self.slow_action()
                    
            # 면적 범위 설정
            if 'area_min' in filters or 'area_max' in filters:
                area_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input.input_area")
                if len(area_inputs) >= 2:
                    if 'area_min' in filters:
                        area_inputs[0].clear()
                        area_inputs[0].send_keys(str(filters['area_min']))
                    if 'area_max' in filters:
                        area_inputs[1].clear()
                        area_inputs[1].send_keys(str(filters['area_max']))
                    self.slow_action()
                    
            # 적용 버튼 클릭
            apply_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_apply"))
            )
            apply_btn.click()
            self.slow_action(2)
            
            print("필터 적용 완료")
            return True
            
        except Exception as e:
            print(f"필터 적용 실패: {e}")
            return False
            
    def zoom_map(self, zoom_in=True, times=1):
        """지도 줌 인/아웃"""
        try:
            zoom_selector = "button.btn_zoom_in" if zoom_in else "button.btn_zoom_out"
            zoom_btn = self.driver.find_element(By.CSS_SELECTOR, zoom_selector)
            
            for _ in range(times):
                zoom_btn.click()
                self.slow_action(0.5)
                
            print(f"지도 {'확대' if zoom_in else '축소'} {times}회")
            time.sleep(1)
            
        except Exception as e:
            print(f"줌 조작 실패: {e}")
            
    def move_map(self, direction, pixels=300):
        """지도 이동"""
        try:
            # 지도 요소 찾기
            map_element = self.driver.find_element(By.CSS_SELECTOR, "div#map")
            
            actions = ActionChains(self.driver)
            
            # 방향별 이동
            if direction == "up":
                actions.drag_and_drop_by_offset(map_element, 0, pixels)
            elif direction == "down":
                actions.drag_and_drop_by_offset(map_element, 0, -pixels)
            elif direction == "left":
                actions.drag_and_drop_by_offset(map_element, pixels, 0)
            elif direction == "right":
                actions.drag_and_drop_by_offset(map_element, -pixels, 0)
                
            actions.perform()
            self.slow_action(1)
            print(f"지도 {direction} 이동")
            time.sleep(1.5)  # 지도 로딩 대기
            
        except Exception as e:
            print(f"지도 이동 실패: {e}")
            
    def collect_from_current_view(self):
        """현재 화면의 매물 수집"""
        print("\n현재 화면 매물 수집 중...")
        
        try:
            # 매물 목록 버튼 클릭 (있는 경우)
            try:
                list_btn = self.driver.find_element(By.CSS_SELECTOR, "button.btn_list")
                list_btn.click()
                self.slow_action()
            except:
                pass
                
            # 매물 카드 찾기
            articles = self.driver.find_elements(By.CSS_SELECTOR, "div.item_inner")
            
            new_count = 0
            for article in articles:
                try:
                    # 매물 정보 추출
                    article_id = article.get_attribute("data-nclk-value")
                    if not article_id:
                        continue
                        
                    if article_id in self.collected_articles:
                        continue
                        
                    # 상세 정보 추출
                    info = {
                        'id': article_id,
                        'type': article.find_element(By.CSS_SELECTOR, ".type").text,
                        'price': article.find_element(By.CSS_SELECTOR, ".price").text,
                        'info': article.find_element(By.CSS_SELECTOR, ".info_area").text,
                        'address': article.find_element(By.CSS_SELECTOR, ".address").text,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.collected_articles[article_id] = info
                    new_count += 1
                    
                except Exception as e:
                    continue
                    
            print(f"  새로운 매물 {new_count}개 수집 (전체: {len(self.collected_articles)}개)")
            
            # 스크롤로 더 많은 매물 로드
            self.scroll_article_list()
            
        except Exception as e:
            print(f"매물 수집 오류: {e}")
            
    def scroll_article_list(self):
        """매물 목록 스크롤"""
        try:
            # 매물 목록 컨테이너 찾기
            list_container = self.driver.find_element(By.CSS_SELECTOR, "div.list_contents")
            
            # 스크롤 3회
            for i in range(3):
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight", 
                    list_container
                )
                time.sleep(1)
                
                # 새로운 매물 로드 대기
                self.collect_from_current_view()
                
        except:
            pass
            
    def explore_area_systematically(self, zoom_level=16):
        """지역을 체계적으로 탐색"""
        print(f"\n체계적 지역 탐색 시작 (줌 레벨: {zoom_level})")
        
        # 시작 위치 저장
        self.collect_from_current_view()
        
        # 격자 패턴으로 이동
        moves = [
            ("right", 400), ("down", 400), ("left", 400), ("left", 400),
            ("up", 400), ("up", 400), ("right", 400), ("right", 400),
            ("right", 400), ("down", 400), ("down", 400), ("down", 400)
        ]
        
        for direction, distance in moves:
            self.move_map(direction, distance)
            self.collect_from_current_view()
            
    def save_results(self, filename_prefix="advanced_collection"):
        """수집 결과 저장"""
        if not self.collected_articles:
            print("저장할 데이터가 없습니다.")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장
        json_file = f"{filename_prefix}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.collected_articles, f, ensure_ascii=False, indent=2)
            
        # CSV 저장
        df = pd.DataFrame(self.collected_articles.values())
        csv_file = f"{filename_prefix}_{timestamp}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        print(f"\n저장 완료:")
        print(f"  - JSON: {json_file}")
        print(f"  - CSV: {csv_file}")
        print(f"  - 총 매물 수: {len(self.collected_articles)}개")
        
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            

def main():
    print("=== 네이버 부동산 고급 수집기 ===")
    print("화면을 제어하여 더 많은 데이터를 수집합니다.\n")
    
    # 수집기 생성 (headless=False로 화면 표시, slow_mode=True로 천천히 동작)
    collector = NaverLandAdvancedCollector(headless=False, slow_mode=True)
    
    try:
        # 1. 페이지 접속
        collector.go_to_page()
        
        # 2. 지역 선택 (옵션)
        # collector.select_region("강남구")
        
        # 3. 필터 적용 (옵션)
        filters = {
            'trade_type': ['매매', '전세'],
            'price_min': 30000,  # 3억
            'price_max': 100000  # 10억
        }
        # collector.apply_filters(filters)
        
        # 4. 지도 조작 예시
        print("\n=== 지도 탐색 시작 ===")
        
        # 줌 아웃해서 넓은 지역 보기
        collector.zoom_map(zoom_in=False, times=2)
        collector.collect_from_current_view()
        
        # 체계적으로 지역 탐색
        collector.explore_area_systematically()
        
        # 5. 결과 저장
        collector.save_results()
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        
    finally:
        input("\n엔터를 누르면 브라우저가 종료됩니다...")
        collector.close()


if __name__ == "__main__":
    main()