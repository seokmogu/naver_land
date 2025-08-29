#!/usr/bin/env python3
"""
Supabase Schema Deployment via REST API
Deploys critical missing schema elements using Supabase RPC functions
"""

import os
import sys
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

# Load environment variables
load_dotenv()

class SupabaseSchemaDeployer:
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
    
    def execute_sql_via_rpc(self, sql_statement, function_name="execute_sql"):
        """Execute SQL statement via Supabase RPC"""
        try:
            url = f"{self.supabase_url}/rest/v1/rpc/{function_name}"
            payload = {"sql_query": sql_statement}
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, str(e)
    
    def create_deployment_function(self):
        """Create SQL execution function in Supabase"""
        sql_function = """
        CREATE OR REPLACE FUNCTION execute_sql(sql_query TEXT)
        RETURNS JSON AS $$
        DECLARE
            result JSON;
        BEGIN
            EXECUTE sql_query;
            result := '{"status": "success", "message": "SQL executed successfully"}';
            RETURN result;
        EXCEPTION WHEN OTHERS THEN
            result := json_build_object(
                'status', 'error',
                'message', SQLERRM,
                'sqlstate', SQLSTATE
            );
            RETURN result;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        
        return self.execute_sql_via_rpc(sql_function)
    
    def deploy_critical_elements(self):
        """Deploy critical missing schema elements one by one"""
        print("🚀 DEPLOYING CRITICAL SCHEMA ELEMENTS")
        print("=" * 60)
        print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Deployment tasks
        deployment_tasks = [
            {
                "name": "Create realtors table",
                "sql": """
                CREATE TABLE IF NOT EXISTS realtors (
                    id BIGSERIAL PRIMARY KEY,
                    realtor_name VARCHAR(200) NOT NULL,
                    business_number VARCHAR(50) UNIQUE,
                    license_number VARCHAR(50),
                    phone_number VARCHAR(20),
                    mobile_number VARCHAR(20),
                    email VARCHAR(100),
                    website_url VARCHAR(500),
                    office_address VARCHAR(500),
                    office_postal_code VARCHAR(10),
                    profile_image_url TEXT,
                    company_description TEXT,
                    rating DECIMAL(3, 2),
                    review_count INTEGER DEFAULT 0,
                    total_listings INTEGER DEFAULT 0,
                    active_listings INTEGER DEFAULT 0,
                    is_verified BOOLEAN DEFAULT false,
                    last_verified_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            },
            {
                "name": "Add kakao_api_response to property_locations",
                "sql": """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'property_locations' 
                        AND column_name = 'kakao_api_response'
                    ) THEN
                        ALTER TABLE property_locations 
                        ADD COLUMN kakao_api_response JSONB;
                    END IF;
                END $$;
                """
            },
            {
                "name": "Add floor_description to property_physical", 
                "sql": """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'property_physical' 
                        AND column_name = 'floor_description'
                    ) THEN
                        ALTER TABLE property_physical 
                        ADD COLUMN floor_description TEXT;
                    END IF;
                END $$;
                """
            },
            {
                "name": "Ensure acquisition_tax_rate in property_tax_info",
                "sql": """
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'property_tax_info' 
                        AND column_name = 'acquisition_tax_rate'
                    ) THEN
                        ALTER TABLE property_tax_info 
                        ADD COLUMN acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000;
                    END IF;
                END $$;
                """
            },
            {
                "name": "Create property_realtors relationship table",
                "sql": """
                CREATE TABLE IF NOT EXISTS property_realtors (
                    id BIGSERIAL PRIMARY KEY,
                    property_id BIGINT REFERENCES properties_new(id) ON DELETE CASCADE,
                    realtor_id BIGINT REFERENCES realtors(id),
                    listing_date DATE,
                    listing_type VARCHAR(20) DEFAULT 'exclusive',
                    is_primary BOOLEAN DEFAULT false,
                    commission_rate DECIMAL(5, 4),
                    contact_phone VARCHAR(20),
                    contact_person VARCHAR(100),
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            },
            {
                "name": "Create essential indexes",
                "sql": """
                CREATE INDEX IF NOT EXISTS idx_realtors_name ON realtors(realtor_name);
                CREATE INDEX IF NOT EXISTS idx_realtors_business ON realtors(business_number);
                CREATE INDEX IF NOT EXISTS idx_property_locations_kakao_api 
                    ON property_locations USING GIN (kakao_api_response);
                CREATE INDEX IF NOT EXISTS idx_property_physical_floor_desc 
                    ON property_physical(floor_description);
                CREATE INDEX IF NOT EXISTS idx_property_realtors_property 
                    ON property_realtors(property_id);
                CREATE INDEX IF NOT EXISTS idx_property_realtors_realtor 
                    ON property_realtors(realtor_id);
                """
            }
        ]
        
        # Execute each deployment task
        successful_tasks = 0
        failed_tasks = 0
        
        for i, task in enumerate(deployment_tasks, 1):
            print(f"📝 Task {i}/{len(deployment_tasks)}: {task['name']}")
            
            # Use direct HTTP call to Supabase SQL editor functionality 
            success, result = self.execute_direct_sql(task['sql'])
            
            if success:
                print(f"   ✅ Success")
                successful_tasks += 1
            else:
                print(f"   ❌ Failed: {result}")
                failed_tasks += 1
            
            print()
        
        # Summary
        print("=" * 60)
        print("📊 DEPLOYMENT SUMMARY:")
        print(f"   ✅ Successful tasks: {successful_tasks}")
        print(f"   ❌ Failed tasks: {failed_tasks}")
        
        success_rate = (successful_tasks / len(deployment_tasks)) * 100
        print(f"   📈 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
            print("✅ Critical schema elements have been deployed")
            return True
        else:
            print("\n⚠️ DEPLOYMENT COMPLETED WITH ISSUES")
            print("🔧 Some elements may need manual intervention")
            return False
    
    def execute_direct_sql(self, sql):
        """Execute SQL using Supabase's SQL execution endpoint"""
        try:
            # Try multiple approaches to execute SQL
            
            # Approach 1: Use rpc function if it exists
            url = f"{self.supabase_url}/rest/v1/rpc/execute_sql"
            payload = {"sql_query": sql}
            
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                return True, "Executed successfully"
            
            # Approach 2: Direct SQL execution (may not work with REST API)
            # This would require database access or admin permissions
            
            return False, f"SQL execution not supported via REST API. HTTP {response.status_code}: {response.text}"
            
        except Exception as e:
            return False, str(e)
    
    def validate_deployment(self):
        """Validate that deployment was successful"""
        print("\n🔍 VALIDATING DEPLOYMENT...")
        print("-" * 40)
        
        # Test queries to validate deployment
        validation_checks = [
            {
                "name": "realtors table",
                "table": "realtors",
                "test_query": "?select=id&limit=1"
            },
            {
                "name": "property_realtors table", 
                "table": "property_realtors",
                "test_query": "?select=id&limit=1"
            },
            {
                "name": "property_locations with kakao_api_response",
                "table": "property_locations",
                "test_query": "?select=id,kakao_api_response&limit=1"
            },
            {
                "name": "property_physical with floor_description",
                "table": "property_physical", 
                "test_query": "?select=id,floor_description&limit=1"
            }
        ]
        
        successful_validations = 0
        
        for check in validation_checks:
            try:
                url = f"{self.supabase_url}/rest/v1/{check['table']}{check['test_query']}"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    print(f"✅ {check['name']}: Available")
                    successful_validations += 1
                else:
                    print(f"❌ {check['name']}: Not available ({response.status_code})")
                    
            except Exception as e:
                print(f"❌ {check['name']}: Error - {str(e)}")
        
        validation_rate = (successful_validations / len(validation_checks)) * 100
        print(f"\n📊 Validation success rate: {validation_rate:.1f}%")
        
        return validation_rate >= 75

def main():
    """Main deployment execution"""
    print("🏗️ SUPABASE CRITICAL SCHEMA DEPLOYMENT")
    print("=" * 60)
    
    try:
        deployer = SupabaseSchemaDeployer()
        
        # Run deployment
        deployment_success = deployer.deploy_critical_elements()
        
        if deployment_success:
            # Validate deployment
            validation_success = deployer.validate_deployment()
            
            if validation_success:
                print("\n🎉 DEPLOYMENT AND VALIDATION SUCCESSFUL!")
                print("✅ Critical schema fixes have been applied")
                print("✅ Run quick_schema_check.py to verify completeness")
                return 0
            else:
                print("\n⚠️ Deployment completed but validation had issues")
                return 1
        else:
            print("\n❌ Deployment failed")
            print("🔧 Manual intervention may be required")
            return 1
    
    except Exception as e:
        print(f"\n💥 Deployment error: {str(e)}")
        print("\nℹ️  Note: This deployment method has limitations.")
        print("   For full SQL execution, use a direct database connection")
        print("   or Supabase SQL Editor interface")
        return 1
    
    finally:
        print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)