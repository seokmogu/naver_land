#!/usr/bin/env python3
"""
Data Pipeline Debugging Tool
Traces data flow from API → Parsing → Database to identify NULL data causes
"""

import sys
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import the existing collectors
sys.path.append('/Users/smgu/test_code/naver_land/collectors')
from archived.fixed_naver_collector_v2_optimized import CachedTokenCollector
from db.supabase_client import SupabaseHelper

class DataPipelineDebugger:
    def __init__(self):
        self.debug_log = []
        self.api_responses = {}
        self.parsed_data = {}
        self.db_results = {}
        
    def log_debug(self, phase: str, message: str, data: Optional[Dict] = None):
        """Debug logging with structured data"""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'phase': phase,
            'message': message,
            'data': data
        }
        self.debug_log.append(log_entry)
        print(f"[{timestamp}] {phase}: {message}")
        
    def test_single_property_flow(self, cortar_no: str, max_properties: int = 3):
        """Test complete data flow for a small number of properties"""
        
        print("🔍 Starting Data Pipeline Debug Analysis")
        print("=" * 80)
        
        # Phase 1: API Collection Test
        self.log_debug("PHASE_1", f"Testing API collection for {cortar_no}")
        
        try:
            collector = CachedTokenCollector()
            
            # Ensure valid token
            if not collector.ensure_valid_token():
                self.log_debug("PHASE_1", "❌ Token acquisition failed")
                return False
                
            self.log_debug("PHASE_1", "✅ Token acquired successfully")
            
            # Test basic article list API
            articles = self._test_article_list_api(collector, cortar_no, max_properties)
            if not articles:
                self.log_debug("PHASE_1", "❌ No articles retrieved from API")
                return False
                
            self.log_debug("PHASE_1", f"✅ Retrieved {len(articles)} articles from API")
            
            # Phase 2: Test detailed API responses
            detailed_articles = []
            for i, article in enumerate(articles):
                article_no = article.get('articleNo')
                if article_no:
                    self.log_debug("PHASE_1", f"Testing detailed API for article {article_no}")
                    
                    # Get raw API response
                    raw_detail = self._get_raw_article_detail(collector, article_no)
                    if raw_detail:
                        self.api_responses[article_no] = raw_detail
                        self.log_debug("PHASE_1", f"✅ Raw API response received", {
                            'article_no': article_no,
                            'api_sections': list(raw_detail.keys()),
                            'has_articleDetail': 'articleDetail' in raw_detail,
                            'has_articleAddition': 'articleAddition' in raw_detail,
                            'response_size': len(str(raw_detail))
                        })
                        
                        # Combine basic + detailed data
                        combined_article = article.copy()
                        combined_article['상세정보'] = collector.extract_useful_details(raw_detail)
                        detailed_articles.append(combined_article)
                    else:
                        self.log_debug("PHASE_1", f"❌ No detailed API response for {article_no}")
                        
            if not detailed_articles:
                self.log_debug("PHASE_1", "❌ No detailed articles obtained")
                return False
                
            # Phase 2: Data Parsing Test  
            self.log_debug("PHASE_2", f"Testing data parsing for {len(detailed_articles)} articles")
            
            parsed_properties = []
            for article in detailed_articles:
                article_no = article.get('articleNo', 'UNKNOWN')
                self.log_debug("PHASE_2", f"Parsing article {article_no}")
                
                # Test field extraction
                parsing_result = self._test_field_extraction(article)
                self.parsed_data[article_no] = parsing_result
                
                if parsing_result['success']:
                    parsed_properties.append(parsing_result['property_record'])
                    self.log_debug("PHASE_2", f"✅ Successfully parsed {article_no}", {
                        'extracted_fields': parsing_result['field_count'],
                        'null_fields': parsing_result['null_count'],
                        'price_parsed': parsing_result['price_valid'],
                        'area_parsed': parsing_result['area_valid']
                    })
                else:
                    self.log_debug("PHASE_2", f"❌ Failed to parse {article_no}", {
                        'error': parsing_result['error'],
                        'missing_fields': parsing_result['missing_fields']
                    })
            
            if not parsed_properties:
                self.log_debug("PHASE_2", "❌ No properties successfully parsed")
                return False
                
            # Phase 3: Database Insertion Test
            self.log_debug("PHASE_3", f"Testing database insertion for {len(parsed_properties)} properties")
            
            try:
                helper = SupabaseHelper()
                
                # Test individual insertions to track failures
                for prop in parsed_properties:
                    article_no = prop.get('article_no', 'UNKNOWN')
                    insertion_result = self._test_single_insertion(helper, prop, cortar_no)
                    self.db_results[article_no] = insertion_result
                    
                    if insertion_result['success']:
                        self.log_debug("PHASE_3", f"✅ Successfully inserted {article_no}")
                    else:
                        self.log_debug("PHASE_3", f"❌ Failed to insert {article_no}", {
                            'error': insertion_result['error'],
                            'validation_issues': insertion_result.get('validation_issues', [])
                        })
                        
            except Exception as e:
                self.log_debug("PHASE_3", f"❌ Database connection failed: {e}")
                return False
                
            # Generate comprehensive report
            self._generate_debug_report()
            return True
            
        except Exception as e:
            self.log_debug("FATAL", f"Pipeline test failed: {e}")
            return False
    
    def _test_article_list_api(self, collector, cortar_no: str, max_count: int) -> List[Dict]:
        """Test basic article list API"""
        url = "https://new.land.naver.com/api/articles"
        headers = collector.setup_headers()
        
        params = {
            'cortarNo': cortar_no,
            'order': 'rank',
            'realEstateType': 'SG:SMS:GJCG:APTHGJ:GM:TJ',
            'tradeType': '',
            'tag': '::::::::',
            'rentPriceMin': '0',
            'rentPriceMax': '900000000',
            'priceMin': '0', 
            'priceMax': '900000000',
            'areaMin': '0',
            'areaMax': '900000000',
            'oldBuildYears': '',
            'recentlyBuildYears': '',
            'minHouseHoldCount': '',
            'maxHouseHoldCount': '',
            'showArticle': 'false',
            'sameAddressGroup': 'false',
            'minMaintenanceCost': '',
            'maxMaintenanceCost': '',
            'priceType': 'RETAIL',
            'directions': '',
            'articleState': '',
            'page': 1
        }
        
        try:
            import requests
            response = requests.get(url, headers=headers, params=params, 
                                  cookies=collector.cookies, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articleList', [])
                return articles[:max_count]  # Limit for debugging
            else:
                self.log_debug("PHASE_1", f"Article list API failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_debug("PHASE_1", f"Article list API error: {e}")
            return []
    
    def _get_raw_article_detail(self, collector, article_no: str) -> Optional[Dict]:
        """Get raw article detail response for inspection"""
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        headers = collector.setup_headers()
        params = {'complexNo': ''}
        
        try:
            import requests
            time.sleep(1)  # Rate limiting
            response = requests.get(url, headers=headers, params=params,
                                  cookies=collector.cookies, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log_debug("PHASE_1", f"Detail API failed for {article_no}: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_debug("PHASE_1", f"Detail API error for {article_no}: {e}")
            return None
    
    def _test_field_extraction(self, article: Dict) -> Dict:
        """Test field extraction and identify parsing issues"""
        result = {
            'success': False,
            'property_record': None,
            'field_count': 0,
            'null_count': 0,
            'missing_fields': [],
            'error': None,
            'price_valid': False,
            'area_valid': False
        }
        
        try:
            # Test basic field extraction
            basic_fields = {
                '매물번호': article.get('articleNo'),
                '매물명': article.get('articleName'),
                '부동산타입': article.get('realEstateTypeName'),
                '거래타입': article.get('tradeTypeName'),
                '매매가격': article.get('dealOrWarrantPrc', ''),
                '월세': article.get('rentPrc', ''),
                '전용면적': article.get('area1'),
                '공급면적': article.get('area2'),
                '층정보': article.get('floorInfo'),
                '방향': article.get('direction'),
                '주소': article.get('address', ''),
                '상세주소': article.get('buildingName', ''),
                '등록일': article.get('articleConfirmYMD'),
                '태그': article.get('tagList', []),
                '설명': article.get('articleFeatureDesc', '')
            }
            
            # Check field extraction success
            for field_name, value in basic_fields.items():
                if value is not None and value != '':
                    result['field_count'] += 1
                else:
                    result['null_count'] += 1
                    result['missing_fields'].append(field_name)
            
            # Test price parsing
            price_str = basic_fields.get('매매가격', '')
            if price_str:
                try:
                    # Simulate SupabaseHelper._parse_price logic
                    if isinstance(price_str, (int, float)):
                        result['price_valid'] = True
                    elif isinstance(price_str, str):
                        cleaned_price = price_str.replace(',', '').replace('억', '0000').replace('만', '')
                        if cleaned_price.isdigit():
                            result['price_valid'] = True
                except:
                    pass
            
            # Test area parsing  
            area_str = basic_fields.get('전용면적', '')
            if area_str:
                try:
                    if isinstance(area_str, (int, float)):
                        result['area_valid'] = True
                    elif isinstance(area_str, str):
                        cleaned_area = area_str.replace('㎡', '').strip()
                        float(cleaned_area)
                        result['area_valid'] = True
                except:
                    pass
            
            # Create property record using actual supabase logic
            from datetime import date
            helper = SupabaseHelper()
            property_record = helper._prepare_property_record(
                {key.replace('매물번호', 'articleNo').replace('매물명', 'articleName'): value 
                 for key, value in basic_fields.items()},
                "1168010100",  # dummy cortar_no
                date.today()
            )
            
            result['property_record'] = property_record
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _test_single_insertion(self, helper: SupabaseHelper, property_record: Dict, 
                             cortar_no: str) -> Dict:
        """Test single property insertion"""
        result = {
            'success': False,
            'error': None,
            'validation_issues': []
        }
        
        try:
            # Validate required fields
            required_fields = ['article_no', 'cortar_no', 'article_name']
            for field in required_fields:
                if not property_record.get(field):
                    result['validation_issues'].append(f"Missing {field}")
            
            if result['validation_issues']:
                result['error'] = "Validation failed"
                return result
            
            # Attempt insertion
            helper.client.table('properties').upsert(property_record).execute()
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            
        return result
    
    def _generate_debug_report(self):
        """Generate comprehensive debugging report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"debug_pipeline_report_{timestamp}.json"
        
        report = {
            'summary': {
                'total_articles_tested': len(self.api_responses),
                'api_success_count': len([r for r in self.api_responses.values() if r]),
                'parsing_success_count': len([r for r in self.parsed_data.values() if r.get('success')]),
                'db_success_count': len([r for r in self.db_results.values() if r.get('success')])
            },
            'api_responses': self.api_responses,
            'parsed_data': self.parsed_data,
            'db_results': self.db_results,
            'debug_log': self.debug_log
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n📊 Debug report saved: {report_file}")
        print("\n🎯 SUMMARY:")
        print(f"  Articles tested: {report['summary']['total_articles_tested']}")
        print(f"  API success: {report['summary']['api_success_count']}")
        print(f"  Parsing success: {report['summary']['parsing_success_count']}")
        print(f"  DB success: {report['summary']['db_success_count']}")
        
        # Identify failure patterns
        parsing_failures = [k for k, v in self.parsed_data.items() if not v.get('success')]
        db_failures = [k for k, v in self.db_results.items() if not v.get('success')]
        
        if parsing_failures:
            print(f"\n❌ Parsing failures: {len(parsing_failures)} articles")
            for article_no in parsing_failures:
                error = self.parsed_data[article_no].get('error', 'Unknown')
                print(f"  - {article_no}: {error}")
        
        if db_failures:
            print(f"\n❌ Database failures: {len(db_failures)} articles")
            for article_no in db_failures:
                error = self.db_results[article_no].get('error', 'Unknown')
                print(f"  - {article_no}: {error}")

def main():
    """Run pipeline debugging"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug data pipeline for NULL data issues')
    parser.add_argument('--cortar-no', type=str, default='1168010100',
                       help='Cortar number to test (default: 역삼동)')
    parser.add_argument('--max-properties', type=int, default=3,
                       help='Maximum properties to test (default: 3)')
    
    args = parser.parse_args()
    
    debugger = DataPipelineDebugger()
    success = debugger.test_single_property_flow(args.cortar_no, args.max_properties)
    
    if success:
        print("\n✅ Pipeline debugging completed successfully")
    else:
        print("\n❌ Pipeline debugging failed")
        sys.exit(1)

if __name__ == "__main__":
    main()