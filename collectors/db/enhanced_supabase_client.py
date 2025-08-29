#!/usr/bin/env python3
"""
Enhanced Supabase Client with Fixed Data Processing
Addresses NULL data issues by using robust field mapping and validation
"""

import os
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
import logging

# Add path for enhanced processor
sys.path.append('/Users/smgu/test_code/naver_land/collectors')
from core.enhanced_data_processor import EnhancedDataProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedSupabaseHelper:
    """Enhanced Supabase helper with robust data processing"""
    
    def __init__(self, config_file: str = None):
        """Initialize enhanced Supabase client"""
        # Initialize Supabase client
        if config_file is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            config_file = os.path.join(base_dir, "config", "config.json")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        supabase_config = config.get('supabase', {})
        
        self.url = os.getenv('SUPABASE_URL', supabase_config.get('url'))
        self.key = os.getenv('SUPABASE_KEY', supabase_config.get('anon_key'))
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL과 Key가 필요합니다. config.json 또는 환경변수를 확인하세요.")
        
        self.client: Client = create_client(self.url, self.key)
        
        # Initialize enhanced data processor
        self.data_processor = EnhancedDataProcessor()
        
        logger.info("✅ Enhanced Supabase client initialized")
    
    def save_properties_with_enhanced_processing(self, raw_properties: List[Dict], 
                                               cortar_no: str, 
                                               debug_mode: bool = False) -> Dict:
        """Save properties using enhanced data processing"""
        
        logger.info(f"🔄 Processing {len(raw_properties)} raw properties for {cortar_no}")
        
        # Reset processor stats for this batch
        self.data_processor.reset_stats()
        
        # Process properties with enhanced validation
        processed_properties = []
        processing_errors = []
        
        for i, raw_prop in enumerate(raw_properties):
            try:
                processed_prop = self.data_processor.process_collected_property(raw_prop, cortar_no)
                
                if processed_prop:
                    processed_properties.append(processed_prop)
                    if debug_mode and i < 3:  # Log first few for debugging
                        logger.info(f"✅ Sample processed property {i+1}: {processed_prop['article_no']}")
                else:
                    processing_errors.append({
                        'index': i,
                        'raw_article_no': raw_prop.get('매물번호') or raw_prop.get('articleNo'),
                        'error': 'Processing returned None - likely validation failure'
                    })
                    
            except Exception as e:
                processing_errors.append({
                    'index': i,
                    'raw_article_no': raw_prop.get('매물번호') or raw_prop.get('articleNo'),
                    'error': str(e)
                })
                logger.error(f"❌ Processing error for property {i}: {e}")
        
        # Log processing statistics
        stats = self.data_processor.get_validation_stats()
        logger.info(f"📊 Processing stats: {stats['successful_extractions']}/{stats['total_processed']} successful")
        
        if stats['field_extraction_failures']:
            logger.warning(f"⚠️ Field extraction failures: {stats['field_extraction_failures']}")
        
        if not processed_properties:
            logger.error("❌ No properties successfully processed!")
            return {
                'success': False,
                'error': 'No properties could be processed',
                'processing_errors': processing_errors,
                'processing_stats': stats
            }
        
        # Save processed properties to database
        logger.info(f"💾 Saving {len(processed_properties)} processed properties to database")
        
        today = date.today()
        db_stats = {
            'new_count': 0,
            'updated_count': 0,
            'removed_count': 0,
            'total_saved': 0,
            'insertion_errors': []
        }
        
        try:
            # Get existing properties for comparison
            existing = self.client.table('properties')\
                .select('article_no, price, rent_price, trade_type, last_seen_date')\
                .eq('cortar_no', cortar_no)\
                .eq('is_active', True)\
                .execute()
            
            existing_map = {item['article_no']: item for item in existing.data}
            collected_ids = set()
            
            logger.info(f"📋 Found {len(existing_map)} existing active properties in database")
            
            # Process each property
            for processed_prop in processed_properties:
                article_no = processed_prop['article_no']
                collected_ids.add(article_no)
                
                try:
                    if article_no not in existing_map:
                        # New property - insert
                        self.client.table('properties').upsert(processed_prop).execute()
                        db_stats['new_count'] += 1
                        if debug_mode:
                            logger.info(f"✅ New property inserted: {article_no}")
                    else:
                        # Existing property - check for updates
                        existing_property = existing_map[article_no]
                        old_price = existing_property['price']
                        old_rent_price = existing_property.get('rent_price', 0)
                        
                        new_price = processed_prop['price']
                        new_rent_price = processed_prop['rent_price']
                        
                        price_changed = old_price != new_price
                        rent_changed = old_rent_price != new_rent_price
                        
                        if price_changed or rent_changed:
                            # Update with price change
                            update_data = {
                                'price': new_price,
                                'rent_price': new_rent_price,
                                'last_seen_date': today.isoformat(),
                                'updated_at': datetime.now().isoformat()
                            }
                            
                            self.client.table('properties')\
                                .update(update_data)\
                                .eq('article_no', article_no)\
                                .execute()
                            
                            db_stats['updated_count'] += 1
                            
                            if debug_mode:
                                logger.info(f"🔄 Price updated: {article_no} - {old_price} → {new_price}")
                        else:
                            # No price change - update last_seen_date only
                            self.client.table('properties')\
                                .update({'last_seen_date': today.isoformat()})\
                                .eq('article_no', article_no)\
                                .execute()
                    
                    db_stats['total_saved'] += 1
                    
                except Exception as e:
                    db_stats['insertion_errors'].append({
                        'article_no': article_no,
                        'error': str(e)
                    })
                    logger.error(f"❌ Database insertion error for {article_no}: {e}")
            
            # Handle properties that are no longer found (with grace period)
            missing_properties = 0
            for article_no in existing_map:
                if article_no not in collected_ids:
                    # Check last seen date for grace period
                    last_seen_info = self._get_last_seen_date(article_no)
                    if last_seen_info:
                        last_seen_date = last_seen_info['last_seen_date']
                        days_missing = (today - last_seen_date).days
                        
                        if days_missing >= 3:  # 3일 유예기간
                            # Mark as inactive
                            self.client.table('properties')\
                                .update({\
                                    'is_active': False,\
                                    'deleted_at': today.isoformat(),\
                                    'updated_at': datetime.now().isoformat()\
                                })\
                                .eq('article_no', article_no)\
                                .execute()
                            
                            db_stats['removed_count'] += 1
                            missing_properties += 1
                            
                            if debug_mode:
                                logger.info(f"🗑️ Property deactivated: {article_no} ({days_missing} days missing)")
            
            # Final results
            result = {
                'success': True,
                'db_stats': db_stats,
                'processing_stats': stats,
                'processing_errors': processing_errors,
                'summary': {
                    'raw_input': len(raw_properties),
                    'successfully_processed': len(processed_properties),
                    'processing_failures': len(processing_errors),
                    'new_properties': db_stats['new_count'],
                    'updated_properties': db_stats['updated_count'],
                    'removed_properties': db_stats['removed_count'],
                    'insertion_errors': len(db_stats['insertion_errors'])
                }
            }
            
            logger.info(f"✅ Enhanced processing complete: {result['summary']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Database operation failed: {e}")
            return {
                'success': False,
                'error': f"Database operation failed: {e}",
                'processing_stats': stats,
                'processing_errors': processing_errors
            }
    
    def _get_last_seen_date(self, article_no: str) -> Optional[Dict]:
        """Get last seen date for property"""
        try:
            result = self.client.table('properties')\
                .select('last_seen_date, updated_at, collected_date')\
                .eq('article_no', article_no)\
                .single()\
                .execute()
            
            if result.data:
                property_data = result.data
                last_seen_str = property_data.get('last_seen_date') or \
                              property_data.get('updated_at') or \
                              property_data.get('collected_date')
                
                if last_seen_str:
                    try:
                        last_seen_date = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00')).date()
                        return {'last_seen_date': last_seen_date}
                    except:
                        pass
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Last seen date query failed for {article_no}: {e}")
            return None
    
    def validate_data_quality(self, cortar_no: str, days_back: int = 1) -> Dict:
        """Validate data quality for recent insertions"""
        
        cutoff_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        try:
            # Query recent properties
            recent_properties = self.client.table('properties')\
                .select('*')\
                .eq('cortar_no', cortar_no)\
                .gte('collected_date', cutoff_date)\
                .execute()
            
            if not recent_properties.data:
                return {
                    'total_properties': 0,
                    'null_analysis': {},
                    'data_quality_score': 0
                }
            
            properties = recent_properties.data
            total_count = len(properties)
            
            # Analyze NULL values
            null_analysis = {}
            important_fields = [
                'article_no', 'article_name', 'real_estate_type', 'trade_type',
                'price', 'rent_price', 'area1', 'address_road', 'latitude', 'longitude'
            ]
            
            for field in important_fields:
                null_count = sum(1 for prop in properties if prop.get(field) is None or prop.get(field) == '')
                null_percentage = (null_count / total_count) * 100 if total_count > 0 else 0
                
                null_analysis[field] = {
                    'null_count': null_count,
                    'null_percentage': round(null_percentage, 2),
                    'has_data_count': total_count - null_count
                }
            
            # Calculate overall data quality score
            critical_fields = ['article_no', 'article_name', 'real_estate_type', 'trade_type']
            critical_nulls = sum(null_analysis[field]['null_count'] for field in critical_fields)
            critical_total = len(critical_fields) * total_count
            
            data_quality_score = ((critical_total - critical_nulls) / critical_total * 100) if critical_total > 0 else 0
            
            return {
                'total_properties': total_count,
                'date_range': f"Since {cutoff_date}",
                'null_analysis': null_analysis,
                'data_quality_score': round(data_quality_score, 2),
                'summary': {
                    'excellent': data_quality_score >= 95,
                    'good': 90 <= data_quality_score < 95,
                    'needs_improvement': data_quality_score < 90
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Data quality validation failed: {e}")
            return {'error': str(e)}

# Test function
def test_enhanced_client():
    """Test enhanced Supabase client"""
    try:
        client = EnhancedSupabaseHelper()
        
        # Test data quality validation
        quality_report = client.validate_data_quality('1168010100', days_back=7)
        print(f"📊 Data Quality Report: {quality_report}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_enhanced_client()