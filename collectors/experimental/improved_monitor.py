#!/usr/bin/env python3
"""
개선된 네이버 부동산 수집기 모니터링 대시보드
사용자 중심의 직관적인 인터페이스 제공
"""

import json
import os
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import glob

class ImprovedMonitorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_dashboard()
        elif self.path == '/api/status':
            self.send_status_api()
        else:
            super().do_GET()
    
    def send_dashboard(self):
        """개선된 메인 대시보드 HTML 전송"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>네이버 부동산 수집기 모니터</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* 헤더 섹션 */
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
            margin-bottom: 20px;
        }
        
        .refresh-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 12px 24px;
            border-radius: 50px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }
        
        .refresh-btn:hover {
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-2px);
        }
        
        /* 전체 진행 상태 카드 */
        .progress-overview {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }
        
        .progress-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: #2d3748;
        }
        
        .progress-stats {
            text-align: right;
        }
        
        .progress-number {
            font-size: 2.5rem;
            font-weight: 800;
            color: #4299e1;
            line-height: 1;
        }
        
        .progress-label {
            color: #718096;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        
        .progress-bar-container {
            background: #e2e8f0;
            height: 12px;
            border-radius: 6px;
            overflow: hidden;
            position: relative;
            margin-bottom: 20px;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #4299e1 0%, #3182ce 100%);
            border-radius: 6px;
            transition: width 1s ease;
            position: relative;
        }
        
        .quick-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-item {
            text-align: center;
            padding: 15px;
            background: #f7fafc;
            border-radius: 12px;
        }
        
        .stat-number {
            font-size: 1.8rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 5px;
        }
        
        .stat-label {
            color: #718096;
            font-size: 0.85rem;
        }
        
        /* 동별 상태 그리드 */
        .dong-section {
            background: white;
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 25px;
            display: flex;
            align-items: center;
        }
        
        .section-title::before {
            content: "🏘️";
            margin-right: 10px;
            font-size: 1.8rem;
        }
        
        .dong-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 15px;
        }
        
        .dong-card {
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        
        .dong-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.15);
        }
        
        .dong-completed {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
        }
        
        .dong-progress {
            background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);
            color: white;
            animation: pulse 2s infinite;
        }
        
        .dong-pending {
            background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e0 100%);
            color: #4a5568;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.8; }
        }
        
        .dong-name {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .dong-status {
            font-size: 0.9rem;
            opacity: 0.9;
            margin-bottom: 5px;
        }
        
        .dong-count {
            font-size: 1.2rem;
            font-weight: 700;
        }
        
        .dong-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: rgba(255, 255, 255, 0.3);
        }
        
        /* 최근 활동 섹션 */
        .activity-section {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        .activity-title::before {
            content: "📋";
            margin-right: 10px;
            font-size: 1.8rem;
        }
        
        .activity-item {
            display: flex;
            align-items: center;
            padding: 15px;
            margin: 10px 0;
            background: #f7fafc;
            border-radius: 12px;
            border-left: 4px solid #4299e1;
        }
        
        .activity-icon {
            font-size: 1.5rem;
            margin-right: 15px;
        }
        
        .activity-content {
            flex: 1;
        }
        
        .activity-message {
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 3px;
        }
        
        .activity-time {
            font-size: 0.85rem;
            color: #718096;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #718096;
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 15px;
            opacity: 0.5;
        }
        
        /* 반응형 디자인 */
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .progress-overview,
            .dong-section,
            .activity-section {
                padding: 20px;
            }
            
            .dong-grid {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
            }
            
            .progress-header {
                flex-direction: column;
                text-align: center;
            }
            
            .progress-stats {
                text-align: center;
                margin-top: 15px;
            }
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
            font-size: 1.2rem;
            color: #718096;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 헤더 -->
        <div class="header">
            <h1>🚀 네이버 부동산 수집기</h1>
            <p>강남구 14개 동 매물 수집 현황</p>
            <button class="refresh-btn" onclick="location.reload()">
                🔄 새로고침
            </button>
        </div>
        
        <!-- 전체 진행 현황 -->
        <div class="progress-overview">
            <div class="progress-header">
                <div class="progress-title">전체 진행 현황</div>
                <div class="progress-stats">
                    <div class="progress-number" id="overall-percentage">0%</div>
                    <div class="progress-label">완료됨</div>
                </div>
            </div>
            
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-bar" style="width: 0%"></div>
            </div>
            
            <div class="quick-stats">
                <div class="stat-item">
                    <div class="stat-number" id="completed-count">0</div>
                    <div class="stat-label">완료</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="progress-count">0</div>
                    <div class="stat-label">진행중</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="pending-count">14</div>
                    <div class="stat-label">대기</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="total-properties">0</div>
                    <div class="stat-label">총 매물</div>
                </div>
            </div>
        </div>
        
        <!-- 동별 상태 -->
        <div class="dong-section">
            <h2 class="section-title">동별 수집 현황</h2>
            <div class="dong-grid" id="dong-grid">
                <div class="loading">데이터를 불러오는 중...</div>
            </div>
        </div>
        
        <!-- 최근 활동 -->
        <div class="activity-section">
            <h2 class="section-title activity-title">최근 활동</h2>
            <div id="recent-activity">
                <div class="loading">활동 로그를 불러오는 중...</div>
            </div>
        </div>
    </div>
    
    <script>
        const GANGNAM_DONGS = [
            "개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", 
            "신사동", "압구정동", "역삼동", "일원동", "자곡동", "청담동", "행정동"
        ];
        
        // 전역 상태
        let currentData = {
            completed: 0,
            inProgress: 0,
            totalProperties: 0,
            dongStatus: {}
        };
        
        function updateProgressOverview(data) {
            const totalDongs = GANGNAM_DONGS.length;
            const completedCount = data.completed || 0;
            const inProgressCount = data.in_progress || 0;
            const pendingCount = totalDongs - completedCount - inProgressCount;
            const percentage = Math.round((completedCount / totalDongs) * 100);
            
            // 전체 진행률 업데이트
            document.getElementById('overall-percentage').textContent = percentage + '%';
            document.getElementById('progress-bar').style.width = percentage + '%';
            
            // 통계 업데이트
            document.getElementById('completed-count').textContent = completedCount;
            document.getElementById('progress-count').textContent = inProgressCount;
            document.getElementById('pending-count').textContent = pendingCount;
            document.getElementById('total-properties').textContent = (data.total_properties || 0).toLocaleString();
        }
        
        function updateDongGrid(data) {
            const dongGrid = document.getElementById('dong-grid');
            const completedTasks = data.completed_tasks || [];
            const activeTasks = data.active_tasks || [];
            
            // 동별 상태 맵 생성
            const dongStatusMap = {};
            
            completedTasks.forEach(task => {
                dongStatusMap[task.dong_name] = {
                    status: 'completed',
                    count: task.total_collected || 0
                };
            });
            
            activeTasks.forEach(task => {
                dongStatusMap[task.dong_name] = {
                    status: 'progress',
                    count: task.total_collected || 0
                };
            });
            
            // 동 카드 생성
            let dongHtml = '';
            GANGNAM_DONGS.forEach(dong => {
                const status = dongStatusMap[dong];
                let className = 'dong-pending';
                let statusText = '대기중';
                let countText = '-';
                let statusIcon = '⏳';
                
                if (status) {
                    if (status.status === 'completed') {
                        className = 'dong-completed';
                        statusText = '완료';
                        countText = status.count.toLocaleString() + '개';
                        statusIcon = '✅';
                    } else if (status.status === 'progress') {
                        className = 'dong-progress';
                        statusText = '진행중';
                        countText = status.count.toLocaleString() + '개';
                        statusIcon = '🔄';
                    }
                }
                
                dongHtml += `
                    <div class="dong-card ${className}">
                        <div class="dong-name">${dong}</div>
                        <div class="dong-status">${statusIcon} ${statusText}</div>
                        <div class="dong-count">${countText}</div>
                    </div>
                `;
            });
            
            dongGrid.innerHTML = dongHtml;
        }
        
        function updateRecentActivity(recentLogs) {
            const activityDiv = document.getElementById('recent-activity');
            
            if (!recentLogs || recentLogs.length === 0) {
                activityDiv.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📋</div>
                        <div>최근 활동이 없습니다</div>
                    </div>
                `;
                return;
            }
            
            // 최근 3개 활동만 표시
            const recentActivities = recentLogs.slice(-3).reverse();
            let activityHtml = '';
            
            recentActivities.forEach(log => {
                let icon = '📋';
                if (log.type === 'start') icon = '🚀';
                else if (log.type === 'complete') icon = '✅';
                else if (log.type === 'heartbeat') icon = '💓';
                
                const timeFormat = new Date(log.timestamp).toLocaleString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                activityHtml += `
                    <div class="activity-item">
                        <div class="activity-icon">${icon}</div>
                        <div class="activity-content">
                            <div class="activity-message">${log.message}</div>
                            <div class="activity-time">${timeFormat}</div>
                        </div>
                    </div>
                `;
            });
            
            activityDiv.innerHTML = activityHtml;
        }
        
        function updateDashboard() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    currentData = data;
                    updateProgressOverview(data);
                    updateDongGrid(data);
                })
                .catch(error => {
                    console.error('Status update failed:', error);
                });
            
            // 로그 데이터는 별도로 가져올 수 있지만, 현재는 단순화
            // 실제 로그 API가 있다면 여기에 추가
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    updateRecentActivity(data.recent_logs);
                })
                .catch(error => {
                    console.error('Logs update failed:', error);
                });
        }
        
        // 초기 로드 및 자동 새로고침
        updateDashboard();
        setInterval(updateDashboard, 30000); // 30초마다 업데이트
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def get_actual_property_count(self, dong_name):
        """실제 결과 파일에서 매물 개수 조회"""
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
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                properties = data.get('매물목록', 
                                    data.get('properties', 
                                    data.get('data', 
                                    data.get('results', []))))
                return len(properties) if isinstance(properties, list) else 0
        except Exception as e:
            print(f"매물 개수 계산 오류 ({dong_name}): {e}")
            return 0

    def send_status_api(self):
        """상태 API 응답"""
        try:
            data = {
                'completed': 0,
                'in_progress': 0,
                'total_properties': 0,
                'active_tasks': [],
                'completed_tasks': []
            }
            
            # status.json 읽기
            if os.path.exists('logs/status.json'):
                with open('logs/status.json', 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                for task_id, task_info in status.items():
                    task_status = task_info.get('status', 'unknown')
                    details = task_info.get('details', {})
                    
                    dong_name = details.get('dong_name', 'Unknown')
                    
                    # 실제 파일에서 매물 개수 조회
                    actual_count = self.get_actual_property_count(dong_name) if dong_name != 'Unknown' else 0
                    
                    if task_status == 'completed':
                        data['completed'] += 1
                        data['total_properties'] += actual_count
                        data['completed_tasks'].append({
                            'dong_name': dong_name,
                            'total_collected': actual_count
                        })
                    elif task_status == 'started':
                        data['in_progress'] += 1
                        data['active_tasks'].append({
                            'dong_name': dong_name,
                            'total_collected': actual_count
                        })
            
            self.send_json_response(data)
            
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
    def send_json_response(self, data):
        """JSON 응답 전송"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="개선된 네이버 부동산 수집기 모니터링 대시보드")
    parser.add_argument("--port", type=int, default=8889, help="웹서버 포트 (기본값: 8889)")
    parser.add_argument("--host", default="0.0.0.0", help="웹서버 호스트 (기본값: 0.0.0.0)")
    args = parser.parse_args()
    
    port = args.port
    host = args.host
    
    if not os.path.exists('logs') and not os.path.exists('results'):
        print("❌ logs/ 또는 results/ 디렉토리를 찾을 수 없습니다.")
        print("💡 collectors/ 디렉토리에서 실행해주세요.")
        return
    
    try:
        server = HTTPServer((host, port), ImprovedMonitorHandler)
        print(f"🌐 개선된 모니터링 대시보드 시작: http://localhost:{port}")
        if host != "127.0.0.1" and host != "localhost":
            print(f"🌍 외부 접속 가능: http://<EC2-IP>:{port}")
        print(f"📊 실시간 업데이트: 30초마다 자동 새로고침")
        print("=" * 50)
        print("🛑 종료하려면 Ctrl+C를 눌러주세요")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 모니터링 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 서버 오류: {e}")

if __name__ == "__main__":
    main()