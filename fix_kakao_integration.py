#!/usr/bin/env python3
"""
Complete Kakao Integration Fix
Runs all necessary steps to fix the database schema and test the integration
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

def run_fix_sequence():
    """Run the complete fix sequence"""
    
    print("🔧 KAKAO INTEGRATION COMPLETE FIX")
    print("=" * 50)
    
    # Step 1: Diagnose current issues
    print("\n🔍 Step 1: Diagnosing current schema issues...")
    try:
        result = subprocess.run([sys.executable, "diagnose_schema_issues.py"], 
                              capture_output=True, text=True, cwd=".")
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        return False
    
    # Step 2: Instructions for manual schema fix
    print("\n🛠️ Step 2: Apply the database schema fix")
    print("-" * 40)
    print("MANUAL STEP REQUIRED:")
    print("1. Open your Supabase dashboard SQL editor")
    print("2. Copy and paste the contents of 'complete_schema_fix.sql'")
    print("3. Execute the SQL script")
    print("4. Verify you see success messages like '✅ Added column...'")
    print("\nOR if you have psql access:")
    print("psql -d your_database -f complete_schema_fix.sql")
    
    input("\n⏸️  Press ENTER after you've executed the schema fix SQL...")
    
    # Step 3: Verify the fix worked
    print("\n✅ Step 3: Verifying schema fix...")
    try:
        result = subprocess.run([sys.executable, "diagnose_schema_issues.py"], 
                              capture_output=True, text=True, cwd=".")
        output = result.stdout
        print(output)
        
        if "MISSING COLUMNS" in output:
            print("\n❌ Schema fix was not applied correctly!")
            print("Please check the SQL execution and try again.")
            return False
        else:
            print("\n✅ Schema fix successful!")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    # Step 4: Test the integration
    print("\n🧪 Step 4: Testing Kakao integration...")
    try:
        result = subprocess.run([sys.executable, "test_kakao_integration.py"], 
                              capture_output=True, text=True, cwd=".")
        print(result.stdout)
        
        if result.returncode == 0:
            print("\n🎉 KAKAO INTEGRATION FIX COMPLETED SUCCESSFULLY!")
            print("✅ Database schema is fixed")
            print("✅ All missing columns are now available")
            print("✅ Kakao address conversion should work")
            print("✅ The enhanced_data_collector.py should run without column errors")
            
            print(f"\n🚀 NEXT STEPS:")
            print("1. Run your data collector with Kakao integration enabled")
            print("2. Monitor logs for successful address enrichment")
            print("3. Check the database for enriched address data")
            return True
        else:
            print(f"\n⚠️ Integration test completed with issues")
            print("Check the output above for details")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("This script will guide you through fixing the Kakao integration issues.")
    print("Make sure you have access to your Supabase dashboard or psql.")
    print()
    
    proceed = input("Continue? (y/N): ").lower().strip()
    if proceed == 'y':
        success = run_fix_sequence()
        sys.exit(0 if success else 1)
    else:
        print("Fix cancelled.")
        sys.exit(0)