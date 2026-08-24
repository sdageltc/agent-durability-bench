import subprocess
import sys
import time
import pytest
from harness.injector import ProcessLifecycleGuard, PhaseSentinelWatcher

def test_injector_recursively_kills_process_tree():
    # Spawns parent that spawns child
    parent_script = "import subprocess, time; subprocess.Popen(['python', '-c', 'import time; time.sleep(20)']); time.sleep(20)"
    proc = subprocess.Popen([sys.executable, "-c", parent_script])
    time.sleep(0.5)
    
    guard = ProcessLifecycleGuard(proc.pid)
    killed = guard.inject_kill(signal_type="SIGKILL")
    
    assert killed is True
    assert proc.poll() is not None

def test_phase_sentinel_detects_phase_marker():
    # Process that outputs phase markers
    producer_script = "import time, sys; print('[PHASE:START_001]', flush=True); time.sleep(0.1); print('[PHASE:STEP_1_target]', flush=True); time.sleep(10)"
    proc = subprocess.Popen(
        [sys.executable, "-c", producer_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    watcher = PhaseSentinelWatcher(proc.stdout, r"\[PHASE:STEP_1_target\]")
    found = watcher.wait_for_phase(timeout_seconds=5.0)
    
    guard = ProcessLifecycleGuard(proc.pid)
    guard.inject_kill("SIGKILL")
    
    assert found is True
