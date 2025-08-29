#!/usr/bin/env python3
"""
Enhanced Data Processor - Fixed Field Mapping and Validation
Addresses NULL data issues by providing robust field extraction and validation
"""

import json
from typing import Dict, List, Optional, Any, Union
from datetime import date, datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedDataProcessor:
    """Enhanced data processor with robust field mapping and validation"""
    
    def __init__(self):
        self.field_mapping = self._initialize_field_mapping()
        self.validation_stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'field_extraction_failures': {},
            'price_parsing_failures': 0,
            'area_parsing_failures': 0
        }
    
    def _initialize_field_mapping(self) -> Dict[str, List[str]]:
        """Initialize flexible field mapping for Korean/English keys"""
        return {
            'article_no': ['매물번호', 'articleNo', 'article_no', 'id'],
            'article_name': ['매물명', 'articleName', 'article_name', 'name', 'title'],
            'real_estate_type': ['부동산타입', 'realEstateTypeName', 'real_estate_type', 'property_type', 'type'],
            'trade_type': ['거래타입', 'tradeTypeName', 'trade_type', 'transaction_type'],
            'price': ['매매가격', 'dealOrWarrantPrc', 'price', 'deal_price', 'sale_price'],
            'rent_price': ['월세', 'rentPrc', 'rent_price', 'monthly_rent'],
            'area1': ['전용면적', 'area1', 'exclusive_area', 'usable_area'],
            'area2': ['공급면적', 'area2', 'supply_area', 'total_area'],
            'floor_info': ['층정보', 'floorInfo', 'floor_info', 'floor'],
            'direction': ['방향', 'direction', 'orientation'],
            'address': ['주소', 'address', 'location'],
            'address_detail': ['상세주소', 'buildingName', 'address_detail', 'building_name', 'detailed_address'],
            'registration_date': ['등록일', 'articleConfirmYMD', 'registration_date', 'created_date'],
            'tag_list': ['태그', 'tagList', 'tag_list', 'tags'],
            'description': ['설명', 'articleFeatureDesc', 'description', 'feature_desc', 'content']
        }
    
    def safe_extract_field(self, data: Dict, field_key: str, default: Any = None) -> Any:
        """Safely extract field with multiple key fallbacks"""
        possible_keys = self.field_mapping.get(field_key, [field_key])
        
        for key in possible_keys:
            if key in data and data[key] is not None and data[key] != '':
                return data[key]
        
        # Log missing field for debugging
        if field_key not in self.validation_stats['field_extraction_failures']:
            self.validation_stats['field_extraction_failures'][field_key] = 0
        self.validation_stats['field_extraction_failures'][field_key] += 1
        
        return default
    
    def enhanced_parse_price(self, price_data: Any) -> Optional[int]:
        """Enhanced price parsing with multiple format support"""
        if price_data is None or price_data == '':
            return None
            
        try:
            # Handle different data types
            if isinstance(price_data, (int, float)):
                return int(price_data)
            
            if isinstance(price_data, str):
                # Remove common Korean price formatting
                cleaned = price_data.replace(',', '').replace(' ', '').strip()
                
                # Handle Korean format: "5억 3,000만" 
                if '억' in cleaned or '만' in cleaned:
                    # Convert Korean format
                    if '억' in cleaned:
                        parts = cleaned.split('억')
                        eok = int(parts[0]) if parts[0].isdigit() else 0
                        remaining = parts[1] if len(parts) > 1 else ''
                        
                        man = 0
                        if '만' in remaining:
                            man_part = remaining.replace('만', '')
                            if man_part.isdigit():
                                man = int(man_part)
                        elif remaining.isdigit():
                            man = int(remaining)
                        
                        return eok * 10000 + man
                    elif '만' in cleaned:
                        man_part = cleaned.replace('만', '')
                        if man_part.isdigit():
                            return int(man_part)
                
                # Handle pure numeric strings
                if cleaned.isdigit():
                    return int(cleaned)
                
                # Handle decimal numbers
                try:
                    return int(float(cleaned))
                except ValueError:
                    pass
            
            # If all parsing fails, return None
            self.validation_stats['price_parsing_failures'] += 1
            return None
            
        except Exception as e:
            logger.warning(f"Price parsing failed for '{price_data}': {e}")
            self.validation_stats['price_parsing_failures'] += 1
            return None
    
    def enhanced_parse_area(self, area_data: Any) -> Optional[float]:
        """Enhanced area parsing with multiple format support"""
        if area_data is None or area_data == '':
            return None
            
        try:
            # Handle different data types
            if isinstance(area_data, (int, float)):
                return float(area_data)
            
            if isinstance(area_data, str):
                # Remove common area units and formatting
                cleaned = area_data.replace('㎡', '').replace('m²', '').replace('평', '').replace(',', '').strip()
                
                # Handle numeric strings
                if cleaned:
                    try:
                        return float(cleaned)
                    except ValueError:
                        pass
            
            # If all parsing fails, return None
            self.validation_stats['area_parsing_failures'] += 1
            return None
            
        except Exception as e:
            logger.warning(f"Area parsing failed for '{area_data}': {e}")
            self.validation_stats['area_parsing_failures'] += 1
            return None
    
    def process_collected_property(self, raw_property: Dict, cortar_no: str, 
                                 collected_date: date = None) -> Dict:
        """Process raw property data into clean database record"""
        if collected_date is None:
            collected_date = date.today()
        
        self.validation_stats['total_processed'] += 1
        
        try:
            # Extract basic property information with fallbacks
            processed_property = {
                'article_no': self.safe_extract_field(raw_property, 'article_no'),
                'cortar_no': cortar_no,
                'article_name': self.safe_extract_field(raw_property, 'article_name', ''),
                'real_estate_type': self.safe_extract_field(raw_property, 'real_estate_type', ''),
                'trade_type': self.safe_extract_field(raw_property, 'trade_type', ''),
                'price': self.enhanced_parse_price(self.safe_extract_field(raw_property, 'price')),
                'rent_price': self.enhanced_parse_price(self.safe_extract_field(raw_property, 'rent_price')),
                'area1': self.enhanced_parse_area(self.safe_extract_field(raw_property, 'area1')),
                'area2': self.enhanced_parse_area(self.safe_extract_field(raw_property, 'area2')),
                'floor_info': self.safe_extract_field(raw_property, 'floor_info', ''),
                'direction': self.safe_extract_field(raw_property, 'direction', ''),
                'address_detail': self.safe_extract_field(raw_property, 'address_detail', ''),
                'tag_list': self.safe_extract_field(raw_property, 'tag_list', []),
                'description': self.safe_extract_field(raw_property, 'description', ''),
                'collected_date': collected_date.isoformat(),
                'last_seen_date': collected_date.isoformat(),
                'is_active': True
            }
            
            # Process detailed information if available
            details_info = raw_property.get('상세정보') or raw_property.get('details') or {}
            if details_info:
                processed_property.update(self._process_detailed_info(details_info))
            
            # Store raw details for future reference
            processed_property['details'] = details_info
            
            # Validate required fields
            if self._validate_required_fields(processed_property):
                self.validation_stats['successful_extractions'] += 1
                return processed_property
            else:
                logger.warning(f"Required field validation failed for article {processed_property.get('article_no')}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to process property: {e}")
            return None
    
    def _process_detailed_info(self, details: Dict) -> Dict:
        """Process detailed property information from API response"""
        processed_details = {}
        
        # Extract location information
        location_info = details.get('위치정보', {})
        if location_info:
            processed_details.update({
                'latitude': location_info.get('정확한_위도'),
                'longitude': location_info.get('정확한_경도'),
                'address_detail': location_info.get('상세주소', '')
            })
        
        # Extract address information from Kakao conversion
        kakao_addr = details.get('카카오주소변환', {})
        if kakao_addr:
            processed_details.update({
                'address_road': kakao_addr.get('도로명주소', ''),
                'address_jibun': kakao_addr.get('지번주소', ''),
                'building_name': kakao_addr.get('건물명', ''),
                'postal_code': kakao_addr.get('우편번호', '')
            })
        
        # Set defaults for missing address fields
        processed_details.setdefault('address_road', '')
        processed_details.setdefault('address_jibun', '')  
        processed_details.setdefault('building_name', '')
        processed_details.setdefault('postal_code', '')
        processed_details.setdefault('latitude', None)
        processed_details.setdefault('longitude', None)
        
        return processed_details
    
    def _validate_required_fields(self, property_record: Dict) -> bool:
        """Validate that required fields are present and valid"""
        required_fields = ['article_no', 'cortar_no']
        
        for field in required_fields:
            if not property_record.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate article_no is not empty string
        if not str(property_record['article_no']).strip():
            logger.warning("article_no is empty")
            return False
            
        return True
    
    def process_api_response_batch(self, api_articles: List[Dict], cortar_no: str) -> List[Dict]:
        """Process batch of API articles into database-ready records"""
        processed_batch = []
        
        for raw_article in api_articles:
            # Convert API response format to expected format
            converted_article = self._convert_api_response(raw_article)
            
            # Process with enhanced processor
            processed_property = self.process_collected_property(converted_article, cortar_no)
            
            if processed_property:
                processed_batch.append(processed_property)
        
        logger.info(f"Processed {len(processed_batch)}/{len(api_articles)} articles successfully")
        return processed_batch
    
    def _convert_api_response(self, api_article: Dict) -> Dict:
        """Convert raw API response to expected format for processing"""
        # This handles the mismatch between API response format and expected format
        converted = {
            '매물번호': api_article.get('articleNo'),
            '매물명': api_article.get('articleName'),
            '부동산타입': api_article.get('realEstateTypeName'),
            '거래타입': api_article.get('tradeTypeName'),
            '매매가격': api_article.get('dealOrWarrantPrc', ''),
            '월세': api_article.get('rentPrc', ''),
            '전용면적': api_article.get('area1'),
            '공급면적': api_article.get('area2'),
            '층정보': api_article.get('floorInfo'),
            '방향': api_article.get('direction'),
            '주소': api_article.get('address', ''),
            '상세주소': api_article.get('buildingName', ''),
            '등록일': api_article.get('articleConfirmYMD'),
            '태그': api_article.get('tagList', []),
            '설명': api_article.get('articleFeatureDesc', '')
        }
        
        # Add detailed information if present
        if '상세정보' in api_article:
            converted['상세정보'] = api_article['상세정보']
        
        return converted
    
    def get_validation_stats(self) -> Dict:
        """Get validation and processing statistics"""
        return self.validation_stats.copy()
    
    def reset_stats(self):
        """Reset validation statistics"""
        self.validation_stats = {
            'total_processed': 0,
            'successful_extractions': 0,
            'field_extraction_failures': {},
            'price_parsing_failures': 0,
            'area_parsing_failures': 0
        }

# Test function
def test_processor():
    """Test the enhanced data processor"""
    processor = EnhancedDataProcessor()
    
    # Test data with mixed formats
    test_properties = [
        {
            'articleNo': '12345',
            'articleName': 'Test Property 1',
            'realEstateTypeName': '아파트',
            'tradeTypeName': '매매',
            'dealOrWarrantPrc': '5억 3,000',
            'area1': '84.5㎡',
            'floorInfo': '5/15층'
        },
        {
            '매물번호': '67890',
            '매물명': 'Test Property 2',
            '부동산타입': '오피스텔',
            '거래타입': '전세',
            '매매가격': 500000,
            '전용면적': 65.2
        }
    ]
    
    for prop in test_properties:
        result = processor.process_collected_property(prop, '1168010100')
        print(f"Processed: {result['article_no']} - Success: {result is not None}")
    
    print(f"Stats: {processor.get_validation_stats()}")

if __name__ == "__main__":
    test_processor()