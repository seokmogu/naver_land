#!/usr/bin/env python3
"""
현대적 실시간 웹 모니터링 대시보드 서버
- WebSocket 기반 실시간 업데이트
- RESTful API 엔드포인트
- CORS 지원 및 보안 헤더
- 프로덕션 준비된 구조
"""

import json
import os
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import glob
import psutil
import websockets
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import gzip
import mimetypes

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ModernMonitorHandler(SimpleHTTPRequestHandler):
    """현대적 모니터링 핸들러 - REST API 및 정적 파일 서빙"""
    
    def __init__(self, *args, **kwargs):
        self.cache = {}
        self.cache_ttl = 5  # 5초 캐시
        super().__init__(*args, **kwargs)
    
    def end_headers(self):
        """보안 및 성능 헤더 추가"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Cache-Control', 'public, max-age=300')  # 5분 캐시
        super().end_headers()
    
    def do_GET(self):
        """GET 요청 처리 - 라우팅 개선"""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # 라우팅 테이블
        routes = {
            '/': self.serve_dashboard,
            '/dashboard': self.serve_dashboard,
            '/modern': self.serve_modern_dashboard,
            '/api/status': self.api_status,
            '/api/logs': self.api_logs,
            '/api/results': self.api_results,
            '/api/system': self.api_system,
            '/api/dong-detail': self.api_dong_detail,
            '/ws': self.handle_websocket_upgrade,
            '/health': self.health_check
        }
        
        handler = routes.get(path)
        if handler:
            try:
                handler(query_params)
            except Exception as e:
                logger.error(f"Handler error for {path}: {e}")
                self.send_error(500, f"Internal server error: {str(e)}")
        else:
            super().do_GET()
    
    def do_OPTIONS(self):
        """CORS preflight 처리"""
        self.send_response(200)
        self.end_headers()
    
    def serve_dashboard(self, params):
        """기본 대시보드 (레거시)"""
        self.serve_static_file('simple_monitor.py', 'text/html')
    
    def serve_modern_dashboard(self, params):
        """현대적 대시보드 서빙"""
        self.serve_static_file('modern_dashboard.html', 'text/html')
    
    def serve_static_file(self, filename, content_type):
        """정적 파일 서빙 - 압축 지원"""
        try:
            if filename == 'simple_monitor.py':
                # 기존 simple_monitor.py에서 HTML 추출
                with open('simple_monitor.py', 'r', encoding='utf-8') as f:
                    content = f.read()
                    # HTML 부분만 추출
                    start = content.find('html = """') + 10
                    end = content.find('"""', start)
                    html_content = content[start:end]
            else:
                with open(filename, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            
            # Gzip 압축 지원
            accept_encoding = self.headers.get('Accept-Encoding', '')
            if 'gzip' in accept_encoding and len(html_content) > 1000:
                content = gzip.compress(html_content.encode('utf-8'))
                self.send_response(200)
                self.send_header('Content-Type', f'{content_type}; charset=utf-8')
                self.send_header('Content-Encoding', 'gzip')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                content = html_content.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', f'{content_type}; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                
        except FileNotFoundError:
            self.send_error(404, f"File not found: {filename}")
        except Exception as e:
            logger.error(f"File serving error: {e}")
            self.send_error(500, f"File serving error: {str(e)}")
    
    def get_cached_data(self, key: str, generator_func):
        """캐시된 데이터 조회 또는 생성"""
        current_time = time.time()
        if key in self.cache:
            data, timestamp = self.cache[key]
            if current_time - timestamp < self.cache_ttl:
                return data
        
        # 캐시 미스 - 새 데이터 생성
        new_data = generator_func()
        self.cache[key] = (new_data, current_time)
        return new_data
    
    def api_status(self, params):
        """상태 API - 캐시 및 에러 처리 개선"""
        def generate_status():
            data = {
                'completed': 0,
                'in_progress': 0,
                'total_properties': 0,
                'active_tasks': [],
                'completed_tasks': [],
                'timestamp': datetime.now().isoformat(),
                'server_uptime': self.get_server_uptime()
            }
            
            try:
                if os.path.exists('logs/status.json'):
                    with open('logs/status.json', 'r', encoding='utf-8') as f:
                        status = json.load(f)
                    
                    for task_id, task_info in status.items():
                        task_status = task_info.get('status', 'unknown')
                        details = task_info.get('details', {})
                        
                        dong_name = details.get('dong_name', 'Unknown')
                        actual_count = self.get_actual_property_count(dong_name) if dong_name != 'Unknown' else 0
                        
                        task_data = {
                            'task_id': task_id,
                            'dong_name': dong_name,
                            'total_collected': actual_count,
                            'last_updated': task_info.get('last_updated', ''),
                            'status': task_status
                        }
                        
                        if task_status == 'completed':
                            data['completed'] += 1
                            data['total_properties'] += actual_count
                            data['completed_tasks'].append(task_data)
                        elif task_status in ['started', 'in_progress']:
                            data['in_progress'] += 1
                            data['active_tasks'].append(task_data)
            
            except Exception as e:
                logger.error(f"Status API error: {e}")
                data['error'] = str(e)
            
            return data
        
        status_data = self.get_cached_data('status', generate_status)
        self.send_json_response(status_data)
    
    def api_logs(self, params):
        """로그 API - 페이지네이션 및 필터링 지원"""
        def generate_logs():
            # 쿼리 파라미터
            limit = int(params.get('limit', [20])[0])  # 기본 20개
            offset = int(params.get('offset', [0])[0])
            log_type = params.get('type', [None])[0]  # 로그 타입 필터
            
            data = {
                'recent_logs': [],
                'total_count': 0,
                'has_more': False
            }
            
            try:
                if os.path.exists('logs/live_progress.jsonl'):
                    with open('logs/live_progress.jsonl', 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    logs = []
                    for line in lines:
                        try:
                            entry = json.loads(line.strip())
                            
                            # 타입 필터
                            if log_type and entry.get('type') != log_type:
                                continue
                            
                            timestamp = entry.get('timestamp', 'Unknown')
                            entry_type = entry.get('type', 'Unknown')
                            dong_name = entry.get('dong_name', '')
                            total = entry.get('total_collected', '')
                            
                            message = self.format_log_message(entry_type, dong_name, total, entry)
                            
                            logs.append({
                                'id': len(logs),
                                'timestamp': timestamp,
                                'type': entry_type,
                                'message': message,
                                'dong_name': dong_name,
                                'details': entry
                            })
                            
                        except json.JSONDecodeError:
                            continue
                    
                    # 최신순 정렬
                    logs.sort(key=lambda x: x['timestamp'], reverse=True)
                    
                    data['total_count'] = len(logs)
                    data['recent_logs'] = logs[offset:offset + limit]
                    data['has_more'] = offset + limit < len(logs)
            
            except Exception as e:
                logger.error(f"Logs API error: {e}")
                data['error'] = str(e)
            
            return data
        
        logs_data = self.get_cached_data(f"logs_{params}", generate_logs)
        self.send_json_response(logs_data)
    
    def api_results(self, params):
        """결과 파일 API - 상세 정보 및 통계"""
        def generate_results():
            data = {
                'total_files': 0,
                'total_properties': 0,
                'total_size_mb': 0,
                'recent_files': [],
                'statistics': {
                    'avg_properties_per_file': 0,
                    'largest_file': None,
                    'latest_file': None
                }
            }
            
            try:
                patterns = [
                    "results/naver_optimized_*.json",
                    "safe_results/safe_collect_*.json",
                    "results/*.json"
                ]
                
                all_files = []
                for pattern in patterns:
                    all_files.extend(glob.glob(pattern))
                
                all_files = list(set(all_files))  # 중복 제거
                all_files.sort(key=os.path.getmtime, reverse=True)
                
                data['total_files'] = len(all_files)
                
                file_details = []
                total_properties = 0
                total_size = 0
                
                for filepath in all_files[:20]:  # 최근 20개만 처리
                    try:
                        filename = os.path.basename(filepath)
                        file_size = os.path.getsize(filepath)
                        file_size_mb = file_size / 1024 / 1024
                        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        
                        # 매물 개수 계산
                        property_count = self.count_properties_in_file(filepath)
                        
                        file_info = {
                            'filename': filename,
                            'filepath': filepath,
                            'property_count': property_count,
                            'size_mb': round(file_size_mb, 2),
                            'size_bytes': file_size,
                            'modified': mod_time.isoformat(),
                            'modified_display': mod_time.strftime('%Y-%m-%d %H:%M'),
                            'dong_name': self.extract_dong_from_filename(filename)
                        }
                        
                        file_details.append(file_info)
                        total_properties += property_count
                        total_size += file_size_mb
                        
                    except Exception as e:
                        logger.warning(f"File processing error {filepath}: {e}")
                        continue
                
                data['recent_files'] = file_details[:10]  # 최근 10개만 반환
                data['total_properties'] = total_properties
                data['total_size_mb'] = round(total_size, 2)
                
                # 통계 계산
                if file_details:
                    data['statistics']['avg_properties_per_file'] = round(total_properties / len(file_details))
                    data['statistics']['largest_file'] = max(file_details, key=lambda x: x['size_bytes'])
                    data['statistics']['latest_file'] = file_details[0] if file_details else None
            
            except Exception as e:
                logger.error(f"Results API error: {e}")
                data['error'] = str(e)
            
            return data
        
        results_data = self.get_cached_data('results', generate_results)
        self.send_json_response(results_data)
    
    def api_system(self, params):
        """시스템 정보 API"""
        def generate_system_info():
            try:
                # CPU 및 메모리 정보
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('.')
                
                # 네트워크 정보
                net_io = psutil.net_io_counters()
                
                # 프로세스 정보
                process = psutil.Process()
                process_memory = process.memory_info()
                
                return {
                    'timestamp': datetime.now().isoformat(),
                    'cpu': {
                        'percent': round(cpu_percent, 1),
                        'count': psutil.cpu_count(),
                        'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
                    },
                    'memory': {
                        'total_gb': round(memory.total / 1024**3, 2),
                        'used_gb': round(memory.used / 1024**3, 2),
                        'available_gb': round(memory.available / 1024**3, 2),
                        'percent': memory.percent
                    },
                    'disk': {
                        'total_gb': round(disk.total / 1024**3, 2),
                        'used_gb': round(disk.used / 1024**3, 2),
                        'free_gb': round(disk.free / 1024**3, 2),
                        'percent': round((disk.used / disk.total) * 100, 1)
                    },
                    'network': {
                        'bytes_sent': net_io.bytes_sent,
                        'bytes_recv': net_io.bytes_recv,
                        'packets_sent': net_io.packets_sent,
                        'packets_recv': net_io.packets_recv
                    },
                    'process': {
                        'memory_mb': round(process_memory.rss / 1024**2, 2),
                        'cpu_percent': process.cpu_percent(),
                        'threads': process.num_threads()
                    },
                    'uptime': self.get_server_uptime()
                }
            except Exception as e:
                logger.error(f"System info error: {e}")
                return {'error': str(e)}
        
        system_data = self.get_cached_data('system', generate_system_info)
        self.send_json_response(system_data)
    
    def api_dong_detail(self, params):
        """특정 동의 상세 정보 API"""
        dong_name = params.get('dong', [None])[0]
        if not dong_name:
            self.send_error(400, "동 이름이 필요합니다")
            return
        
        def generate_dong_detail():
            try:
                # 해당 동의 모든 파일 찾기
                patterns = [
                    f'results/naver_optimized_{dong_name}_*.json',
                    f'safe_results/safe_collect_{dong_name}_*.json'
                ]
                
                files = []
                for pattern in patterns:
                    files.extend(glob.glob(pattern))
                
                if not files:
                    return {'error': f'{dong_name}의 데이터를 찾을 수 없습니다'}
                
                # 가장 최신 파일 선택
                latest_file = max(files, key=os.path.getmtime)
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                properties = data.get('매물목록', data.get('properties', []))
                
                # 상세 통계 계산
                stats = {
                    'total_properties': len(properties),
                    'avg_price': 0,
                    'price_range': {'min': 0, 'max': 0},
                    'property_types': {},
                    'area_distribution': {},
                    'floor_distribution': {}
                }
                
                if properties:
                    prices = []
                    for prop in properties:
                        # 가격 정보 추출
                        price_str = prop.get('매매가', prop.get('price', ''))
                        if price_str and price_str != '-':
                            try:
                                # 억, 천만원 단위 처리
                                price = self.parse_price_string(price_str)
                                if price > 0:
                                    prices.append(price)
                            except:
                                pass
                        
                        # 매물 유형
                        prop_type = prop.get('매물종류', prop.get('type', '기타'))
                        stats['property_types'][prop_type] = stats['property_types'].get(prop_type, 0) + 1
                    
                    if prices:
                        stats['avg_price'] = round(sum(prices) / len(prices))
                        stats['price_range'] = {'min': min(prices), 'max': max(prices)}
                
                return {
                    'dong_name': dong_name,
                    'file_info': {
                        'filename': os.path.basename(latest_file),
                        'modified': datetime.fromtimestamp(os.path.getmtime(latest_file)).isoformat(),
                        'size_mb': round(os.path.getsize(latest_file) / 1024**2, 2)
                    },
                    'statistics': stats,
                    'sample_properties': properties[:5] if properties else []  # 샘플 5개
                }
            
            except Exception as e:
                logger.error(f"Dong detail error for {dong_name}: {e}")
                return {'error': str(e)}
        
        dong_data = self.get_cached_data(f'dong_{dong_name}', generate_dong_detail)
        self.send_json_response(dong_data)
    
    def health_check(self, params):
        """헬스체크 엔드포인트"""
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime': self.get_server_uptime(),
            'version': '2.0.0'
        }
        self.send_json_response(health_data)
    
    def handle_websocket_upgrade(self, params):
        """WebSocket 업그레이드 처리 (향후 구현)"""
        self.send_error(501, "WebSocket not implemented yet")
    
    # 유틸리티 메서드들
    def get_server_uptime(self):
        """서버 업타임 계산"""
        if not hasattr(self.server, 'start_time'):
            self.server.start_time = time.time()
        
        uptime_seconds = time.time() - self.server.start_time
        uptime_td = timedelta(seconds=int(uptime_seconds))
        return str(uptime_td)
    
    def get_actual_property_count(self, dong_name: str) -> int:
        """실제 결과 파일에서 매물 개수 조회 - 개선된 버전"""
        try:
            patterns = [
                f'results/naver_optimized_{dong_name}_*.json',
                f'naver_optimized_{dong_name}_*.json',
                f'safe_results/safe_collect_{dong_name}_*.json',
                f'results/*{dong_name}*.json',
                f'*{dong_name}*.json'
            ]
            
            files = []
            for pattern in patterns:
                files.extend(glob.glob(pattern))
            
            if not files:
                return 0
            
            latest_file = max(files, key=os.path.getmtime)
            return self.count_properties_in_file(latest_file)
            
        except Exception as e:
            logger.warning(f"매물 개수 계산 오류 ({dong_name}): {e}")
            return 0
    
    def count_properties_in_file(self, filepath: str) -> int:
        """파일에서 매물 개수 계산"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                properties = data.get('매물목록', 
                                   data.get('properties', 
                                   data.get('data', 
                                   data.get('results', []))))
                return len(properties) if isinstance(properties, list) else 0
        except:
            # JSON 파싱 실패시 간단한 문자열 카운트
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    return content.count('"매물번호"')
            except:
                return 0
    
    def extract_dong_from_filename(self, filename: str) -> str:
        """파일명에서 동 이름 추출"""
        for dong in ['개포동', '논현동', '대치동', '도곡동', '삼성동', '세곡동', '수서동', 
                    '신사동', '압구정동', '역삼동', '일원동', '자곡동', '청담동', '행정동']:
            if dong in filename:
                return dong
        return '알 수 없음'
    
    def parse_price_string(self, price_str: str) -> int:
        """가격 문자열을 숫자로 변환 (만원 단위)"""
        if not price_str or price_str == '-':
            return 0
        
        # 억, 천, 만 단위 처리
        price = 0
        if '억' in price_str:
            parts = price_str.split('억')
            price += int(float(parts[0]) * 10000)  # 억 -> 만원
            if len(parts) > 1 and parts[1].strip():
                remain = parts[1].replace('만', '').replace(',', '').strip()
                if remain:
                    price += int(remain)
        elif '만' in price_str:
            price = int(price_str.replace('만', '').replace(',', ''))
        else:
            price = int(price_str.replace(',', ''))
        
        return price
    
    def format_log_message(self, entry_type: str, dong_name: str, total: Any, entry: Dict) -> str:
        """로그 메시지 포매팅"""
        if entry_type == 'start':
            return f"{dong_name} 수집 시작"
        elif entry_type == 'complete':
            return f"{dong_name} 완료 ({total}개 매물)"
        elif entry_type == 'heartbeat' and total:
            return f"{dong_name} 진행 중 ({total}개 수집됨)"
        elif entry_type == 'error':
            error_msg = entry.get('error', '알 수 없는 오류')
            return f"{dong_name} 오류: {error_msg}"
        else:
            return f"{entry_type} 이벤트"
    
    def send_json_response(self, data: Dict[str, Any]):
        """JSON 응답 전송 - 압축 및 헤더 최적화"""
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        
        # Gzip 압축 지원
        accept_encoding = self.headers.get('Accept-Encoding', '')
        if 'gzip' in accept_encoding and len(json_str) > 500:
            content = gzip.compress(json_str.encode('utf-8'))
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            content = json_str.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)

class WebSocketManager:
    """WebSocket 연결 관리자 (향후 구현)"""
    
    def __init__(self):
        self.connections = set()
        self.running = False
    
    async def register(self, websocket):
        """새로운 WebSocket 연결 등록"""
        self.connections.add(websocket)
        logger.info(f"WebSocket 연결됨: {websocket.remote_address}")
    
    async def unregister(self, websocket):
        """WebSocket 연결 해제"""
        self.connections.discard(websocket)
        logger.info(f"WebSocket 연결 해제: {websocket.remote_address}")
    
    async def broadcast(self, message):
        """모든 연결된 클라이언트에게 메시지 브로드캐스트"""
        if self.connections:
            await asyncio.gather(
                *[conn.send(message) for conn in self.connections],
                return_exceptions=True
            )

def create_logs_directory():
    """로그 디렉토리 생성"""
    os.makedirs('logs', exist_ok=True)

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="현대적 실시간 모니터링 대시보드")
    parser.add_argument("--port", type=int, default=8888, help="웹서버 포트 (기본값: 8888)")
    parser.add_argument("--host", default="0.0.0.0", help="웹서버 호스트 (기본값: 0.0.0.0)")
    parser.add_argument("--cache-ttl", type=int, default=5, help="캐시 TTL 초 (기본값: 5)")
    parser.add_argument("--debug", action="store_true", help="디버그 모드")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 로그 디렉토리 생성
    create_logs_directory()
    
    # 현재 디렉토리 확인
    if not os.path.exists('logs') and not os.path.exists('results'):
        logger.error("❌ logs/ 또는 results/ 디렉토리를 찾을 수 없습니다.")
        logger.info("💡 collectors/ 디렉토리에서 실행해주세요.")
        return
    
    try:
        # HTTP 서버 시작
        server = HTTPServer((args.host, args.port), ModernMonitorHandler)
        server.start_time = time.time()  # 서버 시작 시간 기록
        
        logger.info("🚀 현대적 모니터링 대시보드 서버 시작")
        logger.info(f"🌐 접속 URL: http://localhost:{args.port}/modern")
        if args.host != "127.0.0.1" and args.host != "localhost":
            logger.info(f"🌍 외부 접속: http://<EC2-IP>:{args.port}/modern")
        logger.info(f"📊 API 엔드포인트: http://localhost:{args.port}/api/")
        logger.info(f"🔧 헬스체크: http://localhost:{args.port}/health")
        logger.info(f"⚡ 실시간 업데이트: 5초마다 자동")
        logger.info(f"💾 캐시 TTL: {args.cache_ttl}초")
        logger.info("=" * 50)
        logger.info("🛑 종료하려면 Ctrl+C를 눌러주세요")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 모니터링 서버를 종료합니다.")
    except Exception as e:
        logger.error(f"❌ 서버 오류: {e}")

if __name__ == "__main__":
    main()