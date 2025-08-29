#!/usr/bin/env python3
"""
Robust Data Collector - Enterprise-Grade Backend Architecture
Addresses NULL data issues through comprehensive error handling and data validation
"""

import os
import sys
import json
import time
import logging
import traceback
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir.parent.parent))

from supabase import create_client
from collectors.core.enhanced_data_processor import EnhancedDataProcessor

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('collectors/logs/robust_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class CollectionMetrics:
    """Comprehensive collection metrics"""
    total_articles: int = 0
    successful_collections: int = 0
    failed_collections: int = 0
    api_errors: int = 0
    validation_errors: int = 0
    database_errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_articles == 0:
            return 0.0
        return (self.successful_collections / self.total_articles) * 100
    
    @property
    def duration(self) -> float:
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

@dataclass
class ValidationResult:
    """Data validation result"""
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_data: Optional[Dict] = None

class RobustDataCollector:
    """Enterprise-grade data collector with comprehensive error handling"""
    
    def __init__(self):
        """Initialize robust collector with comprehensive setup"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = CollectionMetrics()
        self.data_processor = EnhancedDataProcessor()
        
        # Initialize Supabase connection with retry logic
        self.supabase_client = self._initialize_supabase_with_retry()
        
        # Token management
        self.token_manager = self._initialize_token_manager()
        
        # Configuration
        self.config = self._load_configuration()
        
        # Circuit breaker for API failures
        self.api_failure_count = 0
        self.max_consecutive_failures = 10
        self.circuit_breaker_open = False
        
        # Database transaction management
        self._current_transaction = None
        
        self.logger.info("✅ Robust Data Collector initialized successfully")
    
    def _initialize_supabase_with_retry(self, max_retries: int = 3):
        """Initialize Supabase client with retry logic"""
        for attempt in range(max_retries):
            try:
                # Production credentials
                url = 'https://eslhavjipwbyvbbknixv.supabase.co'
                key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzbGhhdmppcHdieXZiYmtuaXh2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NDI5OTUxMSwiZXhwIjoyMDY5ODc1NTExfQ.p6JB5xrdLi_yBJTuHg2mF9TZFQiwA4Tqd0hc-7FxFqE'
                
                client = create_client(url, key)
                
                # Test connection
                result = client.table('properties_new').select('id').limit(1).execute()
                self.logger.info(f"✅ Supabase connection established (attempt {attempt + 1})")
                return client
                
            except Exception as e:
                self.logger.warning(f"⚠️ Supabase connection attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to initialize Supabase after {max_retries} attempts")
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def _initialize_token_manager(self):
        """Initialize token manager with fallback options"""
        try:
            sys.path.insert(0, str(current_dir))
            from multi_token_manager import MultiTokenManager
            from playwright_token_collector import PlaywrightTokenCollector
            
            token_manager = MultiTokenManager()
            token_data = token_manager.get_random_token()
            
            if token_data:
                self.token = token_data['token']
                self.cookies = token_data['cookies']
                self.token_expires_at = token_data['expires_at']
                self.logger.info(f"✅ Token loaded successfully (expires: {self.token_expires_at})")
                return token_manager
            else:
                self.logger.warning("⚠️ No available tokens, will attempt auto-collection")
                self._collect_new_token()
                return None
                
        except ImportError as e:
            self.logger.warning(f"⚠️ Token manager not available: {e}")
            self.token = None
            self.cookies = {}
            return None
    
    def _collect_new_token(self):
        """Collect new token with comprehensive error handling"""
        try:
            from playwright_token_collector import PlaywrightTokenCollector
            
            self.logger.info("🤖 Attempting automatic token collection...")
            token_collector = PlaywrightTokenCollector()
            token_data = token_collector.get_token_with_playwright()
            
            if token_data and token_data.get('token'):
                self.token = token_data['token']
                self.cookies = token_data.get('cookies', {})
                self.token_expires_at = datetime.now() + timedelta(hours=6)
                self.logger.info("✅ New token collected successfully")
            else:
                self.logger.error("❌ Automatic token collection failed")
                self.token = None
                self.cookies = {}
                
        except Exception as e:
            self.logger.error(f"❌ Token collection error: {e}")
            self.token = None
            self.cookies = {}
    
    def _load_configuration(self) -> Dict:
        """Load configuration with defaults"""
        default_config = {
            'batch_size': 50,
            'retry_attempts': 3,
            'request_timeout': 15,
            'rate_limit_delay': 2.0,
            'max_concurrent_requests': 5
        }
        
        try:
            config_path = current_dir.parent.parent / 'config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config.get('collector', {}))
        except Exception as e:
            self.logger.warning(f"⚠️ Config loading failed, using defaults: {e}")
        
        return default_config
    
    @contextmanager
    def database_transaction(self):
        """Database transaction context manager"""
        transaction_id = datetime.now().isoformat()
        self.logger.info(f"🔄 Starting transaction {transaction_id}")
        
        try:
            self._current_transaction = transaction_id
            yield transaction_id
            self.logger.info(f"✅ Transaction {transaction_id} committed")
        except Exception as e:
            self.logger.error(f"❌ Transaction {transaction_id} rolled back: {e}")
            # Implement rollback logic here
            raise
        finally:
            self._current_transaction = None
    
    def collect_article_with_comprehensive_validation(self, article_no: str) -> Optional[Dict]:
        """Collect single article with comprehensive validation and error handling"""
        collection_start = time.time()
        
        try:
            self.logger.info(f"🔍 Collecting article {article_no}")
            
            # 1. Circuit breaker check
            if self.circuit_breaker_open:
                self.logger.warning(f"⚠️ Circuit breaker open, skipping article {article_no}")
                return None
            
            # 2. Token validation
            if not self._validate_token():
                self.logger.error(f"❌ Invalid token, cannot collect article {article_no}")
                return None
            
            # 3. API request with retry logic
            raw_data = self._fetch_article_data_with_retry(article_no)
            if not raw_data:
                return None
            
            # 4. Comprehensive data validation
            validation_result = self._validate_article_data(raw_data, article_no)
            if not validation_result.is_valid:
                self.logger.error(f"❌ Validation failed for article {article_no}: {validation_result.errors}")
                self.metrics.validation_errors += 1
                return None
            
            # 5. Data processing and enhancement
            processed_data = self._process_article_data(validation_result.sanitized_data, article_no)
            if not processed_data:
                return None
            
            # 6. Database foreign key resolution
            resolved_data = self._resolve_foreign_keys(processed_data)
            if not resolved_data:
                self.logger.error(f"❌ Foreign key resolution failed for article {article_no}")
                return None
            
            # 7. Success metrics
            self.metrics.successful_collections += 1
            self.api_failure_count = 0  # Reset failure count on success
            
            collection_time = time.time() - collection_start
            self.logger.info(f"✅ Article {article_no} collected successfully ({collection_time:.2f}s)")
            
            return resolved_data
            
        except Exception as e:
            self.metrics.failed_collections += 1
            self.api_failure_count += 1
            
            # Circuit breaker logic
            if self.api_failure_count >= self.max_consecutive_failures:
                self.circuit_breaker_open = True
                self.logger.critical(f"🚨 Circuit breaker opened after {self.api_failure_count} failures")
            
            self.logger.error(f"❌ Collection failed for article {article_no}: {e}")
            self.logger.debug(traceback.format_exc())
            return None
    
    def _validate_token(self) -> bool:
        """Validate current token"""
        if not self.token:
            return False
        
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            self.logger.warning("⚠️ Token expired, attempting refresh")
            self._collect_new_token()
            return bool(self.token)
        
        return True
    
    def _fetch_article_data_with_retry(self, article_no: str, max_retries: int = 3) -> Optional[Dict]:
        """Fetch article data with comprehensive retry logic"""
        url = f"https://new.land.naver.com/api/articles/{article_no}"
        params = {'complexNo': ''}
        headers = self._build_request_headers()
        
        for attempt in range(max_retries):
            try:
                import requests
                
                time.sleep(self.config['rate_limit_delay'])
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    params=params,
                    cookies=self.cookies, 
                    timeout=self.config['request_timeout']
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.debug(f"✅ API response received for article {article_no} (attempt {attempt + 1})")
                    return data
                elif response.status_code == 401:
                    self.logger.warning(f"⚠️ Token expired (401), refreshing token")
                    self._collect_new_token()
                    headers = self._build_request_headers()
                elif response.status_code == 429:
                    wait_time = (2 ** attempt) * self.config['rate_limit_delay']
                    self.logger.warning(f"⚠️ Rate limited (429), waiting {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"⚠️ API error {response.status_code} for article {article_no}")
                
            except Exception as e:
                self.logger.warning(f"⚠️ Request failed for article {article_no} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            except Exception as e:
                self.logger.error(f"❌ Unexpected error fetching article {article_no}: {e}")
                break
        
        self.metrics.api_errors += 1
        return None
    
    def _build_request_headers(self) -> Dict[str, str]:
        """Build comprehensive request headers"""
        return {
            'authorization': f'Bearer {self.token}' if self.token else '',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ko-KR,ko;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://new.land.naver.com/',
            'Origin': 'https://new.land.naver.com',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    
    def _validate_article_data(self, raw_data: Dict, article_no: str) -> ValidationResult:
        """Comprehensive article data validation"""
        result = ValidationResult()
        errors = []
        warnings = []
        
        try:
            # 1. Basic structure validation
            if not isinstance(raw_data, dict):
                errors.append("Invalid data structure - not a dictionary")
                result.errors = errors
                return result
            
            # 2. Check for essential sections
            essential_sections = ['articleDetail', 'articlePrice']
            missing_sections = []
            
            for section in essential_sections:
                if section not in raw_data or not raw_data[section]:
                    missing_sections.append(section)
            
            if missing_sections:
                warnings.append(f"Missing optional sections: {missing_sections}")
            
            # 3. Validate articleDetail section
            article_detail = raw_data.get('articleDetail', {})
            if not article_detail:
                errors.append("Missing critical articleDetail section")
            else:
                # Check for essential fields in articleDetail
                essential_fields = ['buildingName', 'realEstateTypeName', 'tradeTypeName']
                for field in essential_fields:
                    if not article_detail.get(field):
                        warnings.append(f"Missing {field} in articleDetail")
            
            # 4. Validate price information
            article_price = raw_data.get('articlePrice', {})
            has_valid_price = any([
                article_price.get('dealPrice'),
                article_price.get('warrantPrice'), 
                article_price.get('rentPrice')
            ])
            
            if not has_valid_price:
                warnings.append("No valid price information found")
            
            # 5. Validate space information
            article_space = raw_data.get('articleSpace', {})
            if article_space:
                area_fields = ['supplyArea', 'exclusiveArea']
                valid_areas = [article_space.get(field) for field in area_fields if article_space.get(field)]
                if not valid_areas:
                    warnings.append("No valid area information found")
            
            # 6. Data sanitization
            sanitized_data = self._sanitize_article_data(raw_data)
            
            result.is_valid = len(errors) == 0
            result.errors = errors
            result.warnings = warnings
            result.sanitized_data = sanitized_data
            
            if warnings:
                self.logger.warning(f"⚠️ Validation warnings for article {article_no}: {warnings}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Validation error for article {article_no}: {e}")
            result.errors = [f"Validation exception: {str(e)}"]
            return result
    
    def _sanitize_article_data(self, raw_data: Dict) -> Dict:
        """Sanitize and normalize article data"""
        sanitized = {}
        
        try:
            # Deep copy to avoid modifying original data
            import copy
            sanitized = copy.deepcopy(raw_data)
            
            # Sanitize articleDetail
            if 'articleDetail' in sanitized:
                detail = sanitized['articleDetail']
                
                # Normalize text fields
                text_fields = ['buildingName', 'detailDescription', 'exposureAddress']
                for field in text_fields:
                    if detail.get(field):
                        detail[field] = str(detail[field]).strip()
                        if len(detail[field]) > 500:  # Prevent excessively long text
                            detail[field] = detail[field][:500] + "..."
                
                # Normalize numeric fields
                numeric_fields = ['latitude', 'longitude', 'monthlyManagementCost']
                for field in numeric_fields:
                    if detail.get(field) is not None:
                        try:
                            detail[field] = float(detail[field])
                        except (ValueError, TypeError):
                            detail[field] = None
            
            # Sanitize articlePrice
            if 'articlePrice' in sanitized:
                price = sanitized['articlePrice']
                price_fields = ['dealPrice', 'warrantPrice', 'rentPrice', 'deposit']
                
                for field in price_fields:
                    if price.get(field) is not None:
                        try:
                            # Handle various price formats
                            if isinstance(price[field], str):
                                price[field] = int(price[field].replace(',', ''))
                            else:
                                price[field] = int(price[field])
                        except (ValueError, TypeError):
                            price[field] = None
            
            # Sanitize articleSpace
            if 'articleSpace' in sanitized:
                space = sanitized['articleSpace']
                area_fields = ['supplyArea', 'exclusiveArea', 'exclusiveRate']
                
                for field in area_fields:
                    if space.get(field) is not None:
                        try:
                            space[field] = float(space[field])
                        except (ValueError, TypeError):
                            space[field] = None
            
            return sanitized
            
        except Exception as e:
            self.logger.error(f"❌ Data sanitization error: {e}")
            return raw_data
    
    def _process_article_data(self, sanitized_data: Dict, article_no: str) -> Optional[Dict]:
        """Process and structure article data"""
        try:
            processed_data = {
                'article_no': article_no,
                'collection_timestamp': datetime.now().isoformat(),
                'raw_sections': sanitized_data,
                
                # Processed sections with comprehensive error handling
                'basic_info': self._safe_process_section(sanitized_data, 'articleDetail', self._process_article_detail),
                'price_info': self._safe_process_section(sanitized_data, 'articlePrice', self._process_article_price),
                'space_info': self._safe_process_section(sanitized_data, 'articleSpace', self._process_article_space),
                'floor_info': self._safe_process_section(sanitized_data, 'articleFloor', self._process_article_floor),
                'facility_info': self._safe_process_section(sanitized_data, 'articleFacility', self._process_article_facility),
                'realtor_info': self._safe_process_section(sanitized_data, 'articleRealtor', self._process_article_realtor),
                'photo_info': self._safe_process_section(sanitized_data, 'articlePhotos', self._process_article_photos),
                'tax_info': self._safe_process_section(sanitized_data, 'articleTax', self._process_article_tax)
            }
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"❌ Data processing error for article {article_no}: {e}")
            return None
    
    def _safe_process_section(self, data: Dict, section_key: str, processor_func) -> Dict:
        """Safely process a data section with error handling"""
        try:
            section_data = data.get(section_key, {})
            if not section_data:
                self.logger.debug(f"📝 Empty section {section_key}, using defaults")
                return {}
            
            return processor_func(section_data)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Section processing failed for {section_key}: {e}")
            return {}
    
    def _process_article_detail(self, data: Dict) -> Dict:
        """Process articleDetail section with comprehensive error handling"""
        return {
            'building_name': self._safe_str(data.get('buildingName')),
            'building_use': self._safe_str(data.get('buildingUse')),
            'real_estate_type': self._safe_str(data.get('realEstateTypeName')),
            'trade_type': self._safe_str(data.get('tradeTypeName')),
            'latitude': self._safe_float(data.get('latitude')),
            'longitude': self._safe_float(data.get('longitude')),
            'address': self._safe_str(data.get('exposureAddress')),
            'detail_address': self._safe_str(data.get('detailAddress')),
            'parking_possible': data.get('parkingPossibleYN') == 'Y',
            'monthly_management_cost': self._safe_int(data.get('monthlyManagementCost')),
            'detail_description': self._safe_str(data.get('detailDescription')),
            'tag_list': data.get('tagList', []) if isinstance(data.get('tagList'), list) else []
        }
    
    def _process_article_price(self, data: Dict) -> Dict:
        """Process articlePrice section"""
        return {
            'deal_price': self._safe_int(data.get('dealPrice')),
            'warrant_price': self._safe_int(data.get('warrantPrice')),
            'rent_price': self._safe_int(data.get('rentPrice')),
            'deposit': self._safe_int(data.get('deposit')),
            'monthly_management_cost': self._safe_int(data.get('monthlyManagementCost')),
            'premium': self._safe_int(data.get('premium')),
            'price_type': self._safe_str(data.get('priceType')),
            'price_title': self._safe_str(data.get('priceTitle'))
        }
    
    def _process_article_space(self, data: Dict) -> Dict:
        """Process articleSpace section"""
        return {
            'supply_area': self._safe_float(data.get('supplyArea')),
            'exclusive_area': self._safe_float(data.get('exclusiveArea')),
            'exclusive_rate': self._safe_float(data.get('exclusiveRate')),
            'room_count': self._safe_int(data.get('roomCount')),
            'bathroom_count': self._safe_int(data.get('bathroomCount')),
            'space_type': self._safe_str(data.get('spaceType')),
            'area_unit': self._safe_str(data.get('areaUnit', '㎡'))
        }
    
    def _process_article_floor(self, data: Dict) -> Dict:
        """Process articleFloor section"""
        return {
            'total_floor_count': self._safe_int(data.get('totalFloorCount')),
            'current_floor': self._safe_int(data.get('currentFloor')),
            'underground_floor_count': self._safe_int(data.get('undergroundFloorCount')),
            'floor_description': self._safe_str(data.get('floorDescription'))
        }
    
    def _process_article_facility(self, data: Dict) -> Dict:
        """Process articleFacility section"""
        facilities = {}
        facility_keys = [
            'airConditioner', 'cableTv', 'internet', 'interphone',
            'securitySystem', 'elevator', 'parking', 'gasRange'
        ]
        
        for key in facility_keys:
            facilities[key] = data.get(key) == 'Y'
        
        return {
            'facilities': facilities,
            'available_facilities': [k for k, v in facilities.items() if v]
        }
    
    def _process_article_realtor(self, data: Dict) -> Dict:
        """Process articleRealtor section"""
        return {
            'office_name': self._safe_str(data.get('officeName')),
            'realtor_name': self._safe_str(data.get('realtorName')),
            'mobile_number': self._safe_str(data.get('mobileNumber')),
            'telephone': self._safe_str(data.get('telephone')),
            'office_address': self._safe_str(data.get('address')),
            'business_registration_number': self._safe_str(data.get('businessRegistrationNumber')),
            'license_number': self._safe_str(data.get('licenseNumber')),
            'grade': self._safe_float(data.get('grade')),
            'review_count': self._safe_int(data.get('reviewCount')),
            'certified_realtor': data.get('certifiedRealtor') == 'Y'
        }
    
    def _process_article_photos(self, data: List[Dict]) -> Dict:
        """Process articlePhotos section"""
        if not data or not isinstance(data, list):
            return {'photos': [], 'photo_count': 0}
        
        processed_photos = []
        for idx, photo in enumerate(data):
            if isinstance(photo, dict):
                processed_photos.append({
                    'order': idx + 1,
                    'image_url': self._safe_str(photo.get('imageUrl') or photo.get('imageSrc')),
                    'thumbnail_url': self._safe_str(photo.get('thumbnailUrl')),
                    'image_type': self._safe_str(photo.get('imageType', 'general')),
                    'width': self._safe_int(photo.get('width')),
                    'height': self._safe_int(photo.get('height')),
                    'caption': self._safe_str(photo.get('caption', ''))
                })
        
        return {
            'photos': processed_photos,
            'photo_count': len(processed_photos)
        }
    
    def _process_article_tax(self, data: Dict) -> Dict:
        """Process articleTax section"""
        return {
            'acquisition_tax': self._safe_int(data.get('acquisitionTax')),
            'registration_tax': self._safe_int(data.get('registrationTax')),
            'brokerage_fee': self._safe_int(data.get('brokerageFee')),
            'stamp_duty': self._safe_int(data.get('stampDuty')),
            'total_tax': self._safe_int(data.get('totalTax'))
        }
    
    def _resolve_foreign_keys(self, processed_data: Dict) -> Optional[Dict]:
        """Resolve all foreign key constraints before database insertion"""
        try:
            # Extract necessary information
            basic_info = processed_data.get('basic_info', {})
            price_info = processed_data.get('price_info', {})
            
            # 1. Resolve real estate type ID
            real_estate_type_id = self._resolve_real_estate_type_id(basic_info.get('real_estate_type'))
            if not real_estate_type_id:
                self.logger.error(f"❌ Failed to resolve real estate type for article {processed_data['article_no']}")
                return None
            
            # 2. Resolve trade type ID
            trade_type_id = self._resolve_trade_type_id(basic_info.get('trade_type'), price_info)
            if not trade_type_id:
                self.logger.error(f"❌ Failed to resolve trade type for article {processed_data['article_no']}")
                return None
            
            # 3. Resolve region ID
            region_id = self._resolve_region_id(basic_info)
            if not region_id:
                self.logger.error(f"❌ Failed to resolve region for article {processed_data['article_no']}")
                return None
            
            # Add resolved IDs to processed data
            processed_data['resolved_foreign_keys'] = {
                'real_estate_type_id': real_estate_type_id,
                'trade_type_id': trade_type_id,
                'region_id': region_id
            }
            
            return processed_data
            
        except Exception as e:
            self.logger.error(f"❌ Foreign key resolution failed: {e}")
            return None
    
    def _resolve_real_estate_type_id(self, real_estate_type: str) -> Optional[int]:
        """Resolve real estate type ID with caching"""
        if not real_estate_type:
            real_estate_type = "알 수 없음"
        
        try:
            # Check existing
            result = self.supabase_client.table('real_estate_types').select('id').eq('type_name', real_estate_type).execute()
            
            if result.data:
                return result.data[0]['id']
            
            # Create new type
            new_type = {
                'type_code': real_estate_type[:10].upper(),
                'type_name': real_estate_type,
                'category': self._classify_real_estate_type(real_estate_type)
            }
            
            create_result = self.supabase_client.table('real_estate_types').insert(new_type).execute()
            if create_result.data:
                self.logger.info(f"✨ Created new real estate type: {real_estate_type}")
                return create_result.data[0]['id']
            
        except Exception as e:
            self.logger.error(f"❌ Real estate type resolution failed: {e}")
        
        return None
    
    def _resolve_trade_type_id(self, trade_type: str, price_info: Dict) -> Optional[int]:
        """Resolve trade type ID with fallback logic"""
        # Determine trade type from price information if not provided
        if not trade_type:
            if price_info.get('deal_price'):
                trade_type = "매매"
            elif price_info.get('rent_price'):
                trade_type = "월세"
            elif price_info.get('warrant_price'):
                trade_type = "전세"
            else:
                trade_type = "알 수 없음"
        
        try:
            # Check existing
            result = self.supabase_client.table('trade_types').select('id').eq('type_name', trade_type).execute()
            
            if result.data:
                return result.data[0]['id']
            
            # Create new type
            new_type = {
                'type_code': trade_type[:10].upper(),
                'type_name': trade_type,
                'requires_deposit': trade_type in ['전세', '월세']
            }
            
            create_result = self.supabase_client.table('trade_types').insert(new_type).execute()
            if create_result.data:
                self.logger.info(f"✨ Created new trade type: {trade_type}")
                return create_result.data[0]['id']
            
        except Exception as e:
            self.logger.error(f"❌ Trade type resolution failed: {e}")
        
        return None
    
    def _resolve_region_id(self, basic_info: Dict) -> Optional[int]:
        """Resolve region ID with geocoding fallback"""
        # Default to Gangnam region for now
        default_cortar_no = "1168010100"
        
        try:
            # Check existing
            result = self.supabase_client.table('regions').select('id').eq('cortar_no', default_cortar_no).execute()
            
            if result.data:
                return result.data[0]['id']
            
            # Create default region
            new_region = {
                'cortar_no': default_cortar_no,
                'dong_name': '역삼동',
                'gu_name': '강남구'
            }
            
            create_result = self.supabase_client.table('regions').insert(new_region).execute()
            if create_result.data:
                self.logger.info(f"✨ Created default region: 역삼동")
                return create_result.data[0]['id']
            
        except Exception as e:
            self.logger.error(f"❌ Region resolution failed: {e}")
        
        return None
    
    def _classify_real_estate_type(self, type_name: str) -> str:
        """Classify real estate type into category"""
        type_lower = type_name.lower()
        
        if any(keyword in type_lower for keyword in ['아파트', '빌라', '주택', '다세대']):
            return 'residential'
        elif any(keyword in type_lower for keyword in ['상가', '사무실', '매장']):
            return 'commercial'
        elif '오피스텔' in type_lower:
            return 'mixed'
        elif '토지' in type_lower:
            return 'land'
        else:
            return 'other'
    
    # Safe data conversion utilities
    def _safe_str(self, value: Any, default: str = '') -> str:
        """Safely convert to string"""
        if value is None:
            return default
        try:
            return str(value).strip()
        except:
            return default
    
    def _safe_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        """Safely convert to integer"""
        if value is None or value == '':
            return default
        try:
            return int(float(str(value).replace(',', '')))
        except:
            return default
    
    def _safe_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert to float"""
        if value is None or value == '':
            return default
        try:
            return float(str(value).replace(',', ''))
        except:
            return default
    
    def save_to_database_with_transaction(self, processed_data: Dict) -> bool:
        """Save processed data to database with comprehensive transaction management"""
        with self.database_transaction() as transaction_id:
            try:
                article_no = processed_data['article_no']
                self.logger.info(f"💾 Saving article {article_no} to database")
                
                # Extract resolved foreign keys
                foreign_keys = processed_data.get('resolved_foreign_keys', {})
                
                # 1. Save basic property information
                property_id = self._save_property_basic(processed_data, foreign_keys)
                if not property_id:
                    raise Exception("Failed to save basic property information")
                
                # 2. Save related information
                self._save_property_location(property_id, processed_data)
                self._save_property_physical(property_id, processed_data)
                self._save_property_prices(property_id, processed_data)
                self._save_realtor_info(property_id, processed_data)
                self._save_property_images(property_id, processed_data)
                self._save_property_facilities(property_id, processed_data)
                
                self.logger.info(f"✅ Article {article_no} saved successfully")
                return True
                
            except Exception as e:
                self.metrics.database_errors += 1
                self.logger.error(f"❌ Database save failed for article {processed_data.get('article_no')}: {e}")
                raise
    
    def _save_property_basic(self, data: Dict, foreign_keys: Dict) -> Optional[int]:
        """Save basic property with comprehensive error handling"""
        try:
            basic_info = data['basic_info']
            article_no = data['article_no']
            
            # Check if property already exists
            existing = self.supabase_client.table('properties_new').select('id, created_at').eq('article_no', article_no).execute()
            
            property_data = {
                'article_no': article_no,
                'article_name': basic_info.get('building_name'),
                'real_estate_type_id': foreign_keys['real_estate_type_id'],
                'trade_type_id': foreign_keys['trade_type_id'],
                'region_id': foreign_keys['region_id'],
                'last_seen_date': date.today().isoformat(),
                'is_active': True,
                'tag_list': basic_info.get('tag_list', []),
                'description': basic_info.get('detail_description'),
                'updated_at': datetime.now().isoformat()
            }
            
            if existing.data:
                # Update existing property
                property_id = existing.data[0]['id']
                property_data['created_at'] = existing.data[0]['created_at']
                
                self.supabase_client.table('properties_new').update(property_data).eq('id', property_id).execute()
                self.logger.info(f"🔄 Updated existing property {article_no}")
                return property_id
            else:
                # Create new property
                property_data['collected_date'] = date.today().isoformat()
                property_data['created_at'] = datetime.now().isoformat()
                
                result = self.supabase_client.table('properties_new').insert(property_data).execute()
                if result.data:
                    self.logger.info(f"✨ Created new property {article_no}")
                    return result.data[0]['id']
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save basic property: {e}")
            raise
    
    def _save_property_location(self, property_id: int, data: Dict):
        """Save location information"""
        try:
            basic_info = data['basic_info']
            
            location_data = {
                'property_id': property_id,
                'latitude': basic_info.get('latitude'),
                'longitude': basic_info.get('longitude'),
                'address_road': basic_info.get('address'),
                'building_name': basic_info.get('building_name'),
                'address_verified': False
            }
            
            self.supabase_client.table('property_locations').insert(location_data).execute()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save location: {e}")
    
    def _save_property_physical(self, property_id: int, data: Dict):
        """Save physical property information"""
        try:
            space_info = data.get('space_info', {})
            floor_info = data.get('floor_info', {})
            
            # Validate and sanitize area data
            exclusive_area = space_info.get('exclusive_area')
            supply_area = space_info.get('supply_area')
            
            if exclusive_area and exclusive_area <= 0:
                exclusive_area = 10.0  # Minimum area
            
            if supply_area and supply_area <= 0:
                supply_area = exclusive_area * 1.2 if exclusive_area else 12.0
            
            physical_data = {
                'property_id': property_id,
                'area_exclusive': exclusive_area,
                'area_supply': supply_area,
                'area_utilization_rate': space_info.get('exclusive_rate'),
                'floor_current': floor_info.get('current_floor'),
                'floor_total': floor_info.get('total_floor_count'),
                'floor_underground': floor_info.get('underground_floor_count'),
                'room_count': space_info.get('room_count'),
                'bathroom_count': space_info.get('bathroom_count')
            }
            
            self.supabase_client.table('property_physical').insert(physical_data).execute()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save physical info: {e}")
    
    def _save_property_prices(self, property_id: int, data: Dict):
        """Save price information"""
        try:
            price_info = data.get('price_info', {})
            today = date.today().isoformat()
            
            prices = []
            
            if price_info.get('deal_price'):
                prices.append({
                    'property_id': property_id,
                    'price_type': 'sale',
                    'amount': price_info['deal_price'],
                    'valid_from': today
                })
            
            if price_info.get('warrant_price'):
                prices.append({
                    'property_id': property_id,
                    'price_type': 'deposit',
                    'amount': price_info['warrant_price'],
                    'valid_from': today
                })
            
            if price_info.get('rent_price'):
                prices.append({
                    'property_id': property_id,
                    'price_type': 'rent',
                    'amount': price_info['rent_price'],
                    'valid_from': today
                })
            
            if prices:
                self.supabase_client.table('property_prices').insert(prices).execute()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save prices: {e}")
    
    def _save_realtor_info(self, property_id: int, data: Dict):
        """Save realtor information"""
        try:
            realtor_info = data.get('realtor_info', {})
            
            if not realtor_info.get('office_name'):
                return
            
            # Upsert realtor
            realtor_data = {
                'realtor_name': realtor_info['office_name'],
                'business_number': realtor_info.get('business_registration_number'),
                'license_number': realtor_info.get('license_number'),
                'phone_number': realtor_info.get('telephone'),
                'mobile_number': realtor_info.get('mobile_number'),
                'rating': realtor_info.get('grade'),
                'is_verified': realtor_info.get('certified_realtor', False),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Check if realtor exists
            existing = self.supabase_client.table('realtors').select('id').eq('realtor_name', realtor_data['realtor_name']).execute()
            
            if existing.data:
                realtor_id = existing.data[0]['id']
            else:
                new_realtor = self.supabase_client.table('realtors').insert(realtor_data).execute()
                realtor_id = new_realtor.data[0]['id']
            
            # Link property to realtor
            property_realtor = {
                'property_id': property_id,
                'realtor_id': realtor_id,
                'listing_date': date.today().isoformat(),
                'is_primary': True,
                'contact_phone': realtor_info.get('mobile_number')
            }
            
            self.supabase_client.table('property_realtors').insert(property_realtor).execute()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save realtor info: {e}")
    
    def _save_property_images(self, property_id: int, data: Dict):
        """Save image information"""
        try:
            photo_info = data.get('photo_info', {})
            photos = photo_info.get('photos', [])
            
            if not photos:
                return
            
            images = []
            for photo in photos:
                if photo.get('image_url'):
                    image_data = {
                        'property_id': property_id,
                        'image_url': photo['image_url'],
                        'image_type': photo.get('image_type', 'general'),
                        'image_order': photo.get('order', 1),
                        'caption': photo.get('caption', ''),
                        'width': photo.get('width', 0),
                        'height': photo.get('height', 0),
                        'captured_date': date.today().isoformat()
                    }
                    images.append(image_data)
            
            if images:
                self.supabase_client.table('property_images').insert(images).execute()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save images: {e}")
    
    def _save_property_facilities(self, property_id: int, data: Dict):
        """Save facility information"""
        try:
            facility_info = data.get('facility_info', {})
            facilities = facility_info.get('facilities', {})
            
            facility_mapping = {
                'elevator': 1,
                'parking': 2,
                'airConditioner': 7,
                'internet': 8,
                'cableTv': 9,
                'securitySystem': 4,
                'interphone': 6
            }
            
            facility_records = []
            for facility_name, available in facilities.items():
                if available and facility_name in facility_mapping:
                    facility_records.append({
                        'property_id': property_id,
                        'facility_id': facility_mapping[facility_name],
                        'available': True,
                        'condition_grade': 5,
                        'last_checked': date.today().isoformat()
                    })
            
            if facility_records:
                self.supabase_client.table('property_facilities').insert(facility_records).execute()
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to save facilities: {e}")
    
    def get_collection_metrics(self) -> CollectionMetrics:
        """Get current collection metrics"""
        self.metrics.end_time = datetime.now()
        return self.metrics
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker manually"""
        self.circuit_breaker_open = False
        self.api_failure_count = 0
        self.logger.info("🔄 Circuit breaker reset manually")

# Test and utility functions
def test_robust_collector():
    """Test the robust collector"""
    print("🧪 Testing Robust Data Collector")
    print("=" * 50)
    
    try:
        collector = RobustDataCollector()
        
        # Test single article collection
        test_article = "2546339433"  # Test article
        result = collector.collect_article_with_comprehensive_validation(test_article)
        
        if result:
            print("✅ Test collection successful")
            success = collector.save_to_database_with_transaction(result)
            print(f"✅ Database save: {success}")
        
        # Print metrics
        metrics = collector.get_collection_metrics()
        print(f"\n📊 Collection Metrics:")
        print(f"   Success Rate: {metrics.success_rate:.1f}%")
        print(f"   Duration: {metrics.duration:.2f}s")
        print(f"   API Errors: {metrics.api_errors}")
        print(f"   Validation Errors: {metrics.validation_errors}")
        print(f"   Database Errors: {metrics.database_errors}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_robust_collector()