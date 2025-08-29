#!/usr/bin/env python3
"""
Run Pipeline Test - Comprehensive NULL data issue debugging
Tests the complete pipeline from API to Database with enhanced processing
"""

import sys
import os
import json
from datetime import datetime, date

# Add collectors path
sys.path.append('/Users/smgu/test_code/naver_land/collectors')

from archived.fixed_naver_collector_v2_optimized import CachedTokenCollector
from db.enhanced_supabase_client import EnhancedSupabaseHelper
from core.enhanced_data_processor import EnhancedDataProcessor

def test_complete_pipeline(cortar_no: str = "1168010100", max_properties: int = 5):
    """Test complete pipeline with enhanced processing"""
    
    print("🚀 Complete Pipeline Test with Enhanced Processing")
    print("=" * 80)
    print(f"📍 Testing cortar_no: {cortar_no}")
    print(f"📊 Max properties: {max_properties}")
    print(f"⏰ Test time: {datetime.now().isoformat()}")
    
    # Phase 1: API Collection
    print("\n🔍 Phase 1: API Collection Test")
    print("-" * 40)
    
    try:
        collector = CachedTokenCollector()
        
        if not collector.ensure_valid_token():
            print("❌ Token acquisition failed")
            return False
        
        print("✅ Token acquired successfully")
        
        # Test article list API
        articles = test_article_list_api(collector, cortar_no, max_properties)
        if not articles:
            print("❌ No articles from API")
            return False
            
        print(f"✅ Got {len(articles)} articles from API")
        
        # Get detailed information for articles
        detailed_articles = []
        for i, article in enumerate(articles):
            article_no = article.get('articleNo')
            if article_no:
                print(f"  📄 Getting details for article {i+1}: {article_no}")
                
                # Get detailed API response
                detail_response = collector.get_article_detail(article_no)
                if detail_response:
                    # Extract useful details
                    useful_details = collector.extract_useful_details(detail_response)
                    
                    # Combine article with details
                    combined = article.copy()
                    combined['상세정보'] = useful_details
                    detailed_articles.append(combined)
                    
                    print(f"    ✅ Details extracted: {len(str(useful_details))} chars")
                else:
                    print(f"    ❌ No details for {article_no}")
                    # Still add article without details
                    detailed_articles.append(article)
        
        print(f"✅ Phase 1 Complete: {len(detailed_articles)} articles with details")
        
    except Exception as e:
        print(f"❌ Phase 1 failed: {e}")
        return False
    
    # Phase 2: Enhanced Data Processing
    print("\n🔧 Phase 2: Enhanced Data Processing")
    print("-" * 40)
    
    try:
        processor = EnhancedDataProcessor()
        processed_properties = []
        
        for i, article in enumerate(detailed_articles):
            print(f"  🔄 Processing article {i+1}: {article.get('articleNo')}")
            
            # Convert API format to expected format
            converted_article = convert_api_format(article)
            
            # Process with enhanced processor
            processed_prop = processor.process_collected_property(converted_article, cortar_no)
            
            if processed_prop:
                processed_properties.append(processed_prop)
                print(f"    ✅ Successfully processed")
                
                # Show sample of extracted data
                if i == 0:  # Show details for first property
                    print(f"    📊 Sample data:")
                    print(f"      - ID: {processed_prop['article_no']}")
                    print(f"      - Name: {processed_prop['article_name']}")
                    print(f"      - Type: {processed_prop['real_estate_type']}")
                    print(f"      - Trade: {processed_prop['trade_type']}")
                    print(f"      - Price: {processed_prop['price']}")
                    print(f"      - Area: {processed_prop['area1']}")
                    print(f"      - Address: {processed_prop.get('address_road', 'N/A')}")
            else:
                print(f"    ❌ Processing failed")
        
        # Show processing statistics
        stats = processor.get_validation_stats()
        print(f"\n📊 Processing Statistics:")
        print(f"  - Total processed: {stats['total_processed']}")
        print(f"  - Successful: {stats['successful_extractions']}")
        print(f"  - Price parsing failures: {stats['price_parsing_failures']}")
        print(f"  - Area parsing failures: {stats['area_parsing_failures']}")
        
        if stats['field_extraction_failures']:
            print(f"  - Field extraction failures:")
            for field, count in stats['field_extraction_failures'].items():
                print(f"    • {field}: {count}")
        
        print(f"✅ Phase 2 Complete: {len(processed_properties)} properties processed")
        
    except Exception as e:
        print(f"❌ Phase 2 failed: {e}")
        return False
    
    # Phase 3: Enhanced Database Insertion
    print("\n💾 Phase 3: Enhanced Database Insertion")
    print("-" * 40)
    
    try:
        enhanced_client = EnhancedSupabaseHelper()
        
        # Use the original detailed articles (not the processed ones)
        # This tests the full enhanced processing pipeline
        result = enhanced_client.save_properties_with_enhanced_processing(
            detailed_articles, cortar_no, debug_mode=True
        )
        
        if result['success']:
            summary = result['summary']
            print(f"✅ Database insertion successful:")
            print(f"  - Raw input: {summary['raw_input']}")
            print(f"  - Successfully processed: {summary['successfully_processed']}")
            print(f"  - Processing failures: {summary['processing_failures']}")
            print(f"  - New properties: {summary['new_properties']}")
            print(f"  - Updated properties: {summary['updated_properties']}")
            print(f"  - Insertion errors: {summary['insertion_errors']}")
            
            if result['processing_errors']:
                print(f"⚠️ Processing errors found:")
                for error in result['processing_errors'][:3]:  # Show first 3
                    print(f"  - {error}")
            
        else:
            print(f"❌ Database insertion failed: {result.get('error')}")
            return False
        
        print(f"✅ Phase 3 Complete")
        
    except Exception as e:
        print(f"❌ Phase 3 failed: {e}")
        return False
    
    # Phase 4: Data Quality Validation
    print("\n📊 Phase 4: Data Quality Validation")
    print("-" * 40)
    
    try:
        quality_report = enhanced_client.validate_data_quality(cortar_no, days_back=1)
        
        if 'error' not in quality_report:
            print(f"📈 Data Quality Report:")
            print(f"  - Total properties: {quality_report['total_properties']}")
            print(f"  - Data quality score: {quality_report['data_quality_score']}%")
            print(f"  - Date range: {quality_report['date_range']}")
            
            # Show NULL analysis for key fields
            null_analysis = quality_report['null_analysis']
            critical_fields = ['article_no', 'article_name', 'real_estate_type', 'price']
            
            print(f"\n📋 Critical Field Analysis:")
            for field in critical_fields:
                if field in null_analysis:
                    analysis = null_analysis[field]
                    print(f"  - {field}: {analysis['null_percentage']}% NULL ({analysis['null_count']}/{quality_report['total_properties']})")
            
            quality_summary = quality_report['summary']
            if quality_summary['excellent']:
                print(f"🎯 Quality Assessment: EXCELLENT (≥95%)")
            elif quality_summary['good']:
                print(f"⚠️ Quality Assessment: GOOD (90-95%)")
            else:
                print(f"❌ Quality Assessment: NEEDS IMPROVEMENT (<90%)")
        else:
            print(f"❌ Quality validation failed: {quality_report['error']}")
        
        print(f"✅ Phase 4 Complete")
        
    except Exception as e:
        print(f"❌ Phase 4 failed: {e}")
        return False
    
    # Summary
    print("\n🎯 PIPELINE TEST SUMMARY")
    print("=" * 80)
    print("✅ All phases completed successfully!")
    print(f"📊 Processed {len(detailed_articles)} articles end-to-end")
    print(f"💾 Database operations completed with enhanced validation")
    print(f"🔍 Data quality analysis completed")
    
    # Save detailed log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"pipeline_test_log_{timestamp}.json"
    
    test_log = {
        'timestamp': timestamp,
        'cortar_no': cortar_no,
        'max_properties': max_properties,
        'phase_1_articles': len(articles),
        'phase_2_processed': len(processed_properties),
        'phase_3_result': result if 'result' in locals() else None,
        'phase_4_quality': quality_report if 'quality_report' in locals() else None
    }
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(test_log, f, ensure_ascii=False, indent=2)
    
    print(f"📝 Detailed log saved: {log_file}")
    
    return True

