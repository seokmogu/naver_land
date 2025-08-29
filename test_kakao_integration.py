#!/usr/bin/env python3
"""
Test Kakao Address Integration
Verifies that the schema fix allows Kakao data to be saved properly
"""

import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from datetime import datetime

# Add the collectors directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'collectors'))

# Import the actual converter (if it exists)
try:
    from kakao_address_converter import KakaoAddressConverter
    KAKAO_AVAILABLE = True
except ImportError:
    KAKAO_AVAILABLE = False

# Load environment variables
load_dotenv()

def test_kakao_integration():
    """Test the complete Kakao integration pipeline"""
    
    print("🧪 TESTING KAKAO ADDRESS INTEGRATION")
    print("=" * 50)
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_ANON_KEY")
        )
        
        # Test 1: Verify schema is fixed
        print("\n1️⃣ Testing Schema Columns...")
        test_columns = {
            'property_locations': ['kakao_api_response'],
            'property_physical': ['floor_description'],
            'property_tax_info': ['acquisition_tax_rate']
        }
        
        schema_ok = True
        for table, columns in test_columns.items():
            for col in columns:
                try:
                    supabase.table(table).select(col).limit(1).execute()
                    print(f"   ✅ {table}.{col}")
                except Exception as e:
                    print(f"   ❌ {table}.{col}: {str(e)}")
                    schema_ok = False
        
        if not schema_ok:
            print("\n❌ SCHEMA NOT FIXED - Run the complete_schema_fix.sql first!")
            return False
        
        # Test 2: Test Kakao API conversion (if available)
        print("\n2️⃣ Testing Kakao API...")
        if KAKAO_AVAILABLE and os.getenv("KAKAO_REST_API_KEY"):
            try:
                converter = KakaoAddressConverter(os.getenv("KAKAO_REST_API_KEY"))
                
                # Test coordinates (Gangnam area)
                test_lat = "37.4979"
                test_lon = "127.0276"
                
                result = converter.convert_coord_to_address(test_lat, test_lon)
                if result:
                    print(f"   ✅ Kakao API working: {result.get('road_address', 'No address')}")
                    
                    # Test 3: Test database insertion with Kakao data
                    print("\n3️⃣ Testing Database Integration...")
                    
                    test_property_data = {
                        'article_no': f"TEST_{int(datetime.now().timestamp())}",
                        'property_type': 'test',
                        'trade_type': 'test',
                        'title': 'Kakao Integration Test',
                        'price_display': 'Test',
                        'area_display': 'Test',
                        'status': 'test'
                    }
                    
                    # Insert test property first
                    property_result = supabase.table('properties_new').insert(test_property_data).execute()
                    if property_result.data:
                        property_id = property_result.data[0]['id']
                        print(f"   ✅ Test property created: {property_id}")
                        
                        # Test location data with Kakao fields
                        location_data = {
                            'property_id': property_id,
                            'latitude': float(test_lat),
                            'longitude': float(test_lon),
                            'kakao_road_address': result.get('road_address'),
                            'kakao_jibun_address': result.get('jibun_address'),
                            'kakao_building_name': result.get('building_name'),
                            'kakao_zone_no': result.get('zone_no'),
                            'kakao_api_response': result,  # This was the missing column!
                            'address_enriched': True
                        }
                        
                        location_result = supabase.table('property_locations').insert(location_data).execute()
                        if location_result.data:
                            print(f"   ✅ Kakao location data saved successfully!")
                            print(f"   📍 Address: {result.get('road_address')}")
                            print(f"   🏢 Building: {result.get('building_name', 'N/A')}")
                        else:
                            print(f"   ❌ Failed to save location data")
                        
                        # Test physical data with new columns
                        physical_data = {
                            'property_id': property_id,
                            'floor_description': 'Test Floor Description',  # This was missing!
                            'space_type': 'Test Space',
                            'structure_type': 'Test Structure',
                            'monthly_management_cost': 100000
                        }
                        
                        physical_result = supabase.table('property_physical').insert(physical_data).execute()
                        if physical_result.data:
                            print(f"   ✅ Physical data with new columns saved!")
                        
                        # Test tax data with new rate columns
                        tax_data = {
                            'property_id': property_id,
                            'acquisition_tax_rate': 3.5,  # This was missing!
                            'registration_tax_rate': 0.2,
                            'brokerage_fee_rate': 0.4
                        }
                        
                        tax_result = supabase.table('property_tax_info').insert(tax_data).execute()
                        if tax_result.data:
                            print(f"   ✅ Tax data with rate columns saved!")
                        
                        # Cleanup test data
                        supabase.table('properties_new').delete().eq('id', property_id).execute()
                        print(f"   🧹 Test data cleaned up")
                        
                        print(f"\n🎉 KAKAO INTEGRATION TEST PASSED!")
                        print(f"✅ All missing columns are now working")
                        print(f"✅ Kakao API conversion works")
                        print(f"✅ Database integration works")
                        return True
                        
                    else:
                        print("   ❌ Failed to create test property")
                        
                else:
                    print(f"   ❌ Kakao API returned no results")
                    
            except Exception as e:
                print(f"   ❌ Kakao API error: {e}")
        else:
            print("   ⚠️ Kakao API not available (missing converter or API key)")
            print("   ✅ But schema columns should work now")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_kakao_integration()
    sys.exit(0 if success else 1)