"""
Job Scheduler module using APScheduler for scheduling scraping, matching,
auto-apply, report generation, and notification jobs.
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

# Configure logging
logger = logging.getLogger(__name__)


class JobScheduler:
    """
    JobScheduler manages scheduling of background jobs using APScheduler.
    
    Supports:
    - Daily, weekly, custom interval scheduling
    - Job persistence to database
    - Pause/resume/remove jobs
    - Run jobs immediately
    - Lifecycle management (start/shutdown)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the JobScheduler.
        
        Args:
            db_path: Path to SQLite database for job persistence.
                     If None, jobs are stored in memory (not persisted).
        """
        self.db_path = db_path
        self.scheduler = None
        self._running = False
        self._lock = threading.Lock()
        self._job_store = {}  # In-memory store for job definitions
        
        # Setup job store
        if db_path:
            from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
            jobstores = {
                'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')
            }
        else:
            jobstores = {}
        
        # Create scheduler with job stores
        self.scheduler = BackgroundScheduler(jobstores=jobstores)
        
        # Add event listeners for logging
        self.scheduler.add_listener(self._job_event_listener, 
                                   EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        
        logger.info(f"JobScheduler initialized with db_path={db_path}")
    
    def _job_event_listener(self, event):
        """Listener for job execution events."""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} executed successfully")
    
    def add_job(self, func: Callable, trigger: Union[str, Dict], name: str,
                args: Optional[List] = None, kwargs: Optional[Dict] = None,
                job_id: Optional[str] = None,
                replace_existing: bool = False) -> str:
        """
        Add a new scheduled job.
        
        Args:
            func: The function to execute
            trigger: Trigger specification - can be:
                - 'daily': Run daily at midnight
                - 'weekly': Run weekly on Monday at midnight
                - 'interval': Dict with 'seconds', 'minutes', 'hours', 'days'
                - Cron expression: Dict with 'year', 'month', 'day', 'hour', 'minute'
                - Cron string: e.g., '0 0 * * *' for daily at midnight
            name: Human-readable job name
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            job_id: Optional custom job ID (auto-generated if not provided)
            replace_existing: If True, replace existing job with same ID
            
        Returns:
            str: The job ID
        """
        with self._lock:
            if not self._running:
                logger.warning("Scheduler not running. Job will be added but not executed until start() is called.")
            
            # Generate job ID if not provided
            if job_id is None:
                job_id = f"job_{uuid4().hex[:8]}"
            
            # Parse trigger
            aps_trigger = self._parse_trigger(trigger)
            
            # Prepare args and kwargs
            args = args or []
            kwargs = kwargs or {}
            
            # Store job definition for persistence
            job_def = {
                'id': job_id,
                'name': name,
                'trigger': trigger,
                'args': args,
                'kwargs': kwargs,
                'created_at': datetime.now().isoformat(),
                'next_run_time': None
            }
            self._job_store[job_id] = job_def
            
            try:
                # Add job to scheduler
                if replace_existing:
                    # Remove existing job if it exists
                    try:
                        self.scheduler.remove_job(job_id)
                    except JobLookupError:
                        pass
                
                job = self.scheduler.add_job(
                    func,
                    trigger=aps_trigger,
                    id=job_id,
                    name=name,
                    args=args,
                    kwargs=kwargs,
                    replace_existing=replace_existing
                )
                
                # Update next run time
                job_def['next_run_time'] = job.next_run_time.isoformat() if job.next_run_time else None
                
                logger.info(f"Added job '{name}' (ID: {job_id}) with trigger: {trigger}")
                return job_id
                
            except Exception as e:
                logger.error(f"Failed to add job '{name}': {e}")
                raise
    
    def _parse_trigger(self, trigger: Union[str, Dict]) -> Union[CronTrigger, IntervalTrigger]:
        """Parse trigger specification into APScheduler trigger object."""
        if isinstance(trigger, str):
            # Handle string triggers
            if trigger == 'daily':
                return CronTrigger(hour=0, minute=0)
            elif trigger == 'weekly':
                return CronTrigger(day_of_week='mon', hour=0, minute=0)
            else:
                # Try parsing as cron expression
                return CronTrigger.from_crontab(trigger)
        
        elif isinstance(trigger, dict):
            # Check if it's an interval trigger
            if any(k in trigger for k in ['seconds', 'minutes', 'hours', 'days']):
                return IntervalTrigger(
                    seconds=trigger.get('seconds', 0),
                    minutes=trigger.get('minutes', 0),
                    hours=trigger.get('hours', 0),
                    days=trigger.get('days', 0)
                )
            # Otherwise, treat as cron trigger
            else:
                return CronTrigger(**trigger)
        
        else:
            raise ValueError(f"Unsupported trigger type: {type(trigger)}")
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a scheduled job.
        
        Args:
            job_id: ID of the job to remove
            
        Returns:
            bool: True if job was removed, False if not found
        """
        with self._lock:
            try:
                self.scheduler.remove_job(job_id)
                if job_id in self._job_store:
                    del self._job_store[job_id]
                logger.info(f"Removed job {job_id}")
                return True
            except JobLookupError:
                logger.warning(f"Job {job_id} not found for removal")
                return False
            except Exception as e:
                logger.error(f"Failed to remove job {job_id}: {e}")
                return False
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        Get list of all scheduled jobs.
        
        Returns:
            List of job dictionaries with details
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'pending': job.pending
            }
            # Add stored definition if available
            if job.id in self._job_store:
                job_info['definition'] = self._job_store[job.id]
            jobs.append(job_info)
        return jobs
    
    def pause_job(self, job_id: str) -> bool:
        """
        Pause a scheduled job.
        
        Args:
            job_id: ID of the job to pause
            
        Returns:
            bool: True if job was paused, False if not found
        """
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job {job_id}")
            return True
        except JobLookupError:
            logger.warning(f"Job {job_id} not found for pause")
            return False
        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job.
        
        Args:
            job_id: ID of the job to resume
            
        Returns:
            bool: True if job was resumed, False if not found
        """
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job {job_id}")
            return True
        except JobLookupError:
            logger.warning(f"Job {job_id} not found for resume")
            return False
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False
    
    def run_now(self, job_id: str) -> bool:
        """
        Run a scheduled job immediately.
        
        Args:
            job_id: ID of the job to run
            
        Returns:
            bool: True if job was triggered, False if not found
        """
        try:
            self.scheduler.modify_job(job_id, next_run_time=datetime.now())
            logger.info(f"Triggered immediate run for job {job_id}")
            return True
        except JobLookupError:
            logger.warning(f"Job {job_id} not found for immediate run")
            return False
        except Exception as e:
            logger.error(f"Failed to run job {job_id} immediately: {e}")
            return False
    
    def start(self) -> None:
        """Start the scheduler."""
        with self._lock:
            if self._running:
                logger.warning("Scheduler already running")
                return
            
            try:
                self.scheduler.start()
                self._running = True
                logger.info("JobScheduler started")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {e}")
                raise
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the scheduler.
        
        Args:
            wait: Wait for running jobs to complete before shutting down
        """
        with self._lock:
            if not self._running:
                logger.warning("Scheduler not running")
                return
            
            try:
                self.scheduler.shutdown(wait=wait)
                self._running = False
                logger.info("JobScheduler shut down")
            except Exception as e:
                logger.error(f"Failed to shutdown scheduler: {e}")
                raise
    
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running and self.scheduler.running
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get details of a specific job.
        
        Args:
            job_id: ID of the job
            
        Returns:
            Job details or None if not found
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job_info = {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'pending': job.pending
            }
            if job.id in self._job_store:
                job_info['definition'] = self._job_store[job.id]
            return job_info
        return None
    
    def get_job_definitions(self) -> Dict[str, Any]:
        """Get all job definitions stored (including metadata)."""
        return self._job_store.copy()
    
    def restore_jobs(self) -> None:
        """Restore jobs from the job store (useful for recovery)."""
        with self._lock:
            if not self._running:
                logger.warning("Cannot restore jobs: scheduler not running")
                return
            
            restored_count = 0
            for job_id, job_def in self._job_store.items():
                try:
                    # Check if job already exists
                    if self.scheduler.get_job(job_id):
                        continue
                    
                    # Recreate the job
                    # Note: This would need the original function reference
                    # For simplicity, we store just the metadata
                    logger.info(f"Restoring job definition for {job_id}: {job_def.get('name')}")
                    restored_count += 1
                except Exception as e:
                    logger.error(f"Failed to restore job {job_id}: {e}")
            
            logger.info(f"Restored {restored_count} job definitions")