def test_article_list_api(collector, cortar_no: str, max_count: int):
    """Test article list API"""
    import requests
    
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
        response = requests.get(url, headers=headers, params=params,
                              cookies=collector.cookies, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articleList', [])
            return articles[:max_count]
        else:
            print(f"API failed: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"API error: {e}")
        return []

def convert_api_format(api_article):
    """Convert API format to expected format"""
    return {
        '매물번호': api_article.get('articleNo'),
        '매물명': api_article.get('articleName'),
        '부동산타입': api_article.get('realEstateTypeName'),
        '거래타입': api_article.get('tradeTypeName'),
        '매매가격': api_article.get('dealOrWarrantPrc', ''),
        '월세': api_article.get('rentPrc', ''),
        '전용면적': api_article.get('area1'),
        '공급면적': api_article.get('area2'),
        '층정보': api_article.get('floorInfo'),
        '방향': api_article.get('direction'),
        '주소': api_article.get('address', ''),
        '상세주소': api_article.get('buildingName', ''),
        '등록일': api_article.get('articleConfirmYMD'),
        '태그': api_article.get('tagList', []),
        '설명': api_article.get('articleFeatureDesc', ''),
        '상세정보': api_article.get('상세정보', {})
    }

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test complete data pipeline')
    parser.add_argument('--cortar-no', type=str, default='1168010100',
                       help='Cortar number to test (default: 역삼동)')
    parser.add_argument('--max-properties', type=int, default=5,
                       help='Maximum properties to test (default: 5)')
    
    args = parser.parse_args()
    
    success = test_complete_pipeline(args.cortar_no, args.max_properties)
    
    if success:
        print("\n🎉 Pipeline test completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Pipeline test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()