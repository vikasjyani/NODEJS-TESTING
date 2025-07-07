# utils/job_manager.py
"""
Enhanced Job Management System
Handles background job lifecycle, progress tracking, and cleanup
"""
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

from utils.constants import JOB_STATUS, MAX_JOB_RUNTIME, CLEANUP_INTERVAL

logger = logging.getLogger(__name__)

@dataclass
class JobInfo:
    """Job information data class"""
    id: str
    status: str
    progress: int = 0
    current_step: Optional[str] = None
    processed_items: int = 0
    total_items: int = 0
    scenario_name: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    message: str = "Initializing..."
    error: Optional[str] = None
    result: Optional[Dict] = None
    retry_count: int = 0
    thread_id: Optional[int] = None
    items_completed: List[str] = field(default_factory=list)
    items_failed: List[str] = field(default_factory=list)
    detailed_log: List[Dict] = field(default_factory=list)
    configuration: Dict = field(default_factory=dict)

class JobManager:
    """
    Generic job manager for background tasks
    Thread-safe with automatic cleanup and monitoring
    """
    
    def __init__(self, cleanup_interval: int = CLEANUP_INTERVAL):
        self.jobs: Dict[str, JobInfo] = {}
        self.lock = threading.RLock()
        self.cleanup_interval = cleanup_interval
        self.cleanup_running = False
        self.job_stats = defaultdict(int)
        
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        if self.cleanup_running:
            return
        
        def cleanup_worker():
            self.cleanup_running = True
            try:
                while self.cleanup_running:
                    time.sleep(self.cleanup_interval)
                    self._cleanup_old_jobs()
                    self._check_stalled_jobs()
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
            finally:
                self.cleanup_running = False
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("Job cleanup thread started")
    
    def create_job(self, job_id: str, job_type: str = "generic", **kwargs) -> JobInfo:
        """Create a new job with comprehensive tracking"""
        with self.lock:
            job = JobInfo(
                id=job_id,
                status=JOB_STATUS['STARTING'],
                **kwargs
            )
            
            self.jobs[job_id] = job
            self.job_stats[f'created_{job_type}'] += 1
            
            self._add_log_entry(job_id, "Job created", "INFO")
            logger.info(f"Created job {job_id} of type {job_type}")
            return job
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job information with computed fields"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            
            # Convert to dict and add computed fields
            job_dict = job.__dict__.copy()
            
            # Add timing information
            current_time = time.time()
            job_dict['elapsed_seconds'] = current_time - job.start_time
            job_dict['idle_seconds'] = current_time - job.last_update
            
            # Add completion rate
            if job.total_items > 0:
                job_dict['completion_rate'] = len(job.items_completed) / job.total_items
            else:
                job_dict['completion_rate'] = 0
            
            # Add estimated completion time
            if job.progress > 0 and job.status == JOB_STATUS['RUNNING']:
                elapsed = current_time - job.start_time
                estimated_total = (elapsed / job.progress) * 100
                job_dict['estimated_remaining_seconds'] = max(0, estimated_total - elapsed)
            
            return job_dict
    
    def update_job(self, job_id: str, **updates) -> bool:
        """Update job with validation and logging"""
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Attempted to update non-existent job: {job_id}")
                return False
            
            job = self.jobs[job_id]
            old_progress = job.progress
            old_step = job.current_step
            
            # Validate progress updates
            if 'progress' in updates:
                progress = updates['progress']
                if not isinstance(progress, (int, float)) or progress < 0 or progress > 100:
                    logger.warning(f"Invalid progress value for job {job_id}: {progress}")
                    updates['progress'] = max(0, min(100, int(progress)))
                
                # Prevent progress rollback unless explicitly allowed
                if updates['progress'] < old_progress and 'allow_rollback' not in updates:
                    updates['progress'] = old_progress
            
            # Update job fields
            for key, value in updates.items():
                if key == 'allow_rollback':
                    continue  # Skip internal flag
                if hasattr(job, key):
                    setattr(job, key, value)
            
            job.last_update = time.time()
            
            # Add log entry for significant updates
            if ('status' in updates or 'current_step' in updates or 
                updates.get('progress', old_progress) != old_progress):
                
                message = updates.get('message', f"Updated to {job.status}")
                self._add_log_entry(job_id, message, "INFO")
            
            # Log progress changes
            if 'progress' in updates and updates['progress'] != old_progress:
                logger.debug(f"Job {job_id} progress: {old_progress}% -> {updates['progress']}%")
            
            return True
    
    def mark_item_completed(self, job_id: str, item_name: str, success: bool = True) -> bool:
        """Mark a specific item as completed or failed"""
        with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            
            if success:
                if item_name not in job.items_completed:
                    job.items_completed.append(item_name)
                    if item_name in job.items_failed:
                        job.items_failed.remove(item_name)
                    self._add_log_entry(job_id, f"Completed: {item_name}", "SUCCESS")
            else:
                if item_name not in job.items_failed:
                    job.items_failed.append(item_name)
                    if item_name in job.items_completed:
                        job.items_completed.remove(item_name)
                    self._add_log_entry(job_id, f"Failed: {item_name}", "ERROR")
            
            # Update processed count
            job.processed_items = len(job.items_completed) + len(job.items_failed)
            job.last_update = time.time()
            
            return True
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            if job.status in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']]:
                job.status = JOB_STATUS['CANCELLED']
                job.last_update = time.time()
                
                self._add_log_entry(job_id, "Job cancelled by user", "WARNING")
                self.job_stats['cancelled'] += 1
                
                logger.info(f"Job {job_id} cancelled")
                return True
            
            return False
    
    def complete_job(self, job_id: str, result: Dict = None, error: str = None):
        """Mark job as completed or failed"""
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Attempted to complete non-existent job: {job_id}")
                return
            
            job = self.jobs[job_id]
            
            if error:
                job.status = JOB_STATUS['FAILED']
                job.error = error
                job.progress = 100  # Failed jobs are 100% "complete"
                self._add_log_entry(job_id, f"Job failed: {error}", "ERROR")
                self.job_stats['failed'] += 1
            else:
                job.status = JOB_STATUS['COMPLETED']
                job.result = result or {}
                job.progress = 100
                self._add_log_entry(job_id, "Job completed successfully", "SUCCESS")
                self.job_stats['completed'] += 1
            
            job.last_update = time.time()
            logger.info(f"Job {job_id} completed with status: {job.status}")
    
    def _add_log_entry(self, job_id: str, message: str, level: str = "INFO"):
        """Add entry to job's detailed log"""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'progress': job.progress,
                'status': job.status
            }
            job.detailed_log.append(entry)
            
            # Keep log size manageable
            if len(job.detailed_log) > 100:
                job.detailed_log = job.detailed_log[-50:]
    
    def _cleanup_old_jobs(self):
        """Clean up old completed or failed jobs"""
        with self.lock:
            current_time = time.time()
            jobs_to_remove = []
            
            for job_id, job in self.jobs.items():
                job_age = current_time - job.start_time
                idle_time = current_time - job.last_update
                
                # Remove very old jobs (2+ hours)
                if job_age > 7200:
                    jobs_to_remove.append(job_id)
                
                # Remove completed/failed jobs older than 30 minutes
                elif (job.status in [JOB_STATUS['COMPLETED'], JOB_STATUS['FAILED'], JOB_STATUS['CANCELLED']] 
                      and idle_time > 1800):
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                self.job_stats['cleaned_up'] += 1
            
            if jobs_to_remove:
                logger.debug(f"Cleaned up {len(jobs_to_remove)} old jobs")
    
    def _check_stalled_jobs(self):
        """Check for and handle stalled jobs"""
        with self.lock:
            current_time = time.time()
            
            for job_id, job in self.jobs.items():
                idle_time = current_time - job.last_update
                total_time = current_time - job.start_time
                
                # Mark stalled jobs as failed
                if (job.status in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']] and
                    idle_time > 600):  # 10 minutes without update
                    
                    logger.warning(f"Job {job_id} appears stalled (idle: {idle_time:.0f}s)")
                    job.status = JOB_STATUS['FAILED']
                    job.error = f'Job stalled - no updates for {idle_time:.0f} seconds'
                    job.last_update = current_time
                    self._add_log_entry(job_id, "Job marked as stalled", "ERROR")
                    self.job_stats['stalled'] += 1
                
                # Mark timed out jobs as failed
                elif (job.status in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']] and
                      total_time > MAX_JOB_RUNTIME):
                    
                    logger.error(f"Job {job_id} timed out after {total_time:.0f}s")
                    job.status = JOB_STATUS['FAILED']  
                    job.error = f'Job timed out after {MAX_JOB_RUNTIME} seconds'
                    job.last_update = current_time
                    self._add_log_entry(job_id, "Job timed out", "ERROR")
                    self.job_stats['timed_out'] += 1
    
    def get_active_jobs_count(self) -> int:
        """Get count of active jobs"""
        with self.lock:
            return sum(1 for job in self.jobs.values() 
                      if job.status in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']])
    
    def get_jobs_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all jobs"""
        with self.lock:
            summary = {
                'total_jobs': len(self.jobs),
                'active_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'cancelled_jobs': 0,
                'statistics': dict(self.job_stats),
                'recent_jobs': []
            }
            
            # Count by status
            for job in self.jobs.values():
                if job.status in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']]:
                    summary['active_jobs'] += 1
                elif job.status == JOB_STATUS['COMPLETED']:
                    summary['completed_jobs'] += 1
                elif job.status == JOB_STATUS['FAILED']:
                    summary['failed_jobs'] += 1
                elif job.status == JOB_STATUS['CANCELLED']:
                    summary['cancelled_jobs'] += 1
            
            # Add recent jobs (last 10)
            recent_jobs = sorted(
                self.jobs.values(),
                key=lambda x: x.last_update,
                reverse=True
            )[:10]
            
            summary['recent_jobs'] = [
                {
                    'id': job.id,
                    'status': job.status,
                    'progress': job.progress,
                    'scenario_name': job.scenario_name,
                    'elapsed_seconds': time.time() - job.start_time
                }
                for job in recent_jobs
            ]
            
            return summary
    
    def get_job_logs(self, job_id: str, limit: int = 50) -> List[Dict]:
        """Get detailed logs for a specific job"""
        with self.lock:
            if job_id not in self.jobs:
                return []
            
            logs = self.jobs[job_id].detailed_log
            return logs[-limit:] if len(logs) > limit else logs
    
    def shutdown(self):
        """Graceful shutdown of job manager"""
        self.cleanup_running = False
        logger.info("Job manager shutdown initiated")

class ForecastJobManager(JobManager):
    """
    Specialized job manager for forecast operations
    """
    
    def create_forecast_job(self, job_id: str, scenario_name: str, 
                           total_sectors: int, **kwargs) -> JobInfo:
        """Create a forecast-specific job"""
        return self.create_job(
            job_id=job_id,
            job_type="forecast",
            scenario_name=scenario_name,
            total_items=total_sectors,
            current_step="Initializing forecast...",
            **kwargs
        )
    
    def update_sector_progress(self, job_id: str, sector_name: str, 
                             sector_index: int, total_sectors: int, 
                             message: str = None):
        """Update progress for sector processing"""
        progress = int(15 + ((sector_index / total_sectors) * 70))  # 15-85% range
        
        return self.update_job(job_id,
            current_step=sector_name,
            processed_items=sector_index,
            progress=progress,
            message=message or f'Processing {sector_name} ({sector_index+1}/{total_sectors})'
        )