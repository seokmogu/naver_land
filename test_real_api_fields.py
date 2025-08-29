#!/usr/bin/env python3
"""
URGENT: Test script to capture real Naver API field names
This will help us fix the wrong field mappings in enhanced_data_collector.py
"""

import json
import time
import sys
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_single_article_response():
    """Test a single article to see actual API field structure"""
    print("🔍 URGENT: Testing Real Naver API Field Names")
    print("="*60)
    
    try:
        # Import the enhanced collector
        from enhanced_data_collector import EnhancedNaverCollector
        
        collector = EnhancedNaverCollector()
        
        # Test with a hardcoded article number from recent successful collection
        # Using article from the result files we saw earlier
        test_article_no = "2546157515"  # From the JSON file we examined
        
        print(f"🧪 Testing article {test_article_no}...")
        print("⏳ Collecting enhanced data (8 sections)...")
        
        # Get the enhanced data which includes all 8 sections
        enhanced_data = collector.collect_article_detail_enhanced(test_article_no)
        
        if enhanced_data and enhanced_data.get('raw_sections'):
            print("✅ Success! Got API response data")
            
            # Save the complete raw response for analysis
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"real_api_response_{test_article_no}_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Complete response saved to: {output_file}")
            
            # Analyze each section
            raw_sections = enhanced_data['raw_sections']
            
            print(f"\n📊 API Response Analysis:")
            print(f"   Top-level keys: {list(raw_sections.keys())}")
            
            # Detailed analysis of each section
            critical_sections = [
                ('articleSpace', 'MOST CRITICAL - Area Information'),
                ('articlePrice', 'CRITICAL - Pricing'),
                ('articleRealtor', 'HIGH - Agent Info'), 
                ('articleFacility', 'MEDIUM - Facilities'),
                ('articleDetail', 'HIGH - Basic Info'),
                ('articleAddition', 'MEDIUM - Additional'),
                ('articleFloor', 'MEDIUM - Floor Info'),
                ('articleTax', 'LOW - Tax Info'),
                ('articlePhotos', 'MEDIUM - Images')
            ]
            
            print(f"\n🔍 Section-by-Section Field Analysis:")
            
            for section_name, priority in critical_sections:
                if section_name in raw_sections:
                    section_data = raw_sections[section_name]
                    print(f"\n📋 {section_name} ({priority}):")
                    
                    if isinstance(section_data, dict):
                        fields = list(section_data.keys())
                        print(f"   Fields ({len(fields)}): {fields}")
                        
                        # Look for area-related fields in articleSpace
                        if section_name == 'articleSpace':
                            print(f"   🎯 AREA FIELDS FOUND:")
                            area_keywords = ['area', 'space', 'size', 'exclusive', 'supply', 'pyeong', 'meter']
                            for key, value in section_data.items():
                                if any(keyword in key.lower() for keyword in area_keywords):
                                    print(f"      ✅ {key} = {value}")
                                elif value and str(value).replace('.','').isdigit():
                                    print(f"      🔢 {key} = {value} (numeric)")
                        
                        # Look for price fields in articlePrice
                        elif section_name == 'articlePrice':
                            print(f"   💰 PRICE FIELDS FOUND:")
                            price_keywords = ['price', 'cost', 'fee', 'rent', 'deal', 'deposit', 'warrant']
                            for key, value in section_data.items():
                                if any(keyword in key.lower() for keyword in price_keywords):
                                    print(f"      ✅ {key} = {value}")
                                elif value and str(value).replace(',','').isdigit():
                                    print(f"      💵 {key} = {value} (numeric)")
                        
                        # Look for facility fields
                        elif section_name == 'articleFacility':
                            print(f"   🏠 FACILITY FIELDS FOUND:")
                            for key, value in section_data.items():
                                if value == 'Y' or value == 'N' or isinstance(value, bool):
                                    print(f"      ✅ {key} = {value}")
                        
                        # Sample a few key-value pairs for other sections
                        else:
                            sample_size = min(5, len(fields))
                            print(f"   📝 Sample fields:")
                            for key in fields[:sample_size]:
                                value = section_data[key]
                                if isinstance(value, str) and len(str(value)) > 50:
                                    value = str(value)[:50] + "..."
                                print(f"      {key} = {value}")
                    
                    elif isinstance(section_data, list):
                        print(f"   Array with {len(section_data)} items")
                        if len(section_data) > 0:
                            if isinstance(section_data[0], dict):
                                print(f"   First item keys: {list(section_data[0].keys())}")
                    
                else:
                    print(f"\n❌ {section_name} - NOT FOUND IN API RESPONSE")
            
            # Generate field mapping corrections
            print(f"\n🔧 RECOMMENDED CORRECTIONS:")
            print("="*50)
            
            if 'articleSpace' in raw_sections:
                space_data = raw_sections['articleSpace']
                print("📐 articleSpace section corrections:")
                print(f"   Available fields: {list(space_data.keys())}")
                print("   ❌ Current wrong mapping: data.get('area1'), data.get('area2')")
                print("   🔧 Fix: Replace with actual field names found above")
            
            if 'articlePrice' in raw_sections:
                price_data = raw_sections['articlePrice'] 
                print("\n💰 articlePrice section corrections:")
                print(f"   Available fields: {list(price_data.keys())}")
                print("   ⚠️  Verify: dealPrice, warrantPrice, rentPrice field names")
            
            return True
            
        else:
            print("❌ Failed to get API response data")
            print("   This could be due to:")
            print("   1. Invalid article number")
            print("   2. Token expired")  
            print("   3. Rate limiting (429 error)")
            print("   4. Article no longer exists")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def test_with_fresh_article():
    """Try to get a fresh article from list and test it"""
    print(f"\n🔄 Trying to get fresh article from list...")
    
    try:
        from enhanced_data_collector import EnhancedNaverCollector
        
        collector = EnhancedNaverCollector()
        
        # Get articles from 역삼동 
        cortar_no = "1168010100"  # 역삼동
        print(f"📋 Getting article list from {cortar_no}...")
        
        articles = collector.collect_single_page_articles(cortar_no, 1)
        
        if articles and len(articles) > 0:
            test_article = articles[0]
            print(f"🎯 Testing fresh article: {test_article}")
            
            enhanced_data = collector.collect_article_detail_enhanced(test_article)
            
            if enhanced_data:
                print("✅ Success with fresh article!")
                
                # Quick analysis
                if enhanced_data.get('raw_sections'):
                    raw_sections = enhanced_data['raw_sections']
                    
                    if 'articleSpace' in raw_sections:
                        space_data = raw_sections['articleSpace']
                        print(f"\n🎯 articleSpace fields: {list(space_data.keys())}")
                        print(f"    Data sample: {dict(list(space_data.items())[:3])}")
                    
                    if 'articlePrice' in raw_sections:
                        price_data = raw_sections['articlePrice']
                        print(f"\n💰 articlePrice fields: {list(price_data.keys())}")
                        print(f"    Data sample: {dict(list(price_data.items())[:3])}")
                
                return enhanced_data
            
        else:
            print("❌ No articles found in list")
    
    except Exception as e:
        print(f"❌ Error getting fresh article: {e}")
    
    return None

if __name__ == "__main__":
    print("🚨 URGENT FIELD MAPPING TEST")
    print("This will identify the correct Naver API field names")
    print("to fix the NULL value issues in enhanced_data_collector.py")
    print("="*60)
    
    # Test 1: Try with known article
    success = test_single_article_response()
    
    # Test 2: If first test failed, try with fresh article
    if not success:
        print("\n🔄 First test failed, trying with fresh article...")
        time.sleep(2)
        test_with_fresh_article()
    
    print("\n✅ Test complete! Check the generated JSON file for detailed analysis.")
    print("📋 Use this data to fix the field mappings in enhanced_data_collector.py")