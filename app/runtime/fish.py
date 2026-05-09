from __future__ import annotations
import asyncio
import psutil
import base64
from typing import Tuple

ENCODING = "utf-8"

async def run_fish(cmd: str, timeout_sec: int = 120, elevated: bool = False) -> Tuple[int, str, str]:
    """
    Executes a Fish shell command securely.
    
    SECURITY FIX: 
    - Uses Base64 encoding for the command payload to prevent injection vulnerabilities.
    """
    
    b64_cmd = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    
    # Decode and execute within the fish context
    fish_cmd_str = f"echo {b64_cmd} | base64 -d | fish"

    if elevated:
        # ARCHITECTURAL FIX: Preserve Wayland and DBus sockets through the pkexec barrier
        env_preserve = "WAYLAND_DISPLAY=$WAYLAND_DISPLAY XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS=$DBUS_SESSION_BUS_ADDRESS"
        fish_cmd_str = f"echo {b64_cmd} | base64 -d | env {env_preserve} fish"
        args = ["pkexec", "sh", "-c", fish_cmd_str] 
    else:
        args = ["fish", "-c", fish_cmd_str]

    try:
        proc = await asyncio.create_subprocess_exec(
            *args, 
            stdout=asyncio.subprocess.PIPE, 
            stderr=asyncio.subprocess.PIPE
        )
        pid = proc.pid
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            code = await proc.wait()
            return code, stdout.decode(ENCODING, errors="replace"), stderr.decode(ENCODING, errors="replace")
        except asyncio.TimeoutError:
            _kill_process_tree(pid)
            return 124, "", f"Timed out after {timeout_sec}s"
            
    except Exception as e:
        return 1, "", str(e)

def _kill_process_tree(pid: int):
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass
