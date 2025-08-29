#!/usr/bin/env python3
"""
라이트웨이트 Job 스케줄러
- 메모리 사용량 <20MB
- 파일 기반 상태 관리
- 기존 수집기와 완벽 호환
"""

import json
import os
import time
import threading
import subprocess
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging
from dataclasses import dataclass, asdict
import pytz

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"

@dataclass
class Job:
    id: str
    name: str
    command: str
    schedule_type: str  # "once", "interval", "cron"
    schedule_value: str  # seconds for interval, cron expression for cron
    status: JobStatus
    created_at: str
    scheduled_for: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    output_file: Optional[str] = None
    pid: Optional[int] = None
    priority: int = 5  # 1(highest) - 10(lowest)
    max_runtime: int = 3600  # seconds
    retry_count: int = 0
    max_retries: int = 0

class LightweightScheduler:
    def __init__(self, data_dir: str = "./scheduler_data"):
        self.data_dir = data_dir
        self.jobs_file = os.path.join(data_dir, "jobs.json")
        self.running_jobs_file = os.path.join(data_dir, "running_jobs.json")
        self.logs_dir = os.path.join(data_dir, "job_logs")
        
        # 스케줄러 상태
        self.jobs: Dict[str, Job] = {}
        self.running_jobs: Dict[str, Dict] = {}  # job_id -> process_info
        self.scheduler_thread = None
        self.running = False
        
        # KST 시간대
        self.kst = pytz.timezone('Asia/Seoul')
        
        # 초기화
        self._initialize()
        
        # 로깅 설정 (최소화)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(data_dir, 'scheduler.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize(self):
        """스케줄러 초기화"""
        # 디렉토리 생성
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Job 데이터 로드
        self._load_jobs()
        self._load_running_jobs()
        
        # 시스템 종료 시 정리 핸들러
        signal.signal(signal.SIGINT, self._cleanup_handler)
        signal.signal(signal.SIGTERM, self._cleanup_handler)
    
    def _get_kst_time(self) -> datetime:
        """KST 현재 시간 반환"""
        return datetime.now(self.kst)
    
    def _load_jobs(self):
        """저장된 Job 데이터 로드"""
        if os.path.exists(self.jobs_file):
            try:
                with open(self.jobs_file, 'r', encoding='utf-8') as f:
                    jobs_data = json.load(f)
                    for job_id, job_dict in jobs_data.items():
                        job_dict['status'] = JobStatus(job_dict['status'])
                        self.jobs[job_id] = Job(**job_dict)
            except Exception as e:
                self.logger.error(f"Job 데이터 로드 실패: {e}")
                self.jobs = {}
    
    def _save_jobs(self):
        """Job 데이터 저장"""
        try:
            jobs_data = {}
            for job_id, job in self.jobs.items():
                job_dict = asdict(job)
                job_dict['status'] = job.status.value
                jobs_data[job_id] = job_dict
            
            with open(self.jobs_file, 'w', encoding='utf-8') as f:
                json.dump(jobs_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Job 데이터 저장 실패: {e}")
    
    def _load_running_jobs(self):
        """실행 중인 Job 정보 로드"""
        if os.path.exists(self.running_jobs_file):
            try:
                with open(self.running_jobs_file, 'r', encoding='utf-8') as f:
                    self.running_jobs = json.load(f)
                    
                # 프로세스 상태 확인 및 정리
                for job_id, proc_info in list(self.running_jobs.items()):
                    if not self._is_process_running(proc_info.get('pid')):
                        self.logger.info(f"좀비 프로세스 정리: {job_id}")
                        self._cleanup_job(job_id)
            except Exception as e:
                self.logger.error(f"실행 중인 Job 데이터 로드 실패: {e}")
                self.running_jobs = {}
    
    def _save_running_jobs(self):
        """실행 중인 Job 정보 저장"""
        try:
            with open(self.running_jobs_file, 'w', encoding='utf-8') as f:
                json.dump(self.running_jobs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"실행 중인 Job 데이터 저장 실패: {e}")
    
    def _is_process_running(self, pid: Optional[int]) -> bool:
        """프로세스 실행 상태 확인"""
        if not pid:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    def add_job(self, name: str, command: str, schedule_type: str = "once", 
                schedule_value: str = "0", priority: int = 5, max_runtime: int = 3600,
                max_retries: int = 0) -> str:
        """새 Job 추가"""
        job_id = f"{name}_{int(time.time())}"
        
        job = Job(
            id=job_id,
            name=name,
            command=command,
            schedule_type=schedule_type,
            schedule_value=schedule_value,
            status=JobStatus.PENDING,
            created_at=self._get_kst_time().isoformat(),
            priority=priority,
            max_runtime=max_runtime,
            max_retries=max_retries
        )
        
        # 스케줄 타입에 따른 다음 실행 시간 계산
        if schedule_type == "once":
            job.scheduled_for = self._get_kst_time().isoformat()
            job.status = JobStatus.SCHEDULED
        elif schedule_type == "interval":
            next_run = self._get_kst_time() + timedelta(seconds=int(schedule_value))
            job.scheduled_for = next_run.isoformat()
            job.status = JobStatus.SCHEDULED
        
        self.jobs[job_id] = job
        self._save_jobs()
        
        self.logger.info(f"새 Job 추가: {name} ({job_id})")
        return job_id
    
    def remove_job(self, job_id: str) -> bool:
        """Job 제거"""
        if job_id not in self.jobs:
            return False
        
        # 실행 중인 Job이면 중지
        if job_id in self.running_jobs:
            self.cancel_job(job_id)
        
        del self.jobs[job_id]
        self._save_jobs()
        
        self.logger.info(f"Job 제거됨: {job_id}")
        return True
    
    def cancel_job(self, job_id: str) -> bool:
        """실행 중인 Job 취소"""
        if job_id not in self.running_jobs:
            return False
        
        proc_info = self.running_jobs[job_id]
        pid = proc_info.get('pid')
        
        if pid and self._is_process_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                if self._is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)
                
                self.logger.info(f"Job 취소됨: {job_id} (PID: {pid})")
            except OSError as e:
                self.logger.error(f"Job 취소 실패: {job_id}, {e}")
        
        self._cleanup_job(job_id, JobStatus.CANCELLED)
        return True
    
    def _cleanup_job(self, job_id: str, status: JobStatus = JobStatus.FAILED):
        """Job 정리"""
        if job_id in self.running_jobs:
            del self.running_jobs[job_id]
            self._save_running_jobs()
        
        if job_id in self.jobs:
            self.jobs[job_id].status = status
            self.jobs[job_id].completed_at = self._get_kst_time().isoformat()
            self._save_jobs()
    
    def _execute_job(self, job: Job):
        """Job 실행"""
        self.logger.info(f"Job 실행 시작: {job.name} ({job.id})")
        
        # 상태 업데이트
        job.status = JobStatus.RUNNING
        job.started_at = self._get_kst_time().isoformat()
        self._save_jobs()
        
        # 로그 파일 경로
        log_file = os.path.join(self.logs_dir, f"{job.id}.log")
        
        try:
            # 프로세스 실행
            with open(log_file, 'w', encoding='utf-8') as f:
                process = subprocess.Popen(
                    job.command.split(),
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd()
                )
                
                # 실행 중인 Job 정보 저장
                proc_info = {
                    'pid': process.pid,
                    'started_at': job.started_at,
                    'log_file': log_file,
                    'max_runtime': job.max_runtime
                }
                self.running_jobs[job.id] = proc_info
                self._save_running_jobs()
                
                job.pid = process.pid
                job.output_file = log_file
                self._save_jobs()
                
                # 프로세스 완료 대기 (타임아웃 포함)
                try:
                    process.wait(timeout=job.max_runtime)
                    return_code = process.returncode
                    
                    if return_code == 0:
                        job.status = JobStatus.COMPLETED
                        self.logger.info(f"Job 완료: {job.name} ({job.id})")
                    else:
                        job.status = JobStatus.FAILED
                        job.error_message = f"Process exited with code {return_code}"
                        self.logger.error(f"Job 실패: {job.name}, 종료 코드: {return_code}")
                        
                except subprocess.TimeoutExpired:
                    process.kill()
                    job.status = JobStatus.FAILED
                    job.error_message = f"Timeout after {job.max_runtime} seconds"
                    self.logger.error(f"Job 타임아웃: {job.name}")
                    
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            self.logger.error(f"Job 실행 오류: {job.name}, {e}")
        
        finally:
            # 정리
            job.completed_at = self._get_kst_time().isoformat()
            job.pid = None
            self._save_jobs()
            
            if job.id in self.running_jobs:
                del self.running_jobs[job.id]
                self._save_running_jobs()
            
            # 재시도 처리
            if job.status == JobStatus.FAILED and job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.SCHEDULED
                next_retry = self._get_kst_time() + timedelta(minutes=5)  # 5분 후 재시도
                job.scheduled_for = next_retry.isoformat()
                self.logger.info(f"Job 재시도 예약: {job.name} ({job.retry_count}/{job.max_retries})")
            
            # 반복 Job 다음 실행 예약
            elif job.status == JobStatus.COMPLETED and job.schedule_type == "interval":
                next_run = self._get_kst_time() + timedelta(seconds=int(job.schedule_value))
                job.scheduled_for = next_run.isoformat()
                job.status = JobStatus.SCHEDULED
                job.started_at = None
                job.completed_at = None
                job.retry_count = 0
                self.logger.info(f"Job 다음 실행 예약: {job.name} at {job.scheduled_for}")
            
            self._save_jobs()
    
    def _scheduler_loop(self):
        """메인 스케줄러 루프"""
        while self.running:
            try:
                current_time = self._get_kst_time()
                
                # 실행할 Job 찾기
                scheduled_jobs = []
                for job in self.jobs.values():
                    if (job.status == JobStatus.SCHEDULED and 
                        job.scheduled_for and
                        datetime.fromisoformat(job.scheduled_for.replace('Z', '+00:00')) <= current_time):
                        scheduled_jobs.append(job)
                
                # 우선순위 순으로 정렬 (낮은 숫자 = 높은 우선순위)
                scheduled_jobs.sort(key=lambda j: j.priority)
                
                # Job 실행 (동시 실행 제한: 3개)
                max_concurrent = 3
                running_count = len(self.running_jobs)
                
                for job in scheduled_jobs:
                    if running_count >= max_concurrent:
                        break
                    
                    # 별도 스레드에서 Job 실행
                    job_thread = threading.Thread(
                        target=self._execute_job,
                        args=(job,),
                        daemon=True
                    )
                    job_thread.start()
                    running_count += 1
                
                # 실행 중인 Job 상태 확인 (프로세스 정리)
                for job_id, proc_info in list(self.running_jobs.items()):
                    if not self._is_process_running(proc_info.get('pid')):
                        self.logger.warning(f"비정상 종료된 Job 정리: {job_id}")
                        self._cleanup_job(job_id)
                
                time.sleep(10)  # 10초마다 스케줄 확인
                
            except Exception as e:
                self.logger.error(f"스케줄러 루프 오류: {e}")
                time.sleep(5)
    
    def start(self):
        """스케줄러 시작"""
        if self.running:
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.info("라이트웨이트 스케줄러 시작됨")
    
    def stop(self):
        """스케줄러 중지"""
        if not self.running:
            return
        
        self.running = False
        
        # 실행 중인 모든 Job 중지
        for job_id in list(self.running_jobs.keys()):
            self.cancel_job(job_id)
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("라이트웨이트 스케줄러 중지됨")
    
    def _cleanup_handler(self, signum, frame):
        """시스템 종료 시 정리"""
        self.logger.info(f"시그널 수신: {signum}, 정리 중...")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환"""
        status = {
            'running': self.running,
            'total_jobs': len(self.jobs),
            'pending_jobs': len([j for j in self.jobs.values() if j.status == JobStatus.PENDING]),
            'scheduled_jobs': len([j for j in self.jobs.values() if j.status == JobStatus.SCHEDULED]),
            'running_jobs': len(self.running_jobs),
            'completed_jobs': len([j for j in self.jobs.values() if j.status == JobStatus.COMPLETED]),
            'failed_jobs': len([j for j in self.jobs.values() if j.status == JobStatus.FAILED]),
            'jobs': [asdict(job) for job in self.jobs.values()],
            'running_processes': self.running_jobs
        }
        
        # JobStatus enum을 문자열로 변환
        for job_data in status['jobs']:
            job_data['status'] = job_data['status'].value if hasattr(job_data['status'], 'value') else str(job_data['status'])
        
        return status


# 편의 함수들
def create_collection_job(dong_name: str, priority: int = 5) -> str:
    """부동산 수집 Job 생성"""
    command = f"python log_based_collector.py --test-single {dong_name}"
    return f"collect_{dong_name}_{int(time.time())}"

def create_full_collection_job(max_workers: int = 1, priority: int = 3) -> str:
    """전체 강남구 수집 Job 생성"""
    command = f"python log_based_collector.py --max-workers {max_workers}"
    return f"full_collection_{int(time.time())}"


if __name__ == "__main__":
    # 테스트 실행
    scheduler = LightweightScheduler()
    scheduler.start()
    
    try:
        # 테스트 Job 추가
        job_id = scheduler.add_job(
            name="test_collection",
            command="python log_based_collector.py --test-single 역삼동",
            schedule_type="once",
            priority=5
        )
        
        print(f"테스트 Job 추가됨: {job_id}")
        print("스케줄러 실행 중... (Ctrl+C로 종료)")
        
        while True:
            time.sleep(30)
            status = scheduler.get_status()
            print(f"상태 - 총 Job: {status['total_jobs']}, 실행 중: {status['running_jobs']}")
            
    except KeyboardInterrupt:
        print("\n스케줄러 종료 중...")
        scheduler.stop()