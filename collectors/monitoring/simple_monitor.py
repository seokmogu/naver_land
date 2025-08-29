#!/usr/bin/env python3
"""
간단한 웹 모니터링 대시보드
로그 기반 수집기의 진행 상황을 웹에서 실시간 확인
"""

import json
import os
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import glob

class CollectorMonitorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_dashboard()
        elif self.path == '/api/status':
            self.send_status_api()
        elif self.path == '/api/logs':
            self.send_logs_api()
        elif self.path == '/api/results':
            self.send_results_api()
        else:
            super().do_GET()
    
    def send_dashboard(self):
        """메인 대시보드 HTML 전송"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>네이버 부동산 수집기 모니터링</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; }
        .header { background: #007bff; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; }
        .success { border-left: 4px solid #28a745; }
        .warning { border-left: 4px solid #ffc107; }
        .info { border-left: 4px solid #17a2b8; }
        .error { border-left: 4px solid #dc3545; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .progress-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; margin: 20px 0; }
        .progress-bar { background: rgba(255,255,255,0.2); height: 30px; border-radius: 15px; overflow: hidden; margin: 15px 0; }
        .progress-fill { background: linear-gradient(90deg, #00d2ff 0%, #3a7bd5 100%); height: 100%; transition: width 0.5s ease; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .eta-info { display: flex; justify-content: space-between; margin-top: 10px; font-size: 0.9em; }
        .dong-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 15px 0; }
        .dong-item { padding: 10px; border-radius: 8px; text-align: center; font-size: 0.9em; }
        .dong-completed { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .dong-progress { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .dong-pending { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .log-entry { margin: 5px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; font-size: 0.9em; }
        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #0056b3; }
        pre { background: #f8f9fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 네이버 부동산 수집기 모니터링</h1>
        <p>실시간 수집 진행 상황 대시보드</p>
        <button class="refresh-btn" onclick="location.reload()">🔄 새로고침</button>
    </div>
    
    <div class="progress-card">
        <h2>🚀 전체 진행률</h2>
        <div class="progress-bar">
            <div class="progress-fill" id="overall-progress" style="width: 0%;">
                0%
            </div>
        </div>
        <div class="eta-info">
            <div>⏱️ 예상 완료: <span id="eta">계산 중...</span></div>
            <div>⚡ 속도: <span id="speed">-</span> 매물/분</div>
        </div>
    </div>
    
    <div class="stats" id="stats">
        <div class="stat-card">
            <div class="stat-number" id="completed">-</div>
            <div>완료된 동</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="in-progress">-</div>
            <div>진행 중</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="total-properties">-</div>
            <div>총 수집 매물</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="result-files">-</div>
            <div>결과 파일</div>
        </div>
    </div>
    
    <div class="card info">
        <h3>🏘️ 동별 상태 (강남구 14개 동)</h3>
        <div class="dong-grid" id="dong-status">
            로딩 중...
        </div>
    </div>
    
    <div class="card info">
        <h3>📊 현재 상태</h3>
        <div id="current-status">로딩 중...</div>
    </div>
    
    <div class="card info">
        <h3>📋 최근 활동 (최근 10개)</h3>
        <div id="recent-logs">로딩 중...</div>
    </div>
    
    <div class="card info">
        <h3>📁 수집 결과 파일</h3>
        <div id="result-files-list">로딩 중...</div>
    </div>
    
    <script>
        const GANGNAM_DONGS = [
            "개포동", "논현동", "대치동", "도곡동", "삼성동", "세곡동", "수서동", 
            "신사동", "압구정동", "역삼동", "일원동", "자곡동", "청담동", "행정동"
        ];
        
        function calculateProgress(completed, total) {
            return Math.round((completed / total) * 100);
        }
        
        function calculateETA(completed, total, startTime, speed) {
            if (speed <= 0 || completed >= total) return "완료됨";
            
            const remaining = total - completed;
            const minutesLeft = Math.round(remaining / speed);
            
            if (minutesLeft < 60) {
                return `${minutesLeft}분 후`;
            } else {
                const hours = Math.floor(minutesLeft / 60);
                const mins = minutesLeft % 60;
                return `${hours}시간 ${mins}분 후`;
            }
        }
        
        function updateProgressBar(percentage) {
            const progressBar = document.getElementById('overall-progress');
            progressBar.style.width = percentage + '%';
            progressBar.textContent = percentage + '%';
        }
        
        function updateDongStatus(completedTasks, activeTasks) {
            const dongGrid = document.getElementById('dong-status');
            let dongHtml = '';
            
            // 완료/진행 중인 동 목록 생성
            const completedDongs = completedTasks.map(t => t.dong_name);
            const activeDongs = activeTasks.map(t => t.dong_name);
            
            GANGNAM_DONGS.forEach(dong => {
                let className = 'dong-pending';
                let status = '대기 중';
                let count = '';
                
                if (completedDongs.includes(dong)) {
                    className = 'dong-completed';
                    const task = completedTasks.find(t => t.dong_name === dong);
                    status = '완료';
                    count = `${task.total_collected}개`;
                } else if (activeDongs.includes(dong)) {
                    className = 'dong-progress';
                    const task = activeTasks.find(t => t.dong_name === dong);
                    status = '진행 중';
                    count = `${task.total_collected}개`;
                }
                
                dongHtml += `
                    <div class="dong-item ${className}">
                        <strong>${dong}</strong><br>
                        <span>${status}</span><br>
                        <small>${count}</small>
                    </div>
                `;
            });
            
            dongGrid.innerHTML = dongHtml;
        }
        
        function updateDashboard() {
            // 상태 API 호출
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const totalDongs = GANGNAM_DONGS.length;
                    const completedCount = data.completed || 0;
                    const inProgressCount = data.in_progress || 0;
                    const totalProperties = data.total_properties || 0;
                    
                    // 기본 통계 업데이트
                    document.getElementById('completed').textContent = completedCount;
                    document.getElementById('in-progress').textContent = inProgressCount;
                    document.getElementById('total-properties').textContent = totalProperties;
                    
                    // 진행률 계산 및 업데이트
                    const progressPercentage = calculateProgress(completedCount, totalDongs);
                    updateProgressBar(progressPercentage);
                    
                    // 동별 상태 시각화
                    updateDongStatus(data.completed_tasks || [], data.active_tasks || []);
                    
                    // 속도 계산 (간단히 현재까지의 평균)
                    const speed = Math.round(totalProperties / Math.max(1, completedCount));
                    document.getElementById('speed').textContent = speed || '-';
                    
                    // ETA 계산
                    const eta = calculateETA(completedCount, totalDongs, Date.now(), 0.5); // 동당 30분 가정
                    document.getElementById('eta').textContent = eta;
                    
                    // 현재 상태 업데이트
                    let statusHtml = '';
                    if (data.active_tasks && data.active_tasks.length > 0) {
                        statusHtml += '<h4>🔄 진행 중인 작업:</h4>';
                        data.active_tasks.forEach(task => {
                            statusHtml += `<div class="log-entry warning">▶️ ${task.dong_name}: ${task.total_collected}개 수집 완료</div>`;
                        });
                    }
                    
                    if (data.completed_tasks && data.completed_tasks.length > 0) {
                        statusHtml += '<h4>✅ 완료된 작업:</h4>';
                        data.completed_tasks.slice(-5).forEach(task => {
                            statusHtml += `<div class="log-entry success">✅ ${task.dong_name}: ${task.total_collected}개 매물</div>`;
                        });
                    }
                    
                    document.getElementById('current-status').innerHTML = statusHtml || '<p>진행 중인 작업이 없습니다.</p>';
                })
                .catch(error => {
                    document.getElementById('current-status').innerHTML = '<p class="error">❌ 상태 로드 실패: ' + error + '</p>';
                });
            
            // 로그 API 호출
            fetch('/api/logs')
                .then(response => response.json())
                .then(data => {
                    let logsHtml = '';
                    data.recent_logs.forEach(log => {
                        let icon = '📋';
                        let className = 'info';
                        
                        if (log.type === 'start') {
                            icon = '🚀';
                            className = 'info';
                        } else if (log.type === 'complete') {
                            icon = '✅';
                            className = 'success';
                        } else if (log.type === 'heartbeat') {
                            icon = '💓';
                            className = 'warning';
                        }
                        
                        logsHtml += `<div class="log-entry ${className}">${icon} ${log.timestamp}: ${log.message}</div>`;
                    });
                    
                    document.getElementById('recent-logs').innerHTML = logsHtml || '<p>로그를 찾을 수 없습니다.</p>';
                })
                .catch(error => {
                    document.getElementById('recent-logs').innerHTML = '<p class="error">❌ 로그 로드 실패</p>';
                });
            
            // 결과 파일 API 호출
            fetch('/api/results')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('result-files').textContent = data.total_files;
                    
                    let filesHtml = '';
                    data.recent_files.forEach(file => {
                        filesHtml += `
                            <div class="log-entry">
                                📄 <strong>${file.filename}</strong><br>
                                📊 매물: ${file.property_count}개 | 💾 크기: ${file.size}MB | 🕐 ${file.modified}
                            </div>
                        `;
                    });
                    
                    document.getElementById('result-files-list').innerHTML = filesHtml || '<p>결과 파일을 찾을 수 없습니다.</p>';
                })
                .catch(error => {
                    document.getElementById('result-files-list').innerHTML = '<p class="error">❌ 파일 로드 실패</p>';
                });
        }
        
        // 페이지 로드시 및 30초마다 업데이트
        updateDashboard();
        setInterval(updateDashboard, 30000);
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
            # results 디렉토리 포함해서 여러 파일 패턴 시도
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
            
            # 가장 최신 파일 선택
            latest_file = max(files, key=os.path.getmtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 한국어 키 우선으로 다양한 키 시도
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
                    elif task_status == 'started':  # 'in_progress' 대신 'started' 확인
                        data['in_progress'] += 1
                        data['active_tasks'].append({
                            'dong_name': dong_name,
                            'total_collected': actual_count
                        })
            
            self.send_json_response(data)
            
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
    def send_logs_api(self):
        """로그 API 응답"""
        try:
            data = {'recent_logs': []}
            
            if os.path.exists('logs/live_progress.jsonl'):
                with open('logs/live_progress.jsonl', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                recent_lines = lines[-10:] if len(lines) >= 10 else lines
                
                for line in recent_lines:
                    try:
                        entry = json.loads(line.strip())
                        timestamp = entry.get('timestamp', 'Unknown')
                        entry_type = entry.get('type', 'Unknown')
                        dong_name = entry.get('dong_name', '')
                        total = entry.get('total_collected', '')
                        
                        message = ''
                        if entry_type == 'start':
                            message = f"{dong_name} 수집 시작"
                        elif entry_type == 'complete':
                            message = f"{dong_name} 완료 ({total}개)"
                        elif entry_type == 'heartbeat' and total:
                            message = f"{dong_name} 진행 중 ({total}개)"
                        else:
                            message = f"{entry_type} 이벤트"
                        
                        data['recent_logs'].append({
                            'timestamp': timestamp,
                            'type': entry_type,
                            'message': message
                        })
                        
                    except json.JSONDecodeError:
                        continue
            
            self.send_json_response(data)
            
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
    def send_results_api(self):
        """결과 파일 API 응답"""
        try:
            result_files = glob.glob("results/naver_optimized_*.json")
            result_files.sort(key=os.path.getmtime, reverse=True)
            
            data = {
                'total_files': len(result_files),
                'recent_files': []
            }
            
            for filepath in result_files[:5]:  # 최근 5개만
                try:
                    filename = os.path.basename(filepath)
                    file_size = os.path.getsize(filepath) / 1024 / 1024  # MB
                    mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    # 매물 개수는 간단히 매물번호 개수로 추정
                    property_count = 0
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                            property_count = content.count('"매물번호"')
                    except:
                        property_count = 0
                    
                    data['recent_files'].append({
                        'filename': filename,
                        'property_count': property_count,
                        'size': f"{file_size:.1f}",
                        'modified': mod_time.strftime('%Y-%m-%d %H:%M')
                    })
                    
                except Exception:
                    continue
            
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
    
    parser = argparse.ArgumentParser(description="로그 기반 수집기 웹 모니터링 대시보드")
    parser.add_argument("--port", type=int, default=8888, help="웹서버 포트 (기본값: 8888)")
    parser.add_argument("--host", default="0.0.0.0", help="웹서버 호스트 (기본값: 0.0.0.0)")
    args = parser.parse_args()
    
    port = args.port
    host = args.host
    
    # 현재 디렉토리에서 실행되는지 확인
    if not os.path.exists('logs') and not os.path.exists('results'):
        print("❌ logs/ 또는 results/ 디렉토리를 찾을 수 없습니다.")
        print("💡 collectors/ 디렉토리에서 실행해주세요.")
        return
    
    try:
        server = HTTPServer((host, port), CollectorMonitorHandler)
        print(f"🌐 모니터링 대시보드 시작: http://localhost:{port}")
        if host != "127.0.0.1" and host != "localhost":
            print(f"🌍 외부 접속 가능: http://<EC2-IP>:{port}")
        print(f"📊 실시간 업데이트: 30초마다 자동 새로고침")
        print(f"🔄 수동 새로고침: 페이지에서 새로고침 버튼 클릭")
        print("=" * 50)
        print("🛑 종료하려면 Ctrl+C를 눌러주세요")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 모니터링 서버를 종료합니다.")
    except Exception as e:
        print(f"❌ 서버 오류: {e}")

if __name__ == "__main__":
    main()