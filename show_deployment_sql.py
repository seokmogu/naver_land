#!/usr/bin/env python3
"""
Display Deployment SQL Commands
Shows the exact SQL commands that need to be executed in Supabase
"""

def show_deployment_commands():
    print("🏗️ SUPABASE CRITICAL SCHEMA FIXES")
    print("=" * 80)
    print()
    print("📋 Copy and paste these SQL commands into Supabase SQL Editor:")
    print()
    
    # Command 1: Create realtors table
    print("🔹 STEP 1: CREATE REALTORS TABLE")
    print("-" * 40)
    realtors_sql = """
-- Create realtors table
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_realtors_name ON realtors(realtor_name);
CREATE INDEX IF NOT EXISTS idx_realtors_business ON realtors(business_number);
"""
    print(realtors_sql)
    
    # Command 2: Add missing columns
    print("\n🔹 STEP 2: ADD MISSING COLUMNS")
    print("-" * 40)
    columns_sql = """
-- Add kakao_api_response to property_locations
ALTER TABLE property_locations 
ADD COLUMN IF NOT EXISTS kakao_api_response JSONB;

CREATE INDEX IF NOT EXISTS idx_property_locations_kakao_api 
ON property_locations USING GIN (kakao_api_response);

-- Add floor_description to property_physical
ALTER TABLE property_physical 
ADD COLUMN IF NOT EXISTS floor_description TEXT;

CREATE INDEX IF NOT EXISTS idx_property_physical_floor_desc 
ON property_physical(floor_description);

-- Ensure property_tax_info table exists with acquisition_tax_rate
CREATE TABLE IF NOT EXISTS property_tax_info (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT,
    acquisition_tax INTEGER DEFAULT 0,
    acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
    registration_tax INTEGER DEFAULT 0,
    brokerage_fee INTEGER DEFAULT 0,
    total_tax INTEGER DEFAULT 0,
    total_cost INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
    print(columns_sql)
    
    # Command 3: Create property_realtors table
    print("\n🔹 STEP 3: CREATE PROPERTY_REALTORS TABLE")
    print("-" * 40)
    property_realtors_sql = """
-- Create property_realtors relationship table
CREATE TABLE IF NOT EXISTS property_realtors (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT,
    realtor_id BIGINT,
    listing_date DATE,
    listing_type VARCHAR(20) DEFAULT 'exclusive',
    is_primary BOOLEAN DEFAULT false,
    commission_rate DECIMAL(5, 4),
    contact_phone VARCHAR(20),
    contact_person VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_property_realtors_property ON property_realtors(property_id);
CREATE INDEX IF NOT EXISTS idx_property_realtors_realtor ON property_realtors(realtor_id);
"""
    print(property_realtors_sql)
    
    # Command 4: Validation
    print("\n🔹 STEP 4: VALIDATION")
    print("-" * 40)
    validation_sql = """
-- Validate deployment
SELECT 
    table_name,
    COUNT(*) as column_count
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND table_name IN ('realtors', 'property_realtors', 'property_tax_info')
GROUP BY table_name;

-- Check missing columns were added
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND ((table_name = 'property_locations' AND column_name = 'kakao_api_response')
     OR (table_name = 'property_physical' AND column_name = 'floor_description')
     OR (table_name = 'property_tax_info' AND column_name = 'acquisition_tax_rate'));
"""
    print(validation_sql)
    
    print("\n" + "=" * 80)
    print("🎯 DEPLOYMENT INSTRUCTIONS:")
    print("1. Open Supabase Dashboard → Your Project → SQL Editor")
    print("2. Copy and paste each SQL block above")
    print("3. Execute each block in order (Step 1 → 2 → 3 → 4)")
    print("4. Verify the validation results show all tables/columns created")
    print("5. Run: python quick_schema_check.py to confirm completeness")
    print()
    print("⚠️  If any step fails, review the error message and retry")
    print("✅ Expected result: Schema completeness >90%")

if __name__ == "__main__":
    show_deployment_commands()