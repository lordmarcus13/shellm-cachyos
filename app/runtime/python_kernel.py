from __future__ import annotations
import asyncio
import sys
import os
import tempfile
from typing import Tuple

# Standardizing I/O to UTF-8
ENCODING = "utf-8"

async def run_python(code: str, timeout_sec: int = 120) -> Tuple[int, str, str]:
    """
    Executes a Python script securely via a temporary file.
    
    Args:
        code (str): The Python code to execute.
        timeout_sec (int): Execution timeout in seconds.
        
    Returns:
        Tuple[int, str, str]: (exit_code, stdout, stderr)
    """
    
    # Create a temporary file to hold the script
    # We use delete=False to close it before execution, then delete manually
    fd, path = tempfile.mkstemp(suffix=".py", text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Construct command: python -u <script_path>
        # -u: Unbuffered binary stdout/stderr
        cmd = [sys.executable, "-u", path]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            code = await proc.wait()
            
            stdout = stdout_bytes.decode(ENCODING, errors="replace")
            stderr = stderr_bytes.decode(ENCODING, errors="replace")
            
            return code, stdout, stderr
            
        except asyncio.TimeoutError:
            proc.kill()
            return 124, "", f"Timed out after {timeout_sec}s"
            
    except Exception as e:
        return 1, "", f"Execution Error: {str(e)}"
        
    finally:
        # Cleanup
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
