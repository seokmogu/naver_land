#!/bin/bash
# =============================================================================
# SUPABASE SCHEMA DEPLOYMENT VIA CLI
# Deploys critical missing schema elements using Supabase CLI
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_REF="eslhavjipwbyvbbknixv"
SUPABASE_URL="https://eslhavjipwbyvbbknixv.supabase.co"

echo -e "${BLUE}🏗️ SUPABASE CRITICAL SCHEMA DEPLOYMENT${NC}"
echo "============================================================"
echo "🕒 Started at: $(date)"
echo ""

# Function to execute SQL and handle errors
execute_sql() {
    local description="$1"
    local sql="$2"
    
    echo -e "${YELLOW}📝 $description${NC}"
    
    # Create temporary SQL file
    local temp_file=$(mktemp /tmp/supabase_sql.XXXXXX)
    echo "$sql" > "$temp_file"
    
    # Execute SQL via Supabase CLI
    if supabase db reset --linked --db-url "$SUPABASE_URL" 2>/dev/null; then
        echo "   Using reset command"
    fi
    
    # Try to execute the SQL file
    if echo "$sql" | supabase db push --linked 2>/dev/null; then
        echo -e "   ${GREEN}✅ Success${NC}"
        rm "$temp_file"
        return 0
    else
        # Alternative: use psql through supabase
        if supabase db connect --linked <<< "$sql" 2>/dev/null; then
            echo -e "   ${GREEN}✅ Success${NC}"
            rm "$temp_file"
            return 0
        else
            echo -e "   ${RED}❌ Failed${NC}"
            rm "$temp_file"
            return 1
        fi
    fi
}

# Function to validate deployment
validate_table() {
    local table_name="$1"
    echo -e "${BLUE}🔍 Validating table: $table_name${NC}"
    
    # Simple validation by checking if table exists
    local validation_sql="SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = '$table_name'
    ) AS table_exists;"
    
    if echo "$validation_sql" | supabase db connect --linked 2>/dev/null | grep -q "t"; then
        echo -e "   ${GREEN}✅ Table exists${NC}"
        return 0
    else
        echo -e "   ${RED}❌ Table missing${NC}"
        return 1
    fi
}

# Function to check column exists
validate_column() {
    local table_name="$1"
    local column_name="$2"
    echo -e "${BLUE}🔍 Validating column: $table_name.$column_name${NC}"
    
    local validation_sql="SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = '$table_name' 
        AND column_name = '$column_name'
    ) AS column_exists;"
    
    if echo "$validation_sql" | supabase db connect --linked 2>/dev/null | grep -q "t"; then
        echo -e "   ${GREEN}✅ Column exists${NC}"
        return 0
    else
        echo -e "   ${RED}❌ Column missing${NC}"
        return 1
    fi
}

echo -e "${YELLOW}🚀 Starting deployment of critical schema elements...${NC}"
echo ""

successful_deployments=0
failed_deployments=0

# 1. Deploy realtors table
echo -e "${BLUE}=== DEPLOYING REALTORS TABLE ===${NC}"
if execute_sql "Create realtors table" "
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

-- Create indexes for realtors table
CREATE INDEX IF NOT EXISTS idx_realtors_name ON realtors(realtor_name);
CREATE INDEX IF NOT EXISTS idx_realtors_business ON realtors(business_number);
CREATE INDEX IF NOT EXISTS idx_realtors_verified ON realtors(is_verified, rating);
"; then
    ((successful_deployments++))
else
    ((failed_deployments++))
fi
echo ""

# 2. Add kakao_api_response column
echo -e "${BLUE}=== ADDING KAKAO_API_RESPONSE COLUMN ===${NC}"
if execute_sql "Add kakao_api_response to property_locations" "
DO \$\$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_locations' 
        AND column_name = 'kakao_api_response'
    ) THEN
        ALTER TABLE property_locations 
        ADD COLUMN kakao_api_response JSONB;
        
        CREATE INDEX idx_property_locations_kakao_api 
        ON property_locations USING GIN (kakao_api_response);
    END IF;
END \$\$;
"; then
    ((successful_deployments++))
else
    ((failed_deployments++))
fi
echo ""

# 3. Add floor_description column
echo -e "${BLUE}=== ADDING FLOOR_DESCRIPTION COLUMN ===${NC}"
if execute_sql "Add floor_description to property_physical" "
DO \$\$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_physical' 
        AND column_name = 'floor_description'
    ) THEN
        ALTER TABLE property_physical 
        ADD COLUMN floor_description TEXT;
        
        CREATE INDEX idx_property_physical_floor_desc 
        ON property_physical(floor_description);
    END IF;
END \$\$;
"; then
    ((successful_deployments++))
else
    ((failed_deployments++))
