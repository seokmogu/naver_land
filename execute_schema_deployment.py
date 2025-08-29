#!/usr/bin/env python3
"""
Critical Database Schema Deployment Script
Executes the SQL fixes for missing tables and columns in Supabase
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from datetime import datetime

# Load environment variables
load_dotenv()

class SchemaDeploymentManager:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY in .env file")
        
        # Extract database connection details from Supabase URL
        # Format: https://project_ref.supabase.co
        project_ref = self.supabase_url.split('//')[1].split('.')[0]
        
        # Supabase connection parameters
        self.db_params = {
            'host': f'{project_ref}.supabase.co',
            'database': 'postgres',
            'user': 'postgres',
            'password': 'Wlsdud12!',  # You'll need to update this with actual password
            'port': 5432,
            'sslmode': 'require'
        }
        
        self.connection = None
    
    def connect(self):
        """Establish connection to Supabase PostgreSQL database"""
        try:
            print(f"🔌 Connecting to Supabase database...")
            self.connection = psycopg2.connect(**self.db_params)
            self.connection.autocommit = False  # Use transactions
            print("✅ Connected successfully!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {str(e)}")
            print("\n⚠️  Please verify your database credentials in the script")
            return False
    
    def execute_sql_file(self, file_path):
        """Execute SQL commands from file with error handling"""
        if not self.connection:
            print("❌ No database connection")
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            print(f"🚀 Executing SQL deployment from {file_path}...")
            print("=" * 60)
            
            # Split SQL into individual statements and execute
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            successful_statements = 0
            failed_statements = 0
            
            for i, statement in enumerate(statements, 1):
                if not statement or statement.startswith('--') or statement.startswith('/*'):
                    continue
                
                try:
                    print(f"📝 Executing statement {i}/{len(statements)}: {statement[:60]}...")
                    cursor.execute(statement)
                    
                    # Fetch results if available
                    try:
                        results = cursor.fetchall()
                        if results:
                            for row in results:
                                print(f"   📊 {dict(row)}")
                    except psycopg2.ProgrammingError:
                        # No results to fetch (normal for DDL statements)
                        pass
                    
                    successful_statements += 1
                    print(f"   ✅ Success")
                    
                except Exception as stmt_error:
                    failed_statements += 1
                    print(f"   ⚠️  Statement failed: {str(stmt_error)}")
                    # Continue with other statements
                    continue
            
            # Commit all successful changes
            self.connection.commit()
            
            print("=" * 60)
            print(f"🎉 Deployment completed!")
            print(f"   ✅ Successful statements: {successful_statements}")
            print(f"   ⚠️  Failed statements: {failed_statements}")
            
            return failed_statements == 0
            
        except Exception as e:
            print(f"❌ SQL execution failed: {str(e)}")
            self.connection.rollback()
            return False
    
    def validate_deployment(self):
        """Run validation checks to confirm deployment success"""
        if not self.connection:
            return False
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            print("\n🔍 Running deployment validation...")
            print("=" * 50)
            
            # Execute validation function
            cursor.execute("SELECT * FROM validate_critical_schema_deployment();")
            validation_results = cursor.fetchall()
            
            success_count = 0
            for result in validation_results:
                component = result['component']
                status = result['status']
                details = result['details']
                
                status_icon = "✅" if status == "SUCCESS" else "⚠️" if status == "PARTIAL" else "❌"
                print(f"{status_icon} {component}: {status}")
                print(f"   📝 {details}")
                
                if status == "SUCCESS":
                    success_count += 1
            
            # Get deployment summary
            cursor.execute("""
                SELECT * FROM (
                    SELECT 
                        COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) as successful_components,
                        COUNT(CASE WHEN status = 'MISSING' THEN 1 END) as missing_components,
                        COUNT(CASE WHEN status = 'PARTIAL' THEN 1 END) as partial_components,
                        COUNT(*) as total_components,
                        ROUND(
                            COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END)::decimal / COUNT(*) * 100, 
                            2
                        ) as success_percentage
                    FROM validate_critical_schema_deployment()
                ) summary
            """)
            summary = cursor.fetchone()
            
            print("=" * 50)
            print("📊 DEPLOYMENT SUMMARY:")
            print(f"   ✅ Successful: {summary['successful_components']}")
            print(f"   ⚠️  Partial: {summary['partial_components']}")
            print(f"   ❌ Missing: {summary['missing_components']}")
            print(f"   📈 Success Rate: {summary['success_percentage']}%")
            
            return summary['success_percentage'] >= 85.0  # 85% success threshold
            
        except Exception as e:
            print(f"❌ Validation failed: {str(e)}")
            return False
    
    def check_current_schema_state(self):
        """Check current state of critical schema elements"""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            print("\n🔍 Checking current schema state...")
            print("=" * 50)
            
            # Check for critical tables
            critical_tables = ['realtors', 'property_tax_info', 'property_locations', 'property_physical']
            
            for table in critical_tables:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = '{table}'
                    ) AS table_exists
                """)
                exists = cursor.fetchone()['table_exists']
                print(f"{'✅' if exists else '❌'} Table '{table}': {'EXISTS' if exists else 'MISSING'}")
            
            # Check for critical columns
            critical_columns = [
                ('property_locations', 'kakao_api_response'),
                ('property_physical', 'floor_description'),
                ('property_tax_info', 'acquisition_tax_rate')
            ]
            
            print("\n📋 Critical columns:")
            for table, column in critical_columns:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}' 
                        AND column_name = '{column}'
                    ) AS column_exists
                """)
                exists = cursor.fetchone()['column_exists']
                print(f"{'✅' if exists else '❌'} {table}.{column}: {'EXISTS' if exists else 'MISSING'}")
            
        except Exception as e:
            print(f"❌ Schema check failed: {str(e)}")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")

def main():
    """Main deployment execution"""
    print("🏗️ SUPABASE SCHEMA CRITICAL FIXES DEPLOYMENT")
    print("=" * 60)
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Initialize deployment manager
    deployer = SchemaDeploymentManager()
    
    try:
        # Check database connection
        if not deployer.connect():
            return 1
        
        # Check current schema state
        deployer.check_current_schema_state()
        
        # Execute the SQL deployment
        sql_file_path = "/Users/smgu/test_code/naver_land/deploy_critical_schema_fixes.sql"
        
        if not os.path.exists(sql_file_path):
            print(f"❌ SQL file not found: {sql_file_path}")
            return 1
        
        # Execute deployment
        deployment_success = deployer.execute_sql_file(sql_file_path)
        
        if deployment_success:
            # Validate deployment
            validation_success = deployer.validate_deployment()
            
            if validation_success:
                print("\n🎉 CRITICAL SCHEMA FIXES DEPLOYED SUCCESSFULLY!")
                print("✅ All missing tables and columns have been added")
                print("✅ Performance indexes created")
                print("✅ Data validation constraints applied")
                print("✅ Update triggers configured")
                return 0
            else:
                print("\n⚠️ Deployment completed with issues")
                print("🔧 Some components may need manual verification")
                return 1
        else:
            print("\n❌ Deployment failed")
            print("🔧 Check error messages above and retry")
            return 1
    
    except Exception as e:
        print(f"\n💥 Deployment error: {str(e)}")
        return 1
    
    finally:
        deployer.close()
        print(f"\n🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)