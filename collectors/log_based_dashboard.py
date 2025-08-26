#!/usr/bin/env python3
"""
로그 기반 실시간 모니터링 대시보드
- 로그 파일을 실시간으로 읽어서 웹에 표시
- DB 부하 제로 (로그 파일만 읽음)
- 실시간 수집 데이터 현황 표시
"""

import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import time

app = FastAPI(title="네이버 수집 로그 기반 대시보드")

class LogReader:
    def __init__(self, log_dir: str = "/home/ubuntu/naver_land/logs"):
        self.log_dir = log_dir
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 로그 파일 경로들
        self.progress_log = os.path.join(log_dir, "live_progress.jsonl")
        self.collection_log = os.path.join(log_dir, "collection_data.jsonl")
        self.status_log = os.path.join(log_dir, "status.json")
    
    def get_kst_now(self):
        """KST 현재 시간 반환"""
        return datetime.now(self.kst)
    
    def read_json_lines(self, file_path: str, max_lines: int = 1000) -> List[Dict]:
        """JSONL 파일에서 최근 라인들 읽기"""
        if not os.path.exists(file_path):
            return []
        
        try:
            lines = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            # 최근 항목들만 반환
            return lines[-max_lines:] if len(lines) > max_lines else lines
        except Exception as e:
            print(f"로그 파일 읽기 오류 ({file_path}): {e}")
            return []
    
    def read_status_summary(self) -> Dict:
        """현재 상태 요약 읽기"""
        if not os.path.exists(self.status_log):
            return {}
        
        try:
            with open(self.status_log, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"상태 파일 읽기 오류: {e}")
            return {}
    
    def get_active_tasks(self) -> List[Dict]:
        """진행 중인 작업들 조회"""
        status_data = self.read_status_summary()
        active_tasks = []
        
        for task_id, task_info in status_data.items():
            if task_info.get('status') in ['started', 'in_progress']:
                active_tasks.append({
                    'task_id': task_id,
                    'dong_name': task_info.get('details', {}).get('dong_name', 'Unknown'),
                    'status': task_info.get('status'),
                    'started_at': task_info.get('details', {}).get('timestamp'),
                    'total_collected': task_info.get('details', {}).get('total_collected', 0),
                    'last_property': task_info.get('details', {}).get('last_property'),
                    'last_updated': task_info.get('last_updated')
                })
        
        return active_tasks
    
    def get_recent_completed(self) -> List[Dict]:
        """최근 완료된 작업들 조회"""
        progress_logs = self.read_json_lines(self.progress_log, 200)
        completed_tasks = []
        
        # 완료된 작업들 찾기
        for log in reversed(progress_logs):
            if log.get('type') == 'complete' and log.get('status') == 'completed':
                completed_tasks.append({
                    'task_id': log.get('task_id'),
                    'dong_name': log.get('dong_name', 'Unknown'),
                    'status': 'completed',
                    'completed_at': log.get('timestamp'),
                    'total_collected': log.get('total_collected', 0)
                })
                
                if len(completed_tasks) >= 10:
                    break
        
        return completed_tasks
    
    def get_recent_properties(self, limit: int = 20) -> List[Dict]:
        """최근 수집된 매물들 조회"""
        collection_logs = self.read_json_lines(self.collection_log, 500)
        recent_properties = []
        
        for log in reversed(collection_logs):
            if log.get('type') == 'property':
                property_data = log.get('data', {})
                # 매물 제목 우선순위: article_name > title > article_no
                title = property_data.get('article_name') or property_data.get('title') or property_data.get('article_no', 'Unknown')
                
                recent_properties.append({
                    'timestamp': log.get('timestamp'),
                    'task_id': log.get('task_id'),
                    'article_no': property_data.get('article_no'),
                    'title': title,
                    'price': property_data.get('price'),
                    'area': property_data.get('area', property_data.get('area1')),
                    'real_estate_type': property_data.get('real_estate_type'),
                    'address': property_data.get('address', property_data.get('kakao_address'))
                })
                
                if len(recent_properties) >= limit:
                    break
        
        return recent_properties
    
    def get_collection_stats(self) -> Dict:
        """전체 수집 통계"""
        collection_logs = self.read_json_lines(self.collection_log, 2000)
        
        # 오늘 수집된 매물 수
        today = self.get_kst_now().date()
        today_properties = 0
        type_counts = {}
        
        for log in collection_logs:
            if log.get('type') == 'property':
                log_date = datetime.fromisoformat(log.get('timestamp')).date()
                if log_date == today:
                    today_properties += 1
                    
                    # 타입별 집계
                    prop_type = log.get('data', {}).get('real_estate_type', 'Unknown')
                    type_counts[prop_type] = type_counts.get(prop_type, 0) + 1
        
        return {
            'today_total': today_properties,
            'type_breakdown': type_counts
        }

