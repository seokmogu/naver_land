#!/usr/bin/env python3
"""
웹 기반 실시간 모니터링 대시보드
FastAPI + WebSocket을 사용한 실시간 모니터링
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import pytz
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from supabase_client import SupabaseHelper


app = FastAPI(title="네이버 수집 모니터링 대시보드")

async def get_collection_results():
    """수집 작업별 결과 데이터 조회"""
    try:
        helper = SupabaseHelper()
        
        # 1. 진행 중인 수집 작업들의 실시간 수집 현황
        since_time = datetime.now() - timedelta(minutes=30)
        active_collections = helper.client.table('collection_logs')\
            .select('id, dong_name, cortar_no, started_at, status')\
            .in_('status', ['started', 'in_progress'])\
            .gte('created_at', since_time.isoformat())\
            .execute()
        
        # 2. 최근 완료된 수집 작업들의 수집 결과 요약
        completed_collections = helper.client.table('collection_logs')\
            .select('id, dong_name, cortar_no, started_at, completed_at, total_collected, status')\
            .in_('status', ['completed'])\
            .order('completed_at', desc=True)\
            .limit(5)\
            .execute()
        
        results = []
        
        # 진행 중인 수집의 실시간 현황
        for collection in active_collections.data:
            dong_name = collection['dong_name']
            cortar_no = collection['cortar_no']
            started_at = collection['started_at']
            
            # 해당 수집 작업으로 수집된 매물 집계
            stats = await get_collection_stats(helper, cortar_no, started_at)
            
            results.append({
                'type': 'active',
                'dong_name': dong_name,
                'status': collection['status'],
                'started_at': started_at,
                'total_count': stats['total_count'],
                'type_breakdown': stats['type_breakdown']
            })
        
        # 완료된 수집의 결과 요약
        for collection in completed_collections.data:
            dong_name = collection['dong_name']
            cortar_no = collection['cortar_no']
            started_at = collection['started_at']
            completed_at = collection['completed_at']
            total_collected = collection.get('total_collected', 0)
            
            # 해당 수집 작업으로 수집된 매물 집계
            stats = await get_collection_stats(helper, cortar_no, started_at, completed_at)
            
            results.append({
                'type': 'completed',
                'dong_name': dong_name,
                'status': collection['status'],
                'started_at': started_at,
                'completed_at': completed_at,
                'total_count': stats['total_count'],
                'type_breakdown': stats['type_breakdown']
            })
        
        return results
        
    except Exception as e:
        print(f"❌ 수집 결과 데이터 조회 실패: {e}")
        return []

async def get_collection_stats(helper, cortar_no: str, started_at: str, completed_at: str = None):
    """특정 수집 작업의 매물 통계 조회"""
    try:
        # 수집 시작 시간부터 완료 시간(또는 현재)까지 수집된 매물들
        start_date = datetime.fromisoformat(started_at.replace('Z', '+00:00')).date()
        
        query = helper.client.table('properties')\
            .select('real_estate_type')\
            .eq('cortar_no', cortar_no)\
            .gte('collected_date', start_date.isoformat())
        
        if completed_at:
            end_date = datetime.fromisoformat(completed_at.replace('Z', '+00:00')).date()
            query = query.lte('collected_date', end_date.isoformat())
        
        result = query.execute()
        
        # 매물 타입별 집계
        type_count = {}
        for property in result.data:
            real_estate_type = property['real_estate_type']
            type_count[real_estate_type] = type_count.get(real_estate_type, 0) + 1
        
        return {
            'total_count': len(result.data),
            'type_breakdown': type_count
        }
        
    except Exception as e:
        print(f"❌ 수집 통계 조회 실패: {e}")
        return {'total_count': 0, 'type_breakdown': {}}

# KST 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    """KST 현재 시간 반환"""
    return datetime.now(KST)

def format_kst_time(dt_str: str) -> str:
    """UTC 시간 문자열을 KST로 변환"""
    try:
        if dt_str:
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            kst_dt = dt.astimezone(KST)
            return kst_dt.strftime('%Y-%m-%d %H:%M:%S')
        return 'N/A'
    except:
        return 'N/A'

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # 연결이 끊어진 경우 제거
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """대시보드 HTML 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>네이버 수집 라이브 모니터링</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: #f5f7fa; 
                color: #333;
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 20px; 
                text-align: center; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .live-indicator { 
                display: inline-block; 
                width: 12px; 
                height: 12px; 
                background: #ff4757; 
                border-radius: 50%; 
                animation: pulse 2s infinite; 
                margin-right: 8px;
            }
            @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
            .container { padding: 20px; max-width: 1400px; margin: 0 auto; }
            .stats-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px;
            }
            .stat-card { 
                background: white; 
                padding: 20px; 
                border-radius: 12px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                text-align: center;
            }
            .stat-value { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
            .stat-label { color: #666; font-size: 0.9em; }
            .sections { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 30px; 
                margin-bottom: 30px;
            }
            .section { 
                background: white; 
                border-radius: 12px; 
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .section-header { 
                background: #667eea; 
                color: white; 
                padding: 15px 20px; 
                font-weight: bold;
            }
            .section-content { padding: 20px; }
            .collection-item, .recent-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                padding: 10px 0; 
                border-bottom: 1px solid #eee;
            }
            .collection-item:last-child, .recent-item:last-child { border-bottom: none; }
            .status-badge { 
                padding: 4px 8px; 
                border-radius: 16px; 
                font-size: 0.8em; 
                font-weight: bold;
            }
            .status-started { background: #ffeaa7; color: #d63031; }
            .status-in-progress { background: #a8e6cf; color: #00b894; }
            .status-completed { background: #dff0d8; color: #27ae60; }
            .status-failed { background: #f8d7da; color: #e74c3c; }
            .footer { 
                text-align: center; 
                padding: 20px; 
                color: #666; 
                font-size: 0.9em;
            }
            .full-width { grid-column: 1 / -1; }
            .system-info { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
                gap: 15px;
            }
            .system-metric { text-align: center; }
            .metric-value { font-size: 1.2em; font-weight: bold; color: #667eea; }
            .property-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                padding: 12px 0; 
                border-bottom: 1px solid #eee;
            }
            .property-item:last-child { border-bottom: none; }
            .property-info { flex: 1; }
            .property-title { font-weight: bold; margin-bottom: 4px; }
            .property-details { font-size: 0.8em; color: #666; }
            .property-price { 
                font-weight: bold; 
                color: #e74c3c; 
                margin-left: 15px; 
                text-align: right;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1><span class="live-indicator"></span>네이버 부동산 수집 라이브 모니터링</h1>
            <p id="last-update">연결 중...</p>
        </div>
        
        <div class="container">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="total-today">-</div>
                    <div class="stat-label">오늘 총 작업</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="completed-today">-</div>
                    <div class="stat-label">완료된 작업</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="active-count">-</div>
                    <div class="stat-label">진행 중</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="success-rate">-</div>
                    <div class="stat-label">성공률</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="total-items">-</div>
                    <div class="stat-label">수집된 매물</div>
                </div>
            </div>
            
            <div class="sections">
                <div class="section">
                    <div class="section-header">🔄 진행 중인 수집</div>
                    <div class="section-content">
                        <div id="active-collections">로딩 중...</div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">📋 최근 완료된 수집</div>
                    <div class="section-content">
                        <div id="recent-completed">로딩 중...</div>
                    </div>
                </div>
            </div>
            
            <div class="section full-width">
                <div class="section-header">📊 수집 작업별 결과</div>
                <div class="section-content">
                    <div id="collection-results">로딩 중...</div>
                </div>
            </div>
            
            <div class="section full-width">
                <div class="section-header">💻 시스템 상태</div>
                <div class="section-content">
                    <div class="system-info" id="system-info">로딩 중...</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>실시간 업데이트 • 3초마다 자동 새로고침</p>
        </div>

        <script>
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = function(event) {
                console.log('WebSocket 연결됨');
                document.getElementById('last-update').textContent = '연결됨';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function(event) {
                console.log('WebSocket 연결 끊어짐');
                document.getElementById('last-update').textContent = '연결 끊어짐 - 새로고침 해주세요';
            };
            
            function updateDashboard(data) {
                // 업데이트 시간 (KST)
                const now = new Date();
                document.getElementById('last-update').textContent = 
                    `마지막 업데이트: ${now.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}`;
                
                // 통계 업데이트
                const summary = data.today_summary || {};
                document.getElementById('total-today').textContent = summary.total || 0;
                document.getElementById('completed-today').textContent = summary.completed || 0;
                document.getElementById('active-count').textContent = data.active_collections?.length || 0;
                
                const successRate = summary.total > 0 ? 
                    ((summary.completed / summary.total) * 100).toFixed(1) : 0;
                document.getElementById('success-rate').textContent = successRate + '%';
                document.getElementById('total-items').textContent = 
                    (summary.total_items || 0).toLocaleString();
                
                // 진행 중인 수집
                updateActiveCollections(data.active_collections || []);
                
                // 최근 완료된 수집
                updateRecentCompleted(data.recent_completed || []);
                
                // 수집 작업별 결과
                updateCollectionResults(data.collection_results || []);
                
                // 시스템 정보
                updateSystemInfo(data.system_info || {});
            }
            
            function updateActiveCollections(collections) {
                const container = document.getElementById('active-collections');
                
                if (collections.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666;">진행 중인 수집이 없습니다</p>';
                    return;
                }
                
                container.innerHTML = collections.map(item => {
                    const duration = formatDuration(item.started_at);
                    const startTime = formatKSTStartTime(item.started_at);
                    const statusClass = `status-${item.status.replace('_', '-')}`;
                    
                    return `
                        <div class="collection-item">
                            <div>
                                <strong>${item.dong_name}</strong>
                                <div style="font-size: 0.8em; color: #666;">${startTime} 시작 • ${duration} 경과</div>
                            </div>
                            <span class="status-badge ${statusClass}">${item.status}</span>
                        </div>
                    `;
                }).join('');
            }
            
            function updateRecentCompleted(completed) {
                const container = document.getElementById('recent-completed');
                
                if (completed.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666;">최근 완료된 수집이 없습니다</p>';
                    return;
                }
                
                container.innerHTML = completed.map(item => {
                    const time = formatKSTStartTime(item.completed_at); // 간단한 형식 사용
                    const statusClass = `status-${item.status}`;
                    const items = item.total_collected || 0;
                    
                    return `
                        <div class="recent-item">
                            <div>
                                <strong>${item.dong_name}</strong>
                                <div style="font-size: 0.8em; color: #666;">${time} 완료 • ${items}개 매물</div>
                            </div>
                            <span class="status-badge ${statusClass}">${item.status}</span>
                        </div>
                    `;
                }).join('');
            }
            
            function updateCollectionResults(results) {
                const container = document.getElementById('collection-results');
                
                if (!results || results.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666;">수집 작업 결과가 없습니다</p>';
                    return;
                }
                
                container.innerHTML = results.map(result => {
                    const statusIcon = result.type === 'active' ? 
                        (result.status === 'started' ? '🟡' : '🔵') : '✅';
                    
                    const statusText = result.type === 'active' ? 
                        (result.status === 'started' ? '시작됨' : '진행 중') : '완료';
                    
                    // 매물 타입별 breakdown 텍스트 생성
                    const breakdownText = Object.entries(result.type_breakdown)
                        .map(([type, count]) => `${type} ${count}개`)
                        .join(', ');
                    
                    const timeText = result.type === 'active' ? 
                        `${formatKSTStartTime(result.started_at)} 시작` :
                        `${formatKSTStartTime(result.completed_at)} 완료`;
                    
                    return `
                        <div class="property-item">
                            <div class="property-info">
                                <div class="property-title">${statusIcon} ${result.dong_name} 수집 ${statusText}</div>
                                <div class="property-details">
                                    총 ${result.total_count}개 매물 • ${timeText}
                                    ${breakdownText ? ` • ${breakdownText}` : ''}
                                </div>
                            </div>
                            <div class="property-price" style="color: #2c3e50;">
                                ${result.total_count.toLocaleString()}개
                            </div>
                        </div>
                    `;
                }).join('');
            }
            
            function updateSystemInfo(info) {
                const container = document.getElementById('system-info');
                
                container.innerHTML = `
                    <div class="system-metric">
                        <div class="metric-value">${info.cpu_percent?.toFixed(1) || 0}%</div>
                        <div>CPU</div>
                    </div>
                    <div class="system-metric">
                        <div class="metric-value">${info.memory_percent?.toFixed(1) || 0}%</div>
                        <div>메모리</div>
                    </div>
                    <div class="system-metric">
                        <div class="metric-value">${info.memory_available || 'N/A'}</div>
                        <div>여유 메모리</div>
                    </div>
                    <div class="system-metric">
                        <div class="metric-value">${info.disk_percent?.toFixed(1) || 0}%</div>
                        <div>디스크</div>
                    </div>
                `;
            }
            
            function formatDuration(startTime) {
                if (!startTime) return 'N/A';
                
                const start = new Date(startTime);
                const now = new Date();
                const diff = Math.floor((now - start) / 1000);
                
                const hours = Math.floor(diff / 3600);
                const minutes = Math.floor((diff % 3600) / 60);
                const seconds = diff % 60;
                
                if (hours > 0) return `${hours}시간 ${minutes}분`;
                if (minutes > 0) return `${minutes}분 ${seconds}초`;
                return `${seconds}초`;
            }
            
            function formatKSTTime(timeString) {
                if (!timeString) return 'N/A';
                try {
                    const date = new Date(timeString);
                    return date.toLocaleString('ko-KR', { 
                        timeZone: 'Asia/Seoul',
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    });
                } catch {
                    return 'N/A';
                }
            }
            
            function formatKSTStartTime(timeString) {
                if (!timeString) return 'N/A';
                try {
                    const date = new Date(timeString);
                    return date.toLocaleString('ko-KR', { 
                        timeZone: 'Asia/Seoul',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                } catch {
                    return 'N/A';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    await manager.connect(websocket)
    try:
        while True:
            # 3초마다 데이터 수집 및 전송
            data = await get_monitoring_data()
            await websocket.send_json(data)
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def get_monitoring_data() -> Dict:
    """모니터링 데이터 수집"""
    try:
        helper = SupabaseHelper()
        
        # 진행 중인 수집
        since_time = datetime.now() - timedelta(minutes=30)
        active_result = helper.client.table('collection_logs')\
            .select('*')\
            .in_('status', ['started', 'in_progress'])\
            .gte('created_at', since_time.isoformat())\
            .order('created_at', desc=True)\
            .execute()
        
        # 최근 완료된 수집
        completed_result = helper.client.table('collection_logs')\
            .select('*')\
            .in_('status', ['completed', 'failed', 'timeout'])\
            .order('completed_at', desc=True)\
            .limit(10)\
            .execute()
        
        # 오늘의 요약 (KST 기준)
        kst_now = get_kst_now()
        today = kst_now.date().isoformat()
        # KST 자정을 UTC로 변환
        kst_midnight = KST.localize(datetime.combine(kst_now.date(), datetime.min.time()))
        utc_midnight = kst_midnight.astimezone(pytz.UTC)
        
        today_result = helper.client.table('collection_logs')\
            .select('status, total_collected')\
            .gte('created_at', utc_midnight.isoformat())\
            .execute()
        
        today_summary = {
            'total': len(today_result.data),
            'completed': 0,
            'failed': 0,
            'in_progress': 0,
            'total_items': 0
        }
        
        for log in today_result.data:
            status = log['status']
            if status == 'completed':
                today_summary['completed'] += 1
                if log.get('total_collected'):
                    today_summary['total_items'] += log['total_collected']
            elif status in ['failed', 'timeout']:
                today_summary['failed'] += 1
            elif status in ['started', 'in_progress']:
                today_summary['in_progress'] += 1
        
        # 시스템 정보
        try:
            import psutil
            system_info = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'memory_available': f"{psutil.virtual_memory().available / (1024**3):.1f}GB",
                'disk_percent': psutil.disk_usage('/').percent
            }
        except ImportError:
            system_info = {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_available': 'N/A',
                'disk_percent': 0
            }
        
        # 수집 작업별 결과 데이터 조회
        collection_results = await get_collection_results()
        
        return {
            'active_collections': active_result.data,
            'recent_completed': completed_result.data,
            'today_summary': today_summary,
            'system_info': system_info,
            'collection_results': collection_results,
            'timestamp': get_kst_now().isoformat()
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'active_collections': [],
            'recent_completed': [],
            'today_summary': {},
            'system_info': {},
            'collection_results': [],
            'timestamp': get_kst_now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    print("🌐 웹 대시보드 시작 중...")
    print("📱 브라우저에서 http://localhost:8000 으로 접속하세요")
    uvicorn.run(app, host="0.0.0.0", port=8000)