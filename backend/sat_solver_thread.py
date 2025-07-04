import threading
import time
import copy
import logging
from typing import Optional, Dict, Any
from dataclasses import replace
from computations import sat_search, Session, SATSchedule

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SATSolverThread:
    """
    Background thread that continuously runs SAT solver to optimize the cooking schedule.
    Updates the session's SATSchedule with improved solutions.
    """
    
    def __init__(self):
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.interrupt_event = threading.Event()
        self.session_lock = threading.Lock()
        self.current_session: Optional[Session] = None
        self.stats = {
            'runs': 0,
            'successful_updates': 0,
            'interruptions': 0,
            'errors': 0,
            'total_time': 0.0,
            'last_run_time': 0.0
        }
    
    def start(self, session: Session):
        """Start the SAT solver thread with the given session."""
        if self.thread and self.thread.is_alive():
            logger.warning("SAT solver thread is already running")
            return
        
        self.current_session = copy.deepcopy(session)
        self.stop_event.clear()
        self.interrupt_event.clear()
        
        self.thread = threading.Thread(target=self._run_sat_solver, daemon=True)
        self.thread.start()
        logger.info("SAT solver thread started")
    
    def stop(self):
        """Stop the SAT solver thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5.0)
            if self.thread.is_alive():
                logger.warning("SAT solver thread did not stop gracefully")
        logger.info("SAT solver thread stopped")
    
    def interrupt_and_restart(self, new_session: Session):
        """
        Interrupt the current SAT solver run and restart with updated session.
        Called when a chef finishes a task and the session state changes.
        """
        logger.info("Interrupting SAT solver for session update")
        self.interrupt_event.set()
        self.stats['interruptions'] += 1
        
        # Wait a bit for the interruption to take effect
        time.sleep(0.1)
        
        # Update session and clear interruption flag
        with self.session_lock:
            self.current_session = copy.deepcopy(new_session)
        self.interrupt_event.clear()
        logger.info("SAT solver restarted with updated session")
    
    def update_session(self, new_session: Session):
        """Update the session without interrupting the current SAT run."""
        with self.session_lock:
            self.current_session = copy.deepcopy(new_session)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics about the SAT solver thread."""
        return self.stats.copy()
    
    def _run_sat_solver(self):
        """Main loop for the SAT solver thread."""
        logger.info("SAT solver thread main loop started")
        
        while not self.stop_event.is_set():
            try:
                start_time = time.time()
                
                # Get current session state
                with self.session_lock:
                    if self.current_session is None:
                        time.sleep(1.0)
                        continue
                    session = copy.deepcopy(self.current_session)
                
                # Check if we should interrupt this run
                if self.interrupt_event.is_set():
                    logger.debug("SAT solver run interrupted")
                    time.sleep(0.1)
                    continue
                
                # Run SAT solver with interruption checking
                solution = self._run_sat_with_interruption(session)
                
                if solution and not self.interrupt_event.is_set():
                    # Create new SATSchedule from solution
                    chef_to_tasks: Dict[str, list] = {name: [] for name in session.chefs_data.keys()}
                    
                    # solution is a list of (chef, start_time, task_index)
                    for chef, start_time, task_index in solution:
                        chef_to_tasks[chef].append((start_time, task_index))
                    
                    # For each chef, sort by planned start time and keep only instruction indices
                    chef_to_tasks_ordered: Dict[str, list] = {
                        chef: [task_index for start_time, task_index in sorted(tasks)]
                        for chef, tasks in chef_to_tasks.items()
                    }
                    
                    new_sat_schedule = SATSchedule(chef_to_tasks_ordered)
                    
                    # Update the session with new SAT schedule
                    with self.session_lock:
                        if self.current_session is not None:
                            self.current_session = replace(
                                self.current_session, 
                                sat_schedule=new_sat_schedule
                            )
                    
                    self.stats['successful_updates'] += 1
                    logger.info("SAT solver updated schedule successfully")
                
                # Update statistics
                run_time = time.time() - start_time
                self.stats['runs'] += 1
                self.stats['total_time'] += run_time
                self.stats['last_run_time'] = run_time
                
                logger.debug(f"SAT solver run completed in {run_time:.2f}s")
                
                # Small delay before next run
                time.sleep(0.1)
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error in SAT solver thread: {e}")
                time.sleep(1.0)  # Wait before retrying
    
    def _run_sat_with_interruption(self, session: Session):
        """
        Run SAT solver with periodic interruption checks.
        Returns the solution or None if interrupted.
        """
        try:
            # Use the interruption-aware version of sat_search
            solution = sat_search(
                session, 
                now=0, 
                timeout=30,  # 30 second timeout
                interruption_check=lambda: self.interrupt_event.is_set()
            )
            
            # Check for interruption after the call
            if self.interrupt_event.is_set():
                return None
            
            return solution
            
        except Exception as e:
            logger.error(f"Error in SAT search: {e}")
            return None
    
    def get_current_session(self) -> Optional[Session]:
        """Get a copy of the current session state."""
        with self.session_lock:
            return copy.deepcopy(self.current_session) if self.current_session else None 