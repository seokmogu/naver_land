#!/usr/bin/env python3
"""
Database Schema Diagnostic Tool
Identifies missing columns causing the Kakao integration failure
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def diagnose_database_schema():
    """Check current database schema and identify missing columns"""
    
    try:
        # Initialize Supabase client
        supabase: Client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_ANON_KEY")
        )
        
        print("🔍 DATABASE SCHEMA DIAGNOSIS")
        print("=" * 50)
        
        # Expected columns for each table based on the code
        expected_columns = {
            'property_locations': [
                'kakao_road_address', 'kakao_jibun_address', 'kakao_building_name', 
                'kakao_zone_no', 'kakao_api_response', 'address_enriched', 'subway_stations'
            ],
            'property_physical': [
                'floor_description', 'monthly_management_cost', 'heating_type',
                'veranda_count', 'space_type', 'structure_type', 'ground_floor_count',
                'management_office_tel', 'move_in_type', 'move_in_discussion'
            ],
            'property_tax_info': [
                'acquisition_tax_rate', 'registration_tax_rate', 'brokerage_fee_rate'
            ]
        }
        
        # Check each table by trying to query with expected columns
        for table_name, expected_cols in expected_columns.items():
            print(f"\n📊 Checking table: {table_name}")
            print("-" * 30)
            
            try:
                # First check if table exists by doing a simple select
                result = supabase.table(table_name).select("*").limit(1).execute()
                print(f"✅ Table '{table_name}' exists and is accessible")
                
                # Now test each expected column
                missing_columns = []
                existing_columns = []
                
                for col in expected_cols:
                    try:
                        # Try to select just this column
                        test_result = supabase.table(table_name).select(col).limit(1).execute()
                        existing_columns.append(col)
                        print(f"   ✅ Column '{col}' exists")
                    except Exception as col_error:
                        missing_columns.append(col)
                        print(f"   ❌ Column '{col}' MISSING: {str(col_error)}")
                
                if missing_columns:
                    print(f"\n❌ CRITICAL: Missing columns in {table_name}: {', '.join(missing_columns)}")
                else:
                    print(f"\n✅ All expected columns present in {table_name}")
                    
            except Exception as e:
                print(f"❌ Error accessing table {table_name}: {e}")
                # If table doesn't exist, all columns are missing
                print(f"❌ CRITICAL: Table '{table_name}' may not exist or is inaccessible")
        
        print(f"\n🔧 NEXT STEPS:")
        print("1. Execute the complete schema update SQL")
        print("2. Verify all missing columns are added")
        print("3. Test the Kakao integration again")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    diagnose_database_schema()