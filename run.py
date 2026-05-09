from __future__ import annotations
import uvicorn
import platform
import os
from app.config import settings

def _boot_sequence():
    os_name = platform.system()
    print("=" * 60)
    print(" ⚡ sheLLm DYNAMIC ARCHITECTURE BOOT SEQUENCE ⚡ ")
    print("=" * 60)
    print(f"[SYSTEM] Detected OS: {os_name}")
    
    if os_name == "Windows":
        print("[WARNING] Legacy OS detected. SheLLm is optimized for CachyOS.")
    elif os_name == "Linux":
        print("[VECTOR] Primary Shell: Fish (Execution Enabled)")
        if os.system("which fish > /dev/null 2>&1") != 0:
            print("[WARNING] Fish shell not found in PATH! Execution may fail.")
    else:
        print(f"[WARNING] Unknown OS: {os_name}. Routing may be unstable.")
        
    print("[STATUS] OVERCLOCK MODE: ACTIVE")
    print(f"[NETWORK] Binding to {settings.app_host}:{settings.app_port}")
    print("=" * 60)

if __name__ == "__main__":
    _boot_sequence()
    uvicorn.run(
        "app.main:app", 
        host=settings.app_host, 
        port=settings.app_port, 
        reload=False, 
        access_log=settings.log_enable
    )