log_reader = LogReader()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:  # 복사본으로 순회
            try:
                await connection.send_json(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """로그 기반 대시보드 HTML 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>네이버 수집 로그 기반 모니터링</title>
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
                background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
                color: white; 
                padding: 20px; 
                text-align: center; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .log-badge {
                background: #00b894;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.8em;
                margin-left: 10px;
            }
            .live-indicator { 
                display: inline-block; 
                width: 12px; 
                height: 12px; 
                background: #00b894; 
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
            .stat-value { font-size: 2em; font-weight: bold; margin-bottom: 5px; color: #2d3436; }
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
                background: #2d3436; 
                color: white; 
                padding: 15px 20px; 
                font-weight: bold;
            }
            .section-content { padding: 20px; max-height: 400px; overflow-y: auto; }
            .task-item, .property-item { 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                padding: 12px 0; 
                border-bottom: 1px solid #eee;
            }
            .task-item:last-child, .property-item:last-child { border-bottom: none; }
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
            .log-info {
                background: #e8f4f8;
                border: 1px solid #00b894;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .log-info h3 {
                color: #2d3436;
                margin-bottom: 8px;
            }
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
            <h1>
                <span class="live-indicator"></span>
                네이버 부동산 수집 실시간 모니터링
                <span class="log-badge">LOG 기반</span>
            </h1>
            <p id="last-update">연결 중...</p>
        </div>
        
        <div class="container">
            <div class="log-info">
                <h3>📊 로그 기반 모니터링 시스템</h3>
                <p>• DB 부하 제로 (로그 파일만 읽음) | • 실시간 수집 데이터 표시 | • 10초마다 자동 업데이트</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="active-tasks">-</div>
                    <div class="stat-label">진행 중인 작업</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="today-properties">-</div>
                    <div class="stat-label">오늘 수집 매물</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="recent-properties">-</div>
                    <div class="stat-label">최근 매물</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="collection-rate">-</div>
                    <div class="stat-label">수집 속도 (/분)</div>
                </div>
            </div>
            
            <div class="sections">
                <div class="section">
                    <div class="section-header">🚀 진행 중인 수집 작업</div>
                    <div class="section-content">
                        <div id="active-tasks-list">로딩 중...</div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-header">✅ 최근 완료된 작업</div>
                    <div class="section-content">
                        <div id="completed-tasks">로딩 중...</div>
                    </div>
                </div>
            </div>
            
            <div class="section full-width">
                <div class="section-header">🏢 실시간 수집된 매물 데이터</div>
                <div class="section-content">
                    <div id="recent-properties-list">로딩 중...</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>로그 기반 실시간 모니터링 • 10초마다 자동 새로고침 • DB 부하 제로</p>
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
                document.getElementById('active-tasks').textContent = data.active_tasks?.length || 0;
                document.getElementById('today-properties').textContent = (data.stats?.today_total || 0).toLocaleString();
                document.getElementById('recent-properties').textContent = data.recent_properties?.length || 0;
                
                // 수집 속도 계산 (매물/분)
                const collectionRate = calculateCollectionRate(data.recent_properties || []);
                document.getElementById('collection-rate').textContent = collectionRate;
                
                // 진행 중인 작업들
                updateActiveTasks(data.active_tasks || []);
                
                // 완료된 작업들
                updateCompletedTasks(data.completed_tasks || []);
                
                // 최근 수집된 매물들
                updateRecentProperties(data.recent_properties || []);
            }
            
            function calculateCollectionRate(properties) {
                if (!properties || properties.length === 0) return 0;
                
                const now = new Date();
                const oneMinuteAgo = new Date(now.getTime() - 60000);
                
                const recentCount = properties.filter(prop => {
                    const propTime = new Date(prop.timestamp);
                    return propTime >= oneMinuteAgo;
                }).length;
                
                return recentCount;
            }
            
            function updateActiveTasks(tasks) {
                const container = document.getElementById('active-tasks-list');
                
                if (tasks.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666;">진행 중인 작업이 없습니다</p>';
                    return;
                }
                
                container.innerHTML = tasks.map(task => {
                    const duration = formatDuration(task.started_at);
                    const startTime = formatKSTTime(task.started_at);
                    const statusClass = `status-${task.status.replace('_', '-')}`;
                    
                    return `
                        <div class="task-item">
                            <div>
                                <strong>${task.dong_name}</strong>
                                <div style="font-size: 0.8em; color: #666;">
                                    ${startTime} 시작 • ${duration} 경과<br>
                                    수집: ${task.total_collected}개
                                    ${task.last_property ? ` • 최근: ${task.last_property}` : ''}
                                </div>
                            </div>
                            <span class="status-badge ${statusClass}">${task.status}</span>
                        </div>
                    `;
                }).join('');
            }
            
            function updateCompletedTasks(tasks) {
                const container = document.getElementById('completed-tasks');
                
                if (tasks.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666;">최근 완료된 작업이 없습니다</p>';
                    return;
                }
                
                container.innerHTML = tasks.map(task => {
                    const time = formatKSTTime(task.completed_at);
                    
                    return `
                        <div class="task-item">
                            <div>
                                <strong>${task.dong_name}</strong>
                                <div style="font-size: 0.8em; color: #666;">${time} 완료 • ${task.total_collected}개 매물</div>
                            </div>
                            <span class="status-badge status-completed">completed</span>
                        </div>
                    `;
                }).join('');
            }
            
            function updateRecentProperties(properties) {
                const container = document.getElementById('recent-properties-list');
                
                if (!properties || properties.length === 0) {
                    container.innerHTML = '<p style="text-align: center; color: #666;">수집된 매물이 없습니다</p>';
                    return;
                }
                
                container.innerHTML = properties.map(prop => {
                    const time = formatKSTTime(prop.timestamp);
                    
                    return `
                        <div class="property-item">
                            <div class="property-info">
                                <div class="property-title">${prop.title || prop.article_no || 'Unknown'}</div>
                                <div class="property-details">
                                    ${time} • ${prop.real_estate_type || 'Unknown'} • ${prop.area || 'N/A'}
                                    ${prop.address ? ` • ${prop.address}` : ''}
                                </div>
                            </div>
                            <div class="property-price">
                                ${prop.price || 'N/A'}
                            </div>
                        </div>
                    `;
                }).join('');
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
            # 10초마다 로그 데이터 읽어서 전송
            data = {
                'active_tasks': log_reader.get_active_tasks(),
                'completed_tasks': log_reader.get_recent_completed(),
                'recent_properties': log_reader.get_recent_properties(),
                'stats': log_reader.get_collection_stats(),
                'timestamp': log_reader.get_kst_now().isoformat()
            }
            await websocket.send_json(data)
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 로그 기반 대시보드 시작 중...")
    print("📱 브라우저에서 http://localhost:8000 으로 접속하세요")
    print("📊 로그 파일 기반 실시간 모니터링 (DB 부하 제로)")
    uvicorn.run(app, host="0.0.0.0", port=8000)