# Convenience functions for common job types
def schedule_scraping_job(scheduler: JobScheduler, 
                         func: Callable,
                         interval_type: str = 'daily',
                         **kwargs) -> str:
    """
    Schedule a scraping job.
    
    Args:
        scheduler: JobScheduler instance
        func: The scraping function
        interval_type: 'daily' or 'weekly'
        **kwargs: Additional arguments for add_job
        
    Returns:
        str: Job ID
    """
    trigger_map = {
        'daily': 'daily',
        'weekly': 'weekly'
    }
    trigger = trigger_map.get(interval_type, 'daily')
    
    return scheduler.add_job(
        func=func,
        trigger=trigger,
        name=f"Scraping job ({interval_type})",
        **kwargs
    )


def schedule_matching_job(scheduler: JobScheduler,
                         func: Callable,
                         interval_minutes: int = 30,
                         **kwargs) -> str:
    """
    Schedule a matching job.
    
    Args:
        scheduler: JobScheduler instance
        func: The matching function
        interval_minutes: Run every N minutes
        **kwargs: Additional arguments for add_job
        
    Returns:
        str: Job ID
    """
    return scheduler.add_job(
        func=func,
        trigger={'minutes': interval_minutes},
        name=f"Matching job (every {interval_minutes}min)",
        **kwargs
    )


