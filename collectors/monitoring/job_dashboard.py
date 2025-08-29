#!/usr/bin/env python3
"""
통합 Job 관리 대시보드
- 기존 simple_monitor 확장
- Job 스케줄링 UI 추가
- 경량화된 웹 인터페이스
"""

import json
import os
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import glob
from lightweight_scheduler import LightweightScheduler, JobStatus

class JobDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, scheduler=None, **kwargs):
        self.scheduler = scheduler
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            self.send_main_dashboard()
        elif self.path == '/api/status':
            self.send_status_api()
        elif self.path == '/api/jobs':
            self.send_jobs_api()
        elif self.path == '/api/logs':
            self.send_logs_api()
        elif self.path == '/api/results':
            self.send_results_api()
        elif self.path.startswith('/api/job/'):
            self.handle_job_api()
        else:
            super().do_GET()
    
    def do_POST(self):
        if self.path.startswith('/api/job'):
            self.handle_job_post()
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_job_post(self):
        """Job 관련 POST 요청 처리"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            if self.path == '/api/job/create':
                self.create_job(data)
            elif self.path == '/api/job/cancel':
                self.cancel_job(data)
            elif self.path == '/api/job/remove':
                self.remove_job(data)
            else:
                self.send_json_response({'error': 'Unknown endpoint'}, 404)
                
        except Exception as e:
            self.send_json_response({'error': str(e)}, 500)
    
    def create_job(self, data):
        """새 Job 생성"""
        try:
            name = data.get('name', '')
            job_type = data.get('type', 'single')
            dong_name = data.get('dong_name', '')
            schedule_type = data.get('schedule_type', 'once')
            schedule_value = data.get('schedule_value', '0')
            priority = int(data.get('priority', 5))
            max_retries = int(data.get('max_retries', 0))
            
            # 명령어 생성
            if job_type == 'single':
                if not dong_name:
                    raise ValueError("동 이름이 필요합니다")
                command = f"python log_based_collector.py --test-single {dong_name}"
                job_name = f"수집_{dong_name}"
            elif job_type == 'full':
                max_workers = int(data.get('max_workers', 1))
                command = f"python log_based_collector.py --max-workers {max_workers}"
                job_name = f"전체수집_{max_workers}프로세스"
            else:
                raise ValueError("잘못된 Job 타입입니다")
            
            if name:
                job_name = name
            
            # Job 추가
            job_id = self.scheduler.add_job(
                name=job_name,
                command=command,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                priority=priority,
                max_retries=max_retries,
                max_runtime=7200  # 2시간
            )
            
            self.send_json_response({
                'success': True,
                'job_id': job_id,
                'message': f'Job이 생성되었습니다: {job_name}'
            })
            
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def cancel_job(self, data):
        """Job 취소"""
        try:
            job_id = data.get('job_id')
            if not job_id:
                raise ValueError("Job ID가 필요합니다")
            
            success = self.scheduler.cancel_job(job_id)
            if success:
                self.send_json_response({
                    'success': True,
                    'message': f'Job이 취소되었습니다: {job_id}'
                })
            else:
                self.send_json_response({'error': '취소할 수 없습니다'}, 400)
                
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def remove_job(self, data):
        """Job 제거"""
        try:
            job_id = data.get('job_id')
            if not job_id:
                raise ValueError("Job ID가 필요합니다")
            
            success = self.scheduler.remove_job(job_id)
            if success:
                self.send_json_response({
                    'success': True,
                    'message': f'Job이 제거되었습니다: {job_id}'
                })
            else:
                self.send_json_response({'error': '제거할 수 없습니다'}, 400)
                
        except Exception as e:
            self.send_json_response({'error': str(e)}, 400)
    
    def send_main_dashboard(self):
        """메인 대시보드 HTML"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>라이트웨이트 Job 관리 대시보드</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f7fa; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 1.1em; }
        .header-buttons { margin-top: 20px; }
        .btn { padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all 0.3s; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-primary { background: #007bff; color: white; }
        .btn-primary:hover { background: #0056b3; transform: translateY(-2px); }
        .btn-success { background: #28a745; color: white; }
        .btn-success:hover { background: #1e7e34; transform: translateY(-2px); }
        .btn-warning { background: #ffc107; color: #212529; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn-sm { padding: 6px 12px; font-size: 0.875em; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; border-radius: 12px; padding: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border: 1px solid #e9ecef; }
        .card h3 { color: #343a40; margin-bottom: 20px; font-size: 1.3em; }
        
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { text-align: center; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 10px; }
        .stat-number { font-size: 2.5em; font-weight: bold; color: #495057; margin-bottom: 5px; }
        .stat-label { color: #6c757d; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .job-list { max-height: 400px; overflow-y: auto; }
        .job-item { padding: 15px; margin: 10px 0; border-radius: 8px; border: 1px solid #dee2e6; background: #f8f9fa; }
        .job-item.running { border-left: 4px solid #007bff; background: #e7f3ff; }
        .job-item.completed { border-left: 4px solid #28a745; background: #e8f5e9; }
        .job-item.failed { border-left: 4px solid #dc3545; background: #f8d7da; }
        .job-item.scheduled { border-left: 4px solid #ffc107; background: #fff3cd; }
        
        .job-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .job-title { font-weight: bold; color: #343a40; }
        .job-status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: 600; text-transform: uppercase; }
        .job-details { font-size: 0.9em; color: #6c757d; }
        .job-actions { margin-top: 10px; }
        
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; font-weight: 600; color: #495057; }
        .form-control { width: 100%; padding: 12px; border: 1px solid #ced4da; border-radius: 6px; font-size: 1em; }
        .form-control:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,0.25); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 10% auto; padding: 30px; border-radius: 12px; width: 90%; max-width: 600px; max-height: 80vh; overflow-y: auto; }
        .close { float: right; font-size: 28px; font-weight: bold; cursor: pointer; color: #aaa; }
        .close:hover { color: #000; }
        
        .alert { padding: 15px; margin-bottom: 20px; border-radius: 6px; }
        .alert-success { background-color: #d4edda; border-color: #c3e6cb; color: #155724; }
        .alert-danger { background-color: #f8d7da; border-color: #f5c6cb; color: #721c24; }
        
        .dong-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin: 15px 0; }
        .dong-btn { padding: 10px; background: #e9ecef; border: 1px solid #ced4da; border-radius: 6px; cursor: pointer; text-align: center; transition: all 0.2s; }
        .dong-btn:hover { background: #007bff; color: white; }
        .dong-btn.selected { background: #007bff; color: white; }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header { padding: 20px; }
            .grid { grid-template-columns: 1fr; }
            .form-row { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 라이트웨이트 Job 관리 시스템</h1>
            <p>네이버 부동산 수집기용 경량 스케줄러 & 모니터링</p>
            <div class="header-buttons">
                <button class="btn btn-primary" onclick="showCreateJobModal()">➕ 새 Job 생성</button>
                <button class="btn btn-success" onclick="refreshData()">🔄 새로고침</button>
                <button class="btn btn-warning" onclick="showSystemInfo()">📊 시스템 정보</button>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number" id="total-jobs">-</div>
                <div class="stat-label">총 Job 수</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="running-jobs">-</div>
                <div class="stat-label">실행 중</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="scheduled-jobs">-</div>
                <div class="stat-label">예약됨</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="completed-jobs">-</div>
                <div class="stat-label">완료됨</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="failed-jobs">-</div>
                <div class="stat-label">실패</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>⚡ 활성 Job 목록</h3>
                <div class="job-list" id="active-jobs">로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>📋 전체 Job 목록</h3>
                <div class="job-list" id="all-jobs">로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>📊 수집 현황</h3>
                <div id="collection-status">로딩 중...</div>
            </div>
            
            <div class="card">
                <h3>📁 최근 결과</h3>
                <div id="recent-results">로딩 중...</div>
            </div>
        </div>
    </div>

    <!-- Job 생성 모달 -->
    <div id="createJobModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeModal('createJobModal')">&times;</span>
            <h2>➕ 새 Job 생성</h2>
            <div id="job-alert"></div>
            
            <form id="jobForm">
                <div class="form-group">
                    <label class="form-label">Job 이름</label>
                    <input type="text" class="form-control" id="job-name" placeholder="예: 강남구_오후_수집">
                </div>
                
                <div class="form-group">
                    <label class="form-label">수집 타입</label>
                    <select class="form-control" id="job-type" onchange="toggleJobTypeOptions()">
                        <option value="single">단일 동 수집</option>
                        <option value="full">전체 강남구 수집</option>
                    </select>
                </div>
                
                <div class="form-group" id="dong-selection">
                    <label class="form-label">대상 동 선택</label>
                    <div class="dong-grid">
                        <div class="dong-btn" onclick="selectDong(this, '역삼동')">역삼동</div>
                        <div class="dong-btn" onclick="selectDong(this, '삼성동')">삼성동</div>
                        <div class="dong-btn" onclick="selectDong(this, '논현동')">논현동</div>
                        <div class="dong-btn" onclick="selectDong(this, '대치동')">대치동</div>
                        <div class="dong-btn" onclick="selectDong(this, '신사동')">신사동</div>
                        <div class="dong-btn" onclick="selectDong(this, '압구정동')">압구정동</div>
                        <div class="dong-btn" onclick="selectDong(this, '청담동')">청담동</div>
                        <div class="dong-btn" onclick="selectDong(this, '도곡동')">도곡동</div>
                        <div class="dong-btn" onclick="selectDong(this, '개포동')">개포동</div>
                        <div class="dong-btn" onclick="selectDong(this, '수서동')">수서동</div>
                        <div class="dong-btn" onclick="selectDong(this, '일원동')">일원동</div>
                        <div class="dong-btn" onclick="selectDong(this, '자곡동')">자곡동</div>
                        <div class="dong-btn" onclick="selectDong(this, '세곡동')">세곡동</div>
                        <div class="dong-btn" onclick="selectDong(this, '율현동')">율현동</div>
                    </div>
                    <input type="hidden" id="selected-dong">
                </div>
                
                <div class="form-group" id="workers-selection" style="display: none;">
                    <label class="form-label">병렬 프로세스 수</label>
                    <select class="form-control" id="max-workers">
                        <option value="1">1개 (안전)</option>
                        <option value="2">2개 (권장)</option>
                        <option value="3">3개 (고성능)</option>
                    </select>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">스케줄 타입</label>
                        <select class="form-control" id="schedule-type" onchange="toggleScheduleOptions()">
                            <option value="once">즉시 실행</option>
                            <option value="interval">반복 실행</option>
                        </select>
                    </div>
                    
                    <div class="form-group" id="interval-selection" style="display: none;">
                        <label class="form-label">반복 주기 (초)</label>
                        <select class="form-control" id="schedule-value">
                            <option value="3600">1시간마다</option>
                            <option value="21600">6시간마다</option>
                            <option value="43200">12시간마다</option>
                            <option value="86400">24시간마다</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">우선순위 (1=높음, 10=낮음)</label>
                        <select class="form-control" id="job-priority">
                            <option value="1">1 (최고)</option>
                            <option value="3">3 (높음)</option>
                            <option value="5" selected>5 (보통)</option>
                            <option value="7">7 (낮음)</option>
                            <option value="10">10 (최저)</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label class="form-label">재시도 횟수</label>
                        <select class="form-control" id="max-retries">
                            <option value="0">재시도 안함</option>
                            <option value="1">1회</option>
                            <option value="2">2회</option>
                            <option value="3">3회</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-group">
                    <button type="button" class="btn btn-success" onclick="createJob()">🚀 Job 생성</button>
                    <button type="button" class="btn" onclick="closeModal('createJobModal')">취소</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let refreshInterval;
        
        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            refreshInterval = setInterval(refreshData, 30000); // 30초마다
        });
        
        function refreshData() {
            loadJobsData();
            loadCollectionStatus();
            loadResults();
        }
        
        function loadJobsData() {
            fetch('/api/jobs')
                .then(response => response.json())
                .then(data => {
                    updateStats(data);
                    updateJobLists(data);
                })
                .catch(error => console.error('Jobs 로드 실패:', error));
        }
        
        function updateStats(data) {
            document.getElementById('total-jobs').textContent = data.total_jobs || 0;
            document.getElementById('running-jobs').textContent = data.running_jobs || 0;
            document.getElementById('scheduled-jobs').textContent = data.scheduled_jobs || 0;
            document.getElementById('completed-jobs').textContent = data.completed_jobs || 0;
            document.getElementById('failed-jobs').textContent = data.failed_jobs || 0;
        }
        
        function updateJobLists(data) {
            const activeJobs = data.jobs.filter(job => 
                job.status === 'running' || job.status === 'scheduled'
            );
            
            // 활성 Job 목록
            const activeJobsHtml = activeJobs.map(job => createJobItemHtml(job)).join('');
            document.getElementById('active-jobs').innerHTML = activeJobsHtml || '<p>활성 Job이 없습니다.</p>';
            
            // 전체 Job 목록 (최근 20개)
            const recentJobs = data.jobs.slice(-20).reverse();
            const allJobsHtml = recentJobs.map(job => createJobItemHtml(job)).join('');
            document.getElementById('all-jobs').innerHTML = allJobsHtml || '<p>Job이 없습니다.</p>';
        }
        
        function createJobItemHtml(job) {
            const statusClass = job.status.toLowerCase();
            const statusText = getStatusText(job.status);
            const statusColor = getStatusColor(job.status);
            
            let actionButtons = '';
            if (job.status === 'running') {
                actionButtons = `<button class="btn btn-danger btn-sm" onclick="cancelJob('${job.id}')">⏹️ 취소</button>`;
            } else if (job.status === 'failed' || job.status === 'completed') {
                actionButtons = `<button class="btn btn-danger btn-sm" onclick="removeJob('${job.id}')">🗑️ 제거</button>`;
            }
            
            const scheduledTime = job.scheduled_for ? 
                `예약: ${new Date(job.scheduled_for).toLocaleString('ko-KR')}` : '';
            const createdTime = new Date(job.created_at).toLocaleString('ko-KR');
            
            return `
                <div class="job-item ${statusClass}">
                    <div class="job-header">
                        <div class="job-title">${job.name}</div>
                        <div class="job-status" style="background-color: ${statusColor};">${statusText}</div>
                    </div>
                    <div class="job-details">
                        <div>명령어: <code>${job.command}</code></div>
                        <div>생성: ${createdTime}</div>
                        ${scheduledTime ? `<div>${scheduledTime}</div>` : ''}
                        ${job.error_message ? `<div style="color: red;">오류: ${job.error_message}</div>` : ''}
                    </div>
                    <div class="job-actions">
                        ${actionButtons}
                        <span style="font-size: 0.8em; color: #6c757d;">우선순위: ${job.priority}</span>
                    </div>
                </div>
            `;
        }
        
        function getStatusText(status) {
            const statusMap = {
                'pending': '대기',
                'scheduled': '예약됨',
                'running': '실행 중',
                'completed': '완료',
                'failed': '실패',
                'cancelled': '취소됨'
            };
            return statusMap[status] || status;
        }
        
        function getStatusColor(status) {
            const colorMap = {
                'pending': '#6c757d',
                'scheduled': '#ffc107',
                'running': '#007bff',
                'completed': '#28a745',
                'failed': '#dc3545',
                'cancelled': '#6c757d'
            };
            return colorMap[status] || '#6c757d';
        }
        
        function loadCollectionStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    let html = '<h4>🏘️ 동별 수집 현황</h4>';
                    
                    if (data.active_tasks && data.active_tasks.length > 0) {
                        html += '<div style="margin: 10px 0;"><strong>진행 중:</strong></div>';
                        data.active_tasks.forEach(task => {
                            html += `<div style="margin: 5px 0; padding: 8px; background: #fff3cd; border-radius: 4px;">
                                🔄 ${task.dong_name}: ${task.total_collected}개 수집 중
                            </div>`;
                        });
                    }
                    
                    if (data.completed_tasks && data.completed_tasks.length > 0) {
                        html += '<div style="margin: 15px 0 10px;"><strong>최근 완료:</strong></div>';
                        data.completed_tasks.slice(-5).forEach(task => {
                            html += `<div style="margin: 5px 0; padding: 8px; background: #d4edda; border-radius: 4px;">
                                ✅ ${task.dong_name}: ${task.total_collected}개 완료
                            </div>`;
                        });
                    }
                    
                    if (!data.active_tasks?.length && !data.completed_tasks?.length) {
                        html += '<p style="color: #6c757d;">현재 진행 중인 수집이 없습니다.</p>';
                    }
                    
                    document.getElementById('collection-status').innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('collection-status').innerHTML = '<p style="color: red;">데이터 로드 실패</p>';
                });
        }
        
        function loadResults() {
            fetch('/api/results')
                .then(response => response.json())
                .then(data => {
                    let html = `<div style="margin-bottom: 15px;"><strong>총 ${data.total_files}개 파일</strong></div>`;
                    
                    if (data.recent_files && data.recent_files.length > 0) {
                        data.recent_files.forEach(file => {
                            html += `<div style="margin: 8px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #007bff;">
                                <div><strong>${file.filename}</strong></div>
                                <div style="font-size: 0.9em; color: #6c757d;">
                                    📊 ${file.property_count}개 매물 | 💾 ${file.size}MB | 🕐 ${file.modified}
                                </div>
                            </div>`;
                        });
                    } else {
                        html += '<p style="color: #6c757d;">결과 파일이 없습니다.</p>';
                    }
                    
                    document.getElementById('recent-results').innerHTML = html;
                })
                .catch(error => {
                    document.getElementById('recent-results').innerHTML = '<p style="color: red;">데이터 로드 실패</p>';
                });
        }
        
        // Job 관리 함수들
        function showCreateJobModal() {
            document.getElementById('createJobModal').style.display = 'block';
            document.getElementById('job-alert').innerHTML = '';
        }
        
        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }
        
        function toggleJobTypeOptions() {
            const jobType = document.getElementById('job-type').value;
            const dongSelection = document.getElementById('dong-selection');
            const workersSelection = document.getElementById('workers-selection');
            
            if (jobType === 'single') {
                dongSelection.style.display = 'block';
                workersSelection.style.display = 'none';
            } else {
                dongSelection.style.display = 'none';
                workersSelection.style.display = 'block';
            }
        }
        
        function toggleScheduleOptions() {
            const scheduleType = document.getElementById('schedule-type').value;
            const intervalSelection = document.getElementById('interval-selection');
            
            intervalSelection.style.display = scheduleType === 'interval' ? 'block' : 'none';
        }
        
        function selectDong(element, dongName) {
            // 기존 선택 제거
            document.querySelectorAll('.dong-btn').forEach(btn => btn.classList.remove('selected'));
            // 새 선택 추가
            element.classList.add('selected');
            document.getElementById('selected-dong').value = dongName;
        }
        
        function createJob() {
            const formData = {
                name: document.getElementById('job-name').value,
                type: document.getElementById('job-type').value,
                dong_name: document.getElementById('selected-dong').value,
                max_workers: document.getElementById('max-workers').value,
                schedule_type: document.getElementById('schedule-type').value,
                schedule_value: document.getElementById('schedule-value').value,
                priority: document.getElementById('job-priority').value,
                max_retries: document.getElementById('max-retries').value
            };
            
            // 유효성 검사
            if (formData.type === 'single' && !formData.dong_name) {
                showAlert('동을 선택해주세요.', 'danger');
                return;
            }
            
            fetch('/api/job/create', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert(data.message, 'success');
                    setTimeout(() => {
                        closeModal('createJobModal');
                        refreshData();
                    }, 1500);
                } else {
                    showAlert(data.error, 'danger');
                }
            })
            .catch(error => {
                showAlert('Job 생성 실패: ' + error, 'danger');
            });
        }
        
        function cancelJob(jobId) {
            if (!confirm('이 Job을 취소하시겠습니까?')) return;
            
            fetch('/api/job/cancel', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: jobId})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    refreshData();
                } else {
                    alert('취소 실패: ' + data.error);
                }
            })
            .catch(error => alert('취소 실패: ' + error));
        }
        
        function removeJob(jobId) {
            if (!confirm('이 Job을 완전히 제거하시겠습니까?')) return;
            
            fetch('/api/job/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({job_id: jobId})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    refreshData();
                } else {
                    alert('제거 실패: ' + data.error);
                }
            })
            .catch(error => alert('제거 실패: ' + error));
        }
        
        function showAlert(message, type) {
            const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
            document.getElementById('job-alert').innerHTML = 
                `<div class="alert ${alertClass}">${message}</div>`;
        }
        
        function showSystemInfo() {
            alert('시스템 정보\\n- 메모리 사용량: <100MB\\n- CPU 사용률: 최적화됨\\n- 스케줄러: 라이트웨이트 모드\\n- 동시 실행: 최대 3개 Job');
        }
        
        // 모달 외부 클릭시 닫기
        window.onclick = function(event) {
            const modal = document.getElementById('createJobModal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        }
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_jobs_api(self):
        """Jobs API 응답"""
        try:
            status = self.scheduler.get_status()
            self.send_json_response(status)
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
    def send_status_api(self):
        """기존 collection 상태 API 호환성 유지"""
        try:
            data = {
                'completed': 0,
                'in_progress': 0,
                'total_properties': 0,
                'active_tasks': [],
                'completed_tasks': []
            }
            
            # status.json에서 수집 상태 읽기
            if os.path.exists('logs/status.json'):
                with open('logs/status.json', 'r', encoding='utf-8') as f:
                    status = json.load(f)
                
                for task_id, task_info in status.items():
                    task_status = task_info.get('status', 'unknown')
                    details = task_info.get('details', {})
                    dong_name = details.get('dong_name', 'Unknown')
                    
                    if task_status == 'completed':
                        data['completed'] += 1
                        actual_count = self.get_actual_property_count(dong_name) if dong_name != 'Unknown' else 0
                        data['total_properties'] += actual_count
                        data['completed_tasks'].append({
                            'dong_name': dong_name,
                            'total_collected': actual_count
                        })
                    elif task_status == 'started':
                        data['in_progress'] += 1
                        actual_count = self.get_actual_property_count(dong_name) if dong_name != 'Unknown' else 0
                        data['active_tasks'].append({
                            'dong_name': dong_name,
                            'total_collected': actual_count
                        })
            
            self.send_json_response(data)
            
        except Exception as e:
            self.send_json_response({'error': str(e)})
    
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
        except Exception:
            return 0
    
    def send_logs_api(self):
        """로그 API 응답 (기존 호환성)"""
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
        """결과 파일 API 응답 (기존 호환성)"""
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
    
    def send_json_response(self, data, status_code=200):
        """JSON 응답 전송"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))


def create_handler(scheduler):
    """스케줄러를 주입받는 핸들러 팩토리"""
    def handler(*args, **kwargs):
        return JobDashboardHandler(*args, scheduler=scheduler, **kwargs)
    return handler


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="라이트웨이트 Job 관리 대시보드")
    parser.add_argument("--port", type=int, default=8888, help="웹서버 포트")
    parser.add_argument("--host", default="0.0.0.0", help="웹서버 호스트")
    parser.add_argument("--scheduler-data", default="./scheduler_data", help="스케줄러 데이터 디렉토리")
    args = parser.parse_args()
    
    # 스케줄러 초기화 및 시작
    scheduler = LightweightScheduler(data_dir=args.scheduler_data)
    scheduler.start()
    
    # 웹 서버 시작
    try:
        handler = create_handler(scheduler)
        server = HTTPServer((args.host, args.port), handler)
        
        print(f"🚀 라이트웨이트 Job 관리 대시보드 시작")
        print(f"🌐 URL: http://localhost:{args.port}")
        if args.host != "127.0.0.1" and args.host != "localhost":
            print(f"🌍 외부 접속: http://<EC2-IP>:{args.port}")
        print(f"📊 스케줄러: {args.scheduler_data}")
        print(f"🔄 자동 새로고침: 30초")
        print("=" * 50)
        print("🛑 종료: Ctrl+C")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 서버 종료 중...")
        scheduler.stop()
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
        scheduler.stop()


if __name__ == "__main__":
    main()