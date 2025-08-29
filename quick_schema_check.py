#!/usr/bin/env python3
"""
Quick Database Schema Check
Analyzes current Supabase database state to identify missing elements
"""

import os
import sys
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class SchemaChecker:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
        
        self.headers = {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json'
        }
    
    def check_table_exists(self, table_name):
        """Check if a table exists by attempting to query it"""
        try:
            url = f"{self.supabase_url}/rest/v1/{table_name}"
            params = {'select': 'id', 'limit': 1}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                return True, "EXISTS"
            elif response.status_code == 404:
                return False, "NOT_FOUND"
            else:
                return False, f"ERROR_{response.status_code}"
        except Exception as e:
            return False, f"ERROR: {str(e)}"
    
    def check_table_columns(self, table_name):
        """Get table structure via REST API"""
        try:
            url = f"{self.supabase_url}/rest/v1/{table_name}"
            params = {'select': '*', 'limit': 1}
            
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return True, list(data[0].keys()) if data else []
                else:
                    # Table exists but empty - we can't get column info this way
                    return True, ["table_empty_no_columns_info"]
            else:
                return False, []
        except Exception as e:
            return False, []
    
    def analyze_schema_gaps(self):
        """Analyze current schema and identify gaps"""
        print("🔍 ANALYZING CURRENT SUPABASE SCHEMA STATE")
        print("=" * 60)
        print(f"🕒 Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Critical tables to check
        critical_tables = {
            'realtors': 'Realtor/broker information storage',
            'property_tax_info': 'Property tax calculation data',
            'property_locations': 'Property location and address data',
            'property_physical': 'Physical property characteristics',
            'properties_new': 'Main normalized properties table',
            'property_prices': 'Property pricing information',
            'property_realtors': 'Property-realtor relationship mapping'
        }
        
        # Check each critical table
        table_status = {}
        print("📋 CRITICAL TABLES STATUS:")
        print("-" * 40)
        
        for table, description in critical_tables.items():
            exists, status = self.check_table_exists(table)
            table_status[table] = exists
            
            status_icon = "✅" if exists else "❌"
            print(f"{status_icon} {table:<20} | {status:<15} | {description}")
        
        print()
        
        # Check for specific missing columns in existing tables
        print("🔍 CHECKING FOR MISSING COLUMNS:")
        print("-" * 50)
        
        critical_columns = {
            'property_locations': [
                'kakao_api_response',  # JSONB column for API responses
                'cortar_no',           # Regional code
                'nearest_station',     # Subway info
                'postal_code'          # Postal code
            ],
            'property_physical': [
                'floor_description',   # Floor description text
                'veranda_count',       # Number of verandas
                'space_type',          # Type of space
                'monthly_management_cost'  # Management fee
            ],
            'property_tax_info': [
                'acquisition_tax_rate',  # Tax rate calculation
                'total_cost',            # Total cost calculation
                'is_estimated'           # Whether values are estimates
            ]
        }
        
        columns_analysis = {}
        
        for table, expected_columns in critical_columns.items():
            if table_status.get(table, False):
                has_columns, actual_columns = self.check_table_columns(table)
                columns_analysis[table] = {
                    'exists': has_columns,
                    'columns': actual_columns,
                    'expected': expected_columns
                }
                
                if has_columns and actual_columns and actual_columns != ["table_empty_no_columns_info"]:
                    missing_columns = [col for col in expected_columns if col not in actual_columns]
                    
                    print(f"\n🔍 Table: {table}")
                    print(f"   📊 Total columns found: {len(actual_columns)}")
                    
                    if missing_columns:
                        print(f"   ❌ Missing columns ({len(missing_columns)}):")
                        for col in missing_columns:
                            print(f"      • {col}")
                    else:
                        print("   ✅ All critical columns present")
                        
                else:
                    print(f"\n❌ {table}: Cannot analyze columns (table empty or inaccessible)")
            else:
                print(f"\n❌ {table}: TABLE MISSING - cannot check columns")
        
        print()
        
        # Summary and recommendations
        print("📊 ANALYSIS SUMMARY:")
        print("=" * 50)
        
        missing_tables = [table for table, exists in table_status.items() if not exists]
        existing_tables = [table for table, exists in table_status.items() if exists]
        
        print(f"✅ Existing tables: {len(existing_tables)}/{len(critical_tables)}")
        print(f"❌ Missing tables: {len(missing_tables)}/{len(critical_tables)}")
        
        if missing_tables:
            print(f"\n🚨 MISSING CRITICAL TABLES:")
            for table in missing_tables:
                print(f"   • {table}: {critical_tables[table]}")
        
        # Calculate overall completeness
        total_expected_elements = len(critical_tables) + sum(len(cols) for cols in critical_columns.values())
        existing_elements = len(existing_tables)
        
        # Count existing columns (rough estimate)
        for table, analysis in columns_analysis.items():
            if analysis['exists'] and analysis['columns'] and analysis['columns'] != ["table_empty_no_columns_info"]:
                existing_elements += len([col for col in analysis['expected'] if col in analysis['columns']])
        
        completeness_pct = (existing_elements / total_expected_elements) * 100
        
        print(f"\n📈 OVERALL SCHEMA COMPLETENESS: {completeness_pct:.1f}%")
        
        if completeness_pct < 80:
            print("🚨 CRITICAL: Schema is incomplete - deployment required!")
            print("   Run: python execute_schema_deployment.py")
        elif completeness_pct < 95:
            print("⚠️  WARNING: Some elements missing - deployment recommended")
        else:
            print("✅ Schema appears complete")
        
        return {
            'table_status': table_status,
            'columns_analysis': columns_analysis,
            'completeness_percentage': completeness_pct,
            'missing_tables': missing_tables,
            'needs_deployment': completeness_pct < 90
        }

def main():
    """Main schema analysis execution"""
    try:
        checker = SchemaChecker()
        analysis_result = checker.analyze_schema_gaps()
        
        print(f"\n🕒 Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if analysis_result['needs_deployment']:
            print("\n🚀 NEXT STEPS:")
            print("1. Review the missing elements above")
            print("2. Run deployment script: python execute_schema_deployment.py")
            print("3. Validate results with this script again")
            return 1
        else:
            print("\n✅ Schema analysis complete - no immediate deployment needed")
            return 0
    
    except Exception as e:
        print(f"💥 Analysis failed: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)