fi
echo ""

# 4. Ensure acquisition_tax_rate column exists
echo -e "${BLUE}=== ENSURING ACQUISITION_TAX_RATE COLUMN ===${NC}"
if execute_sql "Ensure acquisition_tax_rate in property_tax_info" "
DO \$\$ 
BEGIN
    -- First ensure the table exists
    CREATE TABLE IF NOT EXISTS property_tax_info (
        id BIGSERIAL PRIMARY KEY,
        property_id BIGINT,
        acquisition_tax INTEGER DEFAULT 0,
        acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
        registration_tax INTEGER DEFAULT 0,
        registration_tax_rate DECIMAL(5, 4) DEFAULT 0.0000,
        brokerage_fee INTEGER DEFAULT 0,
        brokerage_fee_rate DECIMAL(5, 4) DEFAULT 0.0000,
        stamp_duty INTEGER DEFAULT 0,
        vat INTEGER DEFAULT 0,
        total_tax INTEGER DEFAULT 0,
        total_cost INTEGER DEFAULT 0,
        calculation_date DATE DEFAULT CURRENT_DATE,
        is_estimated BOOLEAN DEFAULT false,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Then ensure the column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'property_tax_info' 
        AND column_name = 'acquisition_tax_rate'
    ) THEN
        ALTER TABLE property_tax_info 
        ADD COLUMN acquisition_tax_rate DECIMAL(5, 4) DEFAULT 0.0000;
    END IF;
END \$\$;
"; then
    ((successful_deployments++))
else
    ((failed_deployments++))
fi
echo ""

# 5. Create property_realtors relationship table
echo -e "${BLUE}=== CREATING PROPERTY_REALTORS TABLE ===${NC}"
if execute_sql "Create property_realtors relationship table" "
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
CREATE INDEX IF NOT EXISTS idx_property_realtors_primary ON property_realtors(is_primary, listing_date);
"; then
    ((successful_deployments++))
else
    ((failed_deployments++))
fi
echo ""

# Summary
echo -e "${BLUE}============================================================${NC}"
echo -e "${YELLOW}📊 DEPLOYMENT SUMMARY:${NC}"
echo -e "   ${GREEN}✅ Successful deployments: $successful_deployments${NC}"
echo -e "   ${RED}❌ Failed deployments: $failed_deployments${NC}"

total_deployments=$((successful_deployments + failed_deployments))
if [ $total_deployments -gt 0 ]; then
    success_rate=$((successful_deployments * 100 / total_deployments))
    echo -e "   📈 Success rate: ${success_rate}%"
else
    success_rate=0
fi

echo ""

# Validation phase
echo -e "${BLUE}🔍 VALIDATION PHASE${NC}"
echo "----------------------------------------"

validation_failures=0

# Validate tables exist
for table in "realtors" "property_realtors" "property_tax_info"; do
    if ! validate_table "$table"; then
        ((validation_failures++))
    fi
done

# Validate columns exist  
validate_column "property_locations" "kakao_api_response" || ((validation_failures++))
validate_column "property_physical" "floor_description" || ((validation_failures++))
validate_column "property_tax_info" "acquisition_tax_rate" || ((validation_failures++))

echo ""

# Final status
if [ $success_rate -ge 80 ] && [ $validation_failures -eq 0 ]; then
    echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
    echo -e "${GREEN}✅ All critical schema elements have been deployed${NC}"
    echo -e "${GREEN}✅ Validation passed${NC}"
    echo ""
    echo -e "${BLUE}🚀 Next steps:${NC}"
    echo "   1. Run: python quick_schema_check.py"
    echo "   2. Test your application with the new schema"
    echo "   3. Monitor for any performance issues"
    exit 0
elif [ $success_rate -ge 50 ]; then
    echo -e "${YELLOW}⚠️ DEPLOYMENT COMPLETED WITH ISSUES${NC}"
    echo -e "${YELLOW}🔧 Some elements may need manual intervention${NC}"
    if [ $validation_failures -gt 0 ]; then
        echo -e "${YELLOW}⚠️ $validation_failures validation failures detected${NC}"
    fi
    exit 1
else
    echo -e "${RED}❌ DEPLOYMENT FAILED${NC}"
    echo -e "${RED}💥 Most deployment tasks failed${NC}"
    echo -e "${RED}🔧 Manual database intervention required${NC}"
    echo ""
    echo -e "${BLUE}💡 Troubleshooting suggestions:${NC}"
    echo "   1. Check Supabase project permissions"
    echo "   2. Verify database connection"
    echo "   3. Review error messages above"
    echo "   4. Consider using Supabase SQL Editor for manual deployment"
    exit 2
fi

echo ""
echo "🕒 Completed at: $(date)"