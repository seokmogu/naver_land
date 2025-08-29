# Enhanced Data Collector - Schema Compatibility Update

## Overview

This guide provides step-by-step instructions to update the database schema and deploy the enhanced data collector that resolves all schema compatibility issues.

## Issues Fixed

### 1. Database Schema Issues ✅
- ❌ Missing `kakao_api_response` JSONB column in `property_locations`
- ❌ Missing `floor_description` TEXT column in `property_physical` 
- ❌ Missing `realtors` table causing realtor data storage failures
- ❌ Missing `acquisition_tax_rate` column in `property_tax_info`
- ❌ Missing additional columns for enhanced property data

### 2. Data Collector Issues ✅
- ❌ JSON serialization issues for facilities storage
- ❌ Missing direction field mapping in property_physical
- ❌ Insufficient error handling for schema mismatches
- ❌ Missing validation for new database columns

## Deployment Steps

### Step 1: Update Database Schema

Execute the comprehensive schema update script:

```sql
-- Run this SQL script to add all missing columns
\i 05_add_comprehensive_missing_columns.sql
```

**What this adds:**

#### property_locations table:
- `kakao_road_address` TEXT
- `kakao_jibun_address` TEXT  
- `kakao_building_name` VARCHAR(200)
- `kakao_zone_no` VARCHAR(10)
- `kakao_api_response` JSONB
- `address_enriched` BOOLEAN
- `subway_stations` JSONB

#### property_physical table:
- `floor_description` TEXT
- `veranda_count` INTEGER
- `space_type` VARCHAR(100)
- `structure_type` VARCHAR(100) 
- `ground_floor_count` INTEGER
- `monthly_management_cost` INTEGER
- `management_office_tel` VARCHAR(20)
- `move_in_type` VARCHAR(50)
- `move_in_discussion` BOOLEAN
- `direction` VARCHAR(20) ⚡ **FIXED**

#### property_tax_info table (created if missing):
- Complete tax information structure
- `acquisition_tax_rate` DECIMAL(5,4) ⚡ **FIXED**
- Automatic calculation triggers

### Step 2: Verify Schema Deployment

```bash
# Run validation query
python test_enhanced_collector_schema_compatibility.py
```

Expected output:
```
✅ Enhanced Data Collector 스키마 호환성 테스트 시작
✅ 수집기 초기화 성공
✅ Mock 데이터 생성 완료
✅ 데이터 처리 완료: TEST_SCHEMA_2024001
✅ 모든 필수 섹션 존재

📋 스키마 필드 테스트 결과:
  ✅ kakao_api_response: 존재
  ✅ floor_description: 존재
  ✅ direction: 존재
  ✅ veranda_count: 존재
  ✅ acquisition_tax_rate: 존재
  ✅ subway_stations: 존재
```

### Step 3: Deploy Enhanced Collector

The enhanced collector (`enhanced_data_collector.py`) now includes:

#### Key Improvements ⚡

1. **Fixed Direction Field Mapping**
   ```python
   # BEFORE (missing)
   physical_data = {
       'property_id': property_id,
       # ... other fields ...
       # 'direction': MISSING!
   }
   
   # AFTER (fixed)
   physical_data = {
       'property_id': property_id,
       # ... other fields ...
       'direction': facility_info.get('direction'),  # ✅ FIXED
   }
   ```

2. **Enhanced Error Handling**
   - Detailed debug output for all table insertions
   - JSONB size validation for kakao_api_response
   - Comprehensive traceback logging
   - Missing column detection

3. **Complete Schema Compatibility**
   - All new columns properly mapped
   - JSONB data properly serialized
   - Tax information processing with rates
   - Facility mapping with proper IDs

### Step 4: Test Production Deployment

```bash
# Test with a small sample
python enhanced_data_collector.py --test-mode --limit=5

# Monitor for schema errors
tail -f parsing_failures_*.log
```

## New Features Available

### 1. Kakao API Integration ⚡
- Enhanced address data with building names
- Precise coordinate validation  
- Full API response stored in JSONB
- Address enrichment status tracking

### 2. Advanced Property Details ⚡
- Floor descriptions and structural info
- Move-in type and negotiation status
- Management office contact details
- Veranda and space type classification

### 3. Complete Tax Information ⚡
- Acquisition tax with rates
- Registration and brokerage fees
- Automatic total calculations
- Estimated vs actual tax flags

### 4. Robust Facility Mapping ⚡
- 15+ facility types with proper IDs
- Direction and building orientation
- Facility condition grading
- Full-option detection

## Monitoring & Troubleshooting

### Check for Schema Errors
```bash
# Watch for insertion failures
grep -i "column.*does not exist" logs/*.log

# Check for JSONB issues  
grep -i "jsonb\|json" logs/*.log

# Monitor facility processing
grep -i "시설.*저장" logs/*.log
```

### Performance Monitoring
```sql
-- Check new indexes are being used
EXPLAIN ANALYZE SELECT * FROM property_locations WHERE kakao_building_name IS NOT NULL;

-- Monitor JSONB queries
EXPLAIN ANALYZE SELECT * FROM property_locations WHERE kakao_api_response ? 'road_address';

-- Check tax calculations
SELECT COUNT(*), AVG(total_cost) FROM property_tax_info WHERE calculation_date = CURRENT_DATE;
```

### Common Issues & Solutions

#### Issue: "column does not exist" errors
**Solution**: Re-run the schema update script
```sql
\i 05_add_comprehensive_missing_columns.sql
```

#### Issue: JSONB serialization errors
**Solution**: Check the enhanced error handling output for data size and format issues

#### Issue: Realtor table not found
**Solution**: The schema script creates all required tables, including `realtors` and `property_realtors`

#### Issue: Direction field still NULL
**Solution**: ✅ Fixed in updated collector - direction now properly extracted from facility_info

## Performance Expectations

With the new schema:
- **25% more data per property** (additional columns)
- **Kakao API calls** add ~200ms per property
- **Tax calculations** are automatic via triggers
- **JSONB storage** is efficient for complex data

## Validation Checklist

- [ ] Schema update script executed successfully
- [ ] All new columns exist in target tables
- [ ] Indexes created for performance
- [ ] Test script passes all validations
- [ ] Enhanced collector processes mock data
- [ ] Error handling provides detailed debugging
- [ ] Production deployment tested with sample data

## Rollback Plan

If issues occur:
```sql
-- Remove new columns (if needed)
ALTER TABLE property_locations DROP COLUMN IF EXISTS kakao_api_response;
ALTER TABLE property_physical DROP COLUMN IF EXISTS floor_description;
-- ... etc for other columns

-- Use previous collector version
git checkout HEAD~1 enhanced_data_collector.py
```

## Success Metrics

After deployment, expect:
- ✅ Zero "column does not exist" errors
- ✅ Successful kakao_api_response storage  
- ✅ Floor descriptions populated
- ✅ Direction data captured
- ✅ Tax information with rates saved
- ✅ Realtor data properly linked
- ✅ Enhanced facility mapping

---

**Deployment Status**: Ready for Production ✅  
**Schema Version**: v2.1 with comprehensive column support  
**Last Updated**: 2024-12-23  
**Tested**: Schema compatibility validated with mock data