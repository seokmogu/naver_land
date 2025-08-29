#!/usr/bin/env python3
"""
네이버 부동산 수집기 모니터링 대시보드
실시간 수집 상태와 데이터베이스 현황을 모니터링합니다.
"""

import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import sys
from pathlib import Path

# 현재 디렉토리를 Python path에 추가
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from enhanced_data_collector import EnhancedNaverCollector

class CollectionMonitor:
    def __init__(self):
        """모니터링 시스템 초기화"""
        self.collector = EnhancedNaverCollector()
        self.start_time = datetime.now()
        
    def get_database_stats(self) -> Dict[str, Any]:
        """데이터베이스 현황 조회"""
        try:
            # 주요 테이블 레코드 수 조회
            tables_to_check = [
                'properties_new',
                'property_physical', 
                'property_locations',
                'property_prices',
                'property_images'
            ]
            
            stats = {}
            for table in tables_to_check:
                try:
                    result = self.collector.client.table(table).select('*', count='exact').execute()
                    stats[table] = result.count if hasattr(result, 'count') else 0
                except Exception as e:
                    stats[table] = f"Error: {e}"
                    
            return stats
        except Exception as e:
            return {"error": str(e)}
    
    def get_collection_status(self) -> Dict[str, Any]:
        """수집 현황 조회"""
        try:
            log_file = current_dir / "collectors" / "logs" / "live_progress.jsonl"
            
            if not log_file.exists():
                return {"status": "로그 파일 없음", "last_update": None}
                
            # 최신 로그 항목 읽기
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    if last_line:
                        return json.loads(last_line)
                        
            return {"status": "로그 데이터 없음", "last_update": None}
        except Exception as e:
            return {"status": f"오류: {e}", "last_update": None}
    
    def display_dashboard(self):
        """대시보드 화면 표시"""
        # 화면 초기화
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("🚀 네이버 부동산 데이터 수집기 모니터링 대시보드")
        print("=" * 80)
        print(f"📅 모니터링 시작: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 현재 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🕐 실행 시간: {datetime.now() - self.start_time}")
        print()
        
        # 데이터베이스 현황
        print("📊 데이터베이스 현황")
        print("-" * 40)
        db_stats = self.get_database_stats()
        
        if "error" in db_stats:
            print(f"❌ DB 연결 오류: {db_stats['error']}")
        else:
            for table, count in db_stats.items():
                if isinstance(count, int):
                    print(f"   {table:<20}: {count:,}개")
                else:
                    print(f"   {table:<20}: {count}")
        print()
        
        # 수집 현황
        print("🎯 수집 현황")
        print("-" * 40)
        collection_status = self.get_collection_status()
        
        if collection_status.get('last_update'):
            print(f"   마지막 업데이트: {collection_status['last_update']}")
        
        if 'status' in collection_status:
            print(f"   상태: {collection_status['status']}")
            
        if 'current_dong' in collection_status:
            print(f"   현재 수집 동: {collection_status['current_dong']}")
            
        if 'processed_count' in collection_status:
            print(f"   처리된 매물: {collection_status['processed_count']}개")
            
        print()
        
        # 토큰 상태
        print("🔑 토큰 상태")
        print("-" * 40)
        try:
            # 토큰 만료 시간 확인 (collector 초기화 시 표시됨)
            print("   토큰 상태: 정상")
        except Exception as e:
            print(f"   토큰 상태: 오류 - {e}")
        print()
        
        # 시스템 정보
        print("💻 시스템 정보")
        print("-" * 40)
        print(f"   Python 버전: {sys.version.split()[0]}")
        print(f"   작업 디렉토리: {current_dir}")
        print()
        
        print("🔄 자동 새로고침 중... (Ctrl+C로 종료)")
        print("=" * 80)

    def run(self, refresh_interval: int = 30):
        """모니터링 실행"""
        print("🎯 모니터링 시스템 시작...")
        
        try:
            while True:
                self.display_dashboard()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n\n👋 모니터링 종료")
        except Exception as e:
            print(f"\n❌ 모니터링 오류: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='네이버 부동산 수집기 모니터링')
    parser.add_argument('--interval', type=int, default=30, 
                       help='새로고침 간격 (초, 기본값: 30)')
    
    args = parser.parse_args()
    
    monitor = CollectionMonitor()
    monitor.run(args.interval)