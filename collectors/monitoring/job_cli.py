#!/usr/bin/env python3
"""
라이트웨이트 Job 관리 CLI 도구
- 커맨드라인에서 Job 관리
- 시스템 상태 모니터링
- EC2 환경 최적화
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from lightweight_scheduler import LightweightScheduler, JobStatus
import subprocess

class JobCLI:
    def __init__(self, scheduler_data_dir="./scheduler_data"):
        self.scheduler = LightweightScheduler(data_dir=scheduler_data_dir)
        self.scheduler_data_dir = scheduler_data_dir
    
    def list_jobs(self, status_filter=None):
        """Job 목록 출력"""
        status = self.scheduler.get_status()
        jobs = status['jobs']
        
        if status_filter:
            jobs = [job for job in jobs if job['status'] == status_filter]
        
        if not jobs:
            print(f"📋 Job이 없습니다 {f'(상태: {status_filter})' if status_filter else ''}")
            return
        
        print(f"📋 Job 목록 {'(' + status_filter + ')' if status_filter else ''}:")
        print("=" * 80)
        
        for job in sorted(jobs, key=lambda x: x['created_at'], reverse=True):
            status_icon = self._get_status_icon(job['status'])
            created = datetime.fromisoformat(job['created_at']).strftime('%m-%d %H:%M')
            
            print(f"{status_icon} {job['name']:25s} | {job['id']:20s} | {created}")
            print(f"   명령어: {job['command']}")
            if job.get('scheduled_for'):
                scheduled = datetime.fromisoformat(job['scheduled_for']).strftime('%m-%d %H:%M')
                print(f"   예약시간: {scheduled}")
            if job.get('error_message'):
                print(f"   오류: {job['error_message'][:60]}...")
            print()
    
    def show_status(self):
        """전체 시스템 상태 출력"""
        status = self.scheduler.get_status()
        
        print("🚀 라이트웨이트 Job 스케줄러 상태")
        print("=" * 50)
        print(f"스케줄러 상태: {'🟢 실행 중' if status['running'] else '🔴 중지됨'}")
        print(f"총 Job 수: {status['total_jobs']}")
        print(f"실행 중: {status['running_jobs']}")
        print(f"예약됨: {status['scheduled_jobs']}")
        print(f"완료됨: {status['completed_jobs']}")
        print(f"실패: {status['failed_jobs']}")
        print()
        
        # 실행 중인 프로세스
        if status['running_processes']:
            print("⚡ 실행 중인 프로세스:")
            for job_id, proc_info in status['running_processes'].items():
                job = next((j for j in status['jobs'] if j['id'] == job_id), None)
                if job:
                    started = datetime.fromisoformat(proc_info['started_at']).strftime('%H:%M:%S')
                    print(f"  • {job['name']} (PID: {proc_info['pid']}, 시작: {started})")
            print()
        
        # 다음 예약된 Job
        scheduled_jobs = [job for job in status['jobs'] if job['status'] == 'scheduled']
        if scheduled_jobs:
            next_job = min(scheduled_jobs, key=lambda x: x['scheduled_for'])
            next_time = datetime.fromisoformat(next_job['scheduled_for']).strftime('%m-%d %H:%M')
            print(f"⏰ 다음 실행: {next_job['name']} ({next_time})")
        
        # 디스크 사용량
        self._show_disk_usage()
        
        # 메모리 사용량 (간단히)
        self._show_memory_usage()
    
    def create_job(self, args):
        """새 Job 생성"""
        if args.type == 'single':
            if not args.dong:
                print("❌ 단일 동 수집은 --dong 옵션이 필요합니다")
                return
            command = f"python log_based_collector.py --test-single {args.dong}"
            name = args.name or f"수집_{args.dong}"
        elif args.type == 'full':
            workers = args.workers or 1
            command = f"python log_based_collector.py --max-workers {workers}"
            name = args.name or f"전체수집_{workers}프로세스"
        else:
            print("❌ 잘못된 Job 타입입니다 (single 또는 full)")
            return
        
        try:
            job_id = self.scheduler.add_job(
                name=name,
                command=command,
                schedule_type=args.schedule,
                schedule_value=str(args.interval),
                priority=args.priority,
                max_retries=args.retries,
                max_runtime=args.timeout
            )
            
            print(f"✅ Job이 생성되었습니다:")
            print(f"   ID: {job_id}")
            print(f"   이름: {name}")
            print(f"   명령어: {command}")
            print(f"   스케줄: {args.schedule}")
            if args.schedule == 'interval':
                print(f"   주기: {args.interval}초")
            
        except Exception as e:
            print(f"❌ Job 생성 실패: {e}")
    
    def cancel_job(self, job_id):
        """Job 취소"""
        if self.scheduler.cancel_job(job_id):
            print(f"✅ Job이 취소되었습니다: {job_id}")
        else:
            print(f"❌ Job 취소 실패: {job_id} (실행 중이 아니거나 존재하지 않음)")
    
    def remove_job(self, job_id):
        """Job 제거"""
        if self.scheduler.remove_job(job_id):
            print(f"✅ Job이 제거되었습니다: {job_id}")
        else:
            print(f"❌ Job 제거 실패: {job_id} (존재하지 않음)")
    
    def start_scheduler(self, daemon=False):
        """스케줄러 시작"""
        if daemon:
            print("🚀 스케줄러를 데몬 모드로 시작합니다...")
            # 간단한 데몬 모드 (실제 프로덕션에서는 systemd 사용 권장)
            pid_file = os.path.join(self.scheduler_data_dir, "scheduler.pid")
            
            if os.path.exists(pid_file):
                print("⚠️ 스케줄러가 이미 실행 중입니다 (PID 파일 존재)")
                return
            
            # 백그라운드 실행
            cmd = [sys.executable, __file__, 'run', '--data-dir', self.scheduler_data_dir]
            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # PID 파일 생성
            with open(pid_file, 'w') as f:
                f.write(str(process.pid))
            
            print(f"✅ 스케줄러가 백그라운드에서 시작되었습니다 (PID: {process.pid})")
            print(f"📊 대시보드: python job_dashboard.py --scheduler-data {self.scheduler_data_dir}")
        else:
            print("🚀 스케줄러를 포그라운드 모드로 시작합니다...")
            print("🛑 종료하려면 Ctrl+C를 누르세요")
            
            self.scheduler.start()
            try:
                while True:
                    time.sleep(30)
                    # 간단한 상태 출력
                    status = self.scheduler.get_status()
                    if status['running_jobs'] > 0:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 실행 중인 Job: {status['running_jobs']}개")
            except KeyboardInterrupt:
                print("\n🛑 스케줄러를 종료합니다...")
                self.scheduler.stop()
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        pid_file = os.path.join(self.scheduler_data_dir, "scheduler.pid")
        
        if not os.path.exists(pid_file):
            print("⚠️ 실행 중인 스케줄러를 찾을 수 없습니다")
            return
        
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            os.kill(pid, 15)  # SIGTERM
            time.sleep(2)
            
            try:
                os.kill(pid, 0)  # 프로세스 확인
                print("⚠️ 프로세스가 종료되지 않아 강제 종료합니다...")
                os.kill(pid, 9)  # SIGKILL
            except OSError:
                pass  # 이미 종료됨
            
            os.remove(pid_file)
            print(f"✅ 스케줄러가 종료되었습니다 (PID: {pid})")
            
        except Exception as e:
            print(f"❌ 스케줄러 종료 실패: {e}")
    
    def show_logs(self, job_id=None, lines=10):
        """Job 로그 출력"""
        if job_id:
            log_file = os.path.join(self.scheduler_data_dir, "job_logs", f"{job_id}.log")
            if os.path.exists(log_file):
                print(f"📋 Job 로그: {job_id}")
                print("=" * 50)
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                    for line in log_lines[-lines:]:
                        print(line.rstrip())
            else:
                print(f"❌ 로그 파일을 찾을 수 없습니다: {job_id}")
        else:
            # 스케줄러 로그
            scheduler_log = os.path.join(self.scheduler_data_dir, "scheduler.log")
            if os.path.exists(scheduler_log):
                print("📋 스케줄러 로그 (최근 10줄)")
                print("=" * 50)
                with open(scheduler_log, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                    for line in log_lines[-lines:]:
                        print(line.rstrip())
            else:
                print("❌ 스케줄러 로그 파일이 없습니다")
    
    def quick_setup(self):
        """빠른 설정 - 일반적인 Job들을 미리 생성"""
        print("⚡ 빠른 설정을 시작합니다...")
        
        # 1. 전체 수집 Job (매일 새벽 2시)
        try:
            job_id = self.scheduler.add_job(
                name="일일_전체수집",
                command="python log_based_collector.py --max-workers 2",
                schedule_type="interval",
                schedule_value="86400",  # 24시간
                priority=1
            )
            print(f"✅ 일일 전체수집 Job 생성: {job_id}")
        except Exception as e:
            print(f"❌ 일일 전체수집 Job 생성 실패: {e}")
        
        # 2. 인기 동네 개별 수집 (6시간마다)
        popular_dongs = ["역삼동", "삼성동", "논현동", "대치동"]
        
        for dong in popular_dongs:
            try:
                job_id = self.scheduler.add_job(
                    name=f"정기수집_{dong}",
                    command=f"python log_based_collector.py --test-single {dong}",
                    schedule_type="interval",
                    schedule_value="21600",  # 6시간
                    priority=3
                )
                print(f"✅ {dong} 정기수집 Job 생성: {job_id}")
            except Exception as e:
                print(f"❌ {dong} 정기수집 Job 생성 실패: {e}")
        
        print("\n🎉 빠른 설정이 완료되었습니다!")
        print("📊 생성된 Job 목록을 확인하려면: python job_cli.py list")
        print("🚀 스케줄러를 시작하려면: python job_cli.py start --daemon")
    
    def _get_status_icon(self, status):
        """상태별 아이콘 반환"""
        icons = {
            'pending': '⏳',
            'scheduled': '🕐',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '⏹️'
        }
        return icons.get(status, '❓')
    
    def _show_disk_usage(self):
        """디스크 사용량 표시"""
        try:
            total, used, free = shutil.disk_usage('.')
            total_gb = total // (1024**3)
            used_gb = used // (1024**3)
            free_gb = free // (1024**3)
            
            print(f"💾 디스크 사용량: {used_gb}GB / {total_gb}GB (여유: {free_gb}GB)")
        except:
            print("💾 디스크 사용량: 확인 불가")
    
    def _show_memory_usage(self):
        """메모리 사용량 표시 (간단히)"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            print(f"🧠 메모리 사용량: {memory.percent:.1f}% ({memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB)")
        except ImportError:
            try:
                # psutil 없는 경우 /proc/meminfo 사용 (Linux)
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                    total = int([l for l in lines if l.startswith('MemTotal:')][0].split()[1]) // 1024
                    available = int([l for l in lines if l.startswith('MemAvailable:')][0].split()[1]) // 1024
                    used = total - available
                    print(f"🧠 메모리 사용량: {used}MB / {total}MB ({used/total*100:.1f}%)")
            except:
                print("🧠 메모리 사용량: 확인 불가")


def main():
    parser = argparse.ArgumentParser(description="라이트웨이트 Job 관리 CLI")
    parser.add_argument('--data-dir', default='./scheduler_data', help='스케줄러 데이터 디렉토리')
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # 목록 조회
    list_parser = subparsers.add_parser('list', help='Job 목록 조회')
    list_parser.add_argument('--status', choices=['pending', 'scheduled', 'running', 'completed', 'failed', 'cancelled'],
                           help='상태별 필터링')
    
    # 상태 조회
    subparsers.add_parser('status', help='시스템 상태 조회')
    
    # Job 생성
    create_parser = subparsers.add_parser('create', help='새 Job 생성')
    create_parser.add_argument('type', choices=['single', 'full'], help='Job 타입')
    create_parser.add_argument('--name', help='Job 이름')
    create_parser.add_argument('--dong', help='대상 동 (single 타입시 필수)')
    create_parser.add_argument('--workers', type=int, help='병렬 프로세스 수 (full 타입시)')
    create_parser.add_argument('--schedule', choices=['once', 'interval'], default='once', help='스케줄 타입')
    create_parser.add_argument('--interval', type=int, default=0, help='반복 주기(초)')
    create_parser.add_argument('--priority', type=int, default=5, help='우선순위 (1-10)')
    create_parser.add_argument('--retries', type=int, default=0, help='재시도 횟수')
    create_parser.add_argument('--timeout', type=int, default=3600, help='최대 실행 시간(초)')
    
    # Job 제어
    cancel_parser = subparsers.add_parser('cancel', help='실행 중인 Job 취소')
    cancel_parser.add_argument('job_id', help='취소할 Job ID')
    
    remove_parser = subparsers.add_parser('remove', help='Job 제거')
    remove_parser.add_argument('job_id', help='제거할 Job ID')
    
    # 스케줄러 제어
    start_parser = subparsers.add_parser('start', help='스케줄러 시작')
    start_parser.add_argument('--daemon', action='store_true', help='데몬 모드로 실행')
    
    subparsers.add_parser('stop', help='스케줄러 중지')
    subparsers.add_parser('run', help='스케줄러 실행 (내부용)')
    
    # 로그 조회
    logs_parser = subparsers.add_parser('logs', help='로그 조회')
    logs_parser.add_argument('--job-id', help='특정 Job의 로그 조회')
    logs_parser.add_argument('--lines', type=int, default=10, help='출력할 줄 수')
    
    # 빠른 설정
    subparsers.add_parser('setup', help='빠른 설정 - 일반적인 Job들 생성')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = JobCLI(scheduler_data_dir=args.data_dir)
    
    try:
        if args.command == 'list':
            cli.list_jobs(status_filter=args.status)
        
        elif args.command == 'status':
            cli.show_status()
        
        elif args.command == 'create':
            cli.create_job(args)
        
        elif args.command == 'cancel':
            cli.cancel_job(args.job_id)
        
        elif args.command == 'remove':
            cli.remove_job(args.job_id)
        
        elif args.command == 'start':
            cli.start_scheduler(daemon=args.daemon)
        
        elif args.command == 'stop':
            cli.stop_scheduler()
        
        elif args.command == 'run':
            # 내부용 - 데몬 모드 실제 실행
            print(f"[{datetime.now()}] 스케줄러 시작 (데몬 모드)")
            cli.scheduler.start()
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print(f"[{datetime.now()}] 스케줄러 종료 중...")
                cli.scheduler.stop()
        
        elif args.command == 'logs':
            cli.show_logs(job_id=args.job_id, lines=args.lines)
        
        elif args.command == 'setup':
            cli.quick_setup()
        
    except Exception as e:
        print(f"❌ 오류가 발생했습니다: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import shutil  # disk_usage용
    main()