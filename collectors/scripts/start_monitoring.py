#!/usr/bin/env python3
"""
Quick Start Script for Real-time Monitoring System
Handles the current zombie processes and starts new monitoring
"""

import asyncio
import os
import signal
import time
import psutil
import json
from pathlib import Path

async def kill_zombie_processes():
    """Identify and terminate zombie collection processes"""
    print("🕵️ Detecting zombie processes...")
    
    zombie_processes = []
    
    # Look for Python processes running collectors
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if proc.info['name'] == 'python3' and proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                
                # Check if it's a collector process
                if 'collector' in cmdline.lower() or 'log_based' in cmdline:
                    runtime_hours = (time.time() - proc.info['create_time']) / 3600
                    
                    # Consider it zombie if running >2 hours
                    if runtime_hours > 2:
                        zombie_processes.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline,
                            'runtime_hours': runtime_hours
                        })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if zombie_processes:
        print(f"🧟 Found {len(zombie_processes)} zombie processes:")
        for proc in zombie_processes:
            print(f"  PID {proc['pid']}: {proc['runtime_hours']:.1f}h - {proc['cmdline'][:80]}...")
        
        response = input("\n❓ Terminate zombie processes? (y/N): ")
        if response.lower() == 'y':
            for proc in zombie_processes:
                try:
                    os.kill(proc['pid'], signal.SIGTERM)
                    print(f"  ✅ Terminated PID {proc['pid']}")
                    time.sleep(1)  # Give process time to die gracefully
                    
                    # Force kill if still alive
                    try:
                        os.kill(proc['pid'], signal.SIGKILL)
                        print(f"  🔫 Force killed PID {proc['pid']}")
                    except ProcessLookupError:
                        pass  # Already dead
                        
                except ProcessLookupError:
                    print(f"  💀 PID {proc['pid']} already dead")
                except Exception as e:
                    print(f"  ❌ Failed to kill PID {proc['pid']}: {e}")
    else:
        print("✅ No zombie processes found")

def check_log_file_size():
    """Check current log file size and suggest rotation"""
    log_file = Path("logs/live_progress.jsonl")
    
    if log_file.exists():
        size_mb = log_file.stat().st_size / (1024 * 1024)
        line_count = sum(1 for _ in open(log_file, 'r'))
        
        print(f"📊 Current log file: {size_mb:.1f}MB ({line_count:,} lines)")
        
        if size_mb > 50:
            print("⚠️  Log file is large - rotation recommended")
            response = input("❓ Rotate log file now? (y/N): ")
            if response.lower() == 'y':
                # Backup current log
                backup_name = f"logs/live_progress_backup_{int(time.time())}.jsonl"
                os.rename(str(log_file), backup_name)
                print(f"  📁 Backed up to: {backup_name}")
    else:
        print("📄 No existing log file found")

def check_status_file():
    """Check and clean status file"""
    status_file = Path("logs/status.json")
    
    if status_file.exists():
        try:
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            
            print(f"📋 Status file: {len(status_data)} tracked tasks")
            
            # Show long-running tasks
            current_time = time.time()
            long_running = []
            
            for task_id, task_info in status_data.items():
                if task_info.get('status') in ['started', 'in_progress']:
                    timestamp = task_info.get('timestamp', current_time)
                    age_hours = (current_time - timestamp) / 3600
                    
                    if age_hours > 1:  # More than 1 hour
                        long_running.append({
                            'task_id': task_id,
                            'dong_name': task_info.get('details', {}).get('dong_name', 'Unknown'),
                            'status': task_info.get('status'),
                            'age_hours': age_hours
                        })
            
            if long_running:
                print("⏰ Long-running tasks:")
                for task in long_running:
                    print(f"  {task['dong_name']} ({task['task_id']}): {task['age_hours']:.1f}h - {task['status']}")
                
                response = input("❓ Clean up stale status entries? (y/N): ")
                if response.lower() == 'y':
                    # Remove stale entries
                    cleaned_data = {}
                    for task_id, task_info in status_data.items():
                        if task_info.get('status') not in ['started', 'in_progress']:
                            cleaned_data[task_id] = task_info
                        else:
                            timestamp = task_info.get('timestamp', current_time)
                            age_hours = (current_time - timestamp) / 3600
                            if age_hours <= 1:  # Keep recent tasks
                                cleaned_data[task_id] = task_info
                    
                    # Write cleaned status
                    with open(status_file, 'w') as f:
                        json.dump(cleaned_data, f, indent=2)
                    
                    print(f"  🧹 Cleaned status file: {len(status_data)} → {len(cleaned_data)} entries")
            
        except Exception as e:
            print(f"❌ Error reading status file: {e}")
    else:
        print("📄 No status file found")

async def check_system_resources():
    """Check system resources"""
    print("💻 System Resources:")
    
    # CPU usage
    cpu_usage = psutil.cpu_percent(interval=1)
    print(f"  CPU: {cpu_usage:.1f}%")
    
    # Memory usage
    memory = psutil.virtual_memory()
    print(f"  Memory: {memory.percent:.1f}% ({memory.available / (1024**3):.1f}GB available)")
    
    # Disk usage
    disk = psutil.disk_usage('/')
    print(f"  Disk: {disk.percent:.1f}% ({disk.free / (1024**3):.1f}GB free)")
    
    # Process count
    python_processes = len([p for p in psutil.process_iter() if p.name() == 'python3'])
    print(f"  Python processes: {python_processes}")

def start_monitoring_api():
    """Start the monitoring API server"""
    print("\n🚀 Starting Monitoring API Server...")
    
    # Check if dependencies are installed
    try:
        import fastapi
        import uvicorn
        import redis
        print("  ✅ Dependencies available")
    except ImportError as e:
        print(f"  ❌ Missing dependency: {e}")
        print("  📦 Install with: pip install -r requirements_monitoring.txt")
        return False
    
    try:
        # Start the API server
        import subprocess
        cmd = ["python", "-m", "uvicorn", "monitoring_api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
        print(f"  🔧 Command: {' '.join(cmd)}")
        
        response = input("❓ Start monitoring API? (y/N): ")
        if response.lower() == 'y':
            subprocess.Popen(cmd)
            print("  🌐 API starting at http://localhost:8000")
            print("  📊 Dashboard: http://localhost:8000/dashboard.html")
            return True
        
    except Exception as e:
        print(f"  ❌ Failed to start API: {e}")
    
    return False

async def main():
    """Main startup sequence"""
    print("🚀 Real-time Monitoring System - Quick Start")
    print("=" * 60)
    
    # Step 1: Clean up zombie processes
    await kill_zombie_processes()
    print()
    
    # Step 2: Check log files
    check_log_file_size()
    print()
    
    # Step 3: Check status file
    check_status_file()
    print()
    
    # Step 4: System resources
    await check_system_resources()
    print()
    
    # Step 5: Start monitoring
    start_monitoring_api()
    
    print("\n✅ Startup sequence completed!")
    print("\n📋 Next Steps:")
    print("1. Open http://localhost:8000/health to verify API")
    print("2. Open dashboard.html in browser for UI")
    print("3. Check logs/application.log for any errors")
    print("4. Monitor system resources and processes")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
    except Exception as e:
        print(f"\n❌ Startup error: {e}")