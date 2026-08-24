import psutil
import time
import re
from typing import Optional

class ProcessLifecycleGuard:
    def __init__(self, pid: int):
        self.pid = pid

    def inject_kill(self, signal_type: str = "SIGKILL") -> bool:
        try:
            parent = psutil.Process(self.pid)
            # 1. Terminate all child processes recursively
            try:
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        if signal_type == "SIGKILL":
                            child.kill()
                        else:
                            child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                    
            # 2. Terminate parent process
            try:
                if signal_type == "SIGKILL":
                    parent.kill()
                else:
                    parent.terminate()
                parent.wait(timeout=5)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
            return True
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            return False

class PhaseSentinelWatcher:
    """Watches process stdout stream until target lifecycle phase sentinel is detected."""
    def __init__(self, process_stdout, target_phase_regex: str):
        self.stdout = process_stdout
        self.pattern = re.compile(target_phase_regex)

    def wait_for_phase(self, timeout_seconds: float = 10.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            line = self.stdout.readline()
            if not line:
                time.sleep(0.01)
                continue
            if self.pattern.search(line):
                return True
        return False