def schedule_auto_apply_job(scheduler: JobScheduler,
                           func: Callable,
                           interval_minutes: int = 60,
                           **kwargs) -> str:
    """
    Schedule an auto-apply job.
    
    Args:
        scheduler: JobScheduler instance
        func: The auto-apply function
        interval_minutes: Run every N minutes
        **kwargs: Additional arguments for add_job
        
    Returns:
        str: Job ID
    """
    return scheduler.add_job(
        func=func,
        trigger={'minutes': interval_minutes},
        name=f"Auto-apply job (every {interval_minutes}min)",
        **kwargs
    )


def schedule_report_job(scheduler: JobScheduler,
                       func: Callable,
                       cron_expression: str = '0 0 * * 0',
                       **kwargs) -> str:
    """
    Schedule a report generation job.
    
    Args:
        scheduler: JobScheduler instance
        func: The report generation function
        cron_expression: Cron expression (default: weekly on Sunday at midnight)
        **kwargs: Additional arguments for add_job
        
    Returns:
        str: Job ID
    """
    return scheduler.add_job(
        func=func,
        trigger=cron_expression,
        name="Report generation job",
        **kwargs
    )


def schedule_notification_job(scheduler: JobScheduler,
                             func: Callable,
                             interval_hours: int = 24,
                             **kwargs) -> str:
    """
    Schedule a notification job.
    
    Args:
        scheduler: JobScheduler instance
        func: The notification function
        interval_hours: Run every N hours
        **kwargs: Additional arguments for add_job
        
    Returns:
        str: Job ID
    """
    return scheduler.add_job(
        func=func,
        trigger={'hours': interval_hours},
        name=f"Notification job (every {interval_hours}h)",
        **kwargs
    )


# Background runner for standalone execution
def run_background_runner(scheduler: JobScheduler, 
                          duration_hours: Optional[int] = None):
    """
    Run the scheduler in background with periodic health checks.
    
    Args:
        scheduler: JobScheduler instance
        duration_hours: Optional duration to run (in hours), None for indefinite
    """
    def health_check():
        while scheduler.is_running():
            time.sleep(60)  # Check every minute
            jobs = scheduler.get_jobs()
            logger.debug(f"Health check: {len(jobs)} jobs scheduled")
    
    # Start the scheduler
    scheduler.start()
    logger.info("Background runner started")
    
    # Run health check thread
    health_thread = threading.Thread(target=health_check, daemon=True)
    health_thread.start()
    
    if duration_hours:
        try:
            time.sleep(duration_hours * 3600)
            scheduler.shutdown()
            logger.info(f"Background runner stopped after {duration_hours} hours")
        except KeyboardInterrupt:
            scheduler.shutdown()
            logger.info("Background runner stopped by keyboard interrupt")
    else:
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.shutdown()
            logger.info("Background runner stopped by keyboard interrupt")


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.INFO)
    
    def example_job(name):
        print(f"[Example] Executing job: {name} at {datetime.now()}")
        return True
    
    # Create scheduler with persistence
    scheduler = JobScheduler(db_path="scheduler_jobs.db")
    
    # Add some example jobs
    job1 = scheduler.add_job(
        func=example_job,
        trigger="daily",
        name="Daily scraping",
        args=["Daily scraper"]
    )
    
    job2 = scheduler.add_job(
        func=example_job,
        trigger={"minutes": 30},
        name="Every 30 min matching",
        args=["Matcher"]
    )
    
    # Start scheduler
    scheduler.start()
    
    print("Scheduler started. Jobs:")
    for job in scheduler.get_jobs():
        print(f"  {job['id']}: {job['name']} - next run: {job['next_run_time']}")
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Scheduler shut down")
