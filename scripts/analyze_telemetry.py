import json
import pandas as pd
from pathlib import Path
import sys

# PATHS
BASE_DIR = Path(__file__).parent.parent
LOG_FILE = BASE_DIR / "logs/universal.log.jsonl"
OUTPUT_FILE = BASE_DIR / "app/ui/static/telemetry.js"

def analyze():
    print(f"[FORGE] Analyzing {LOG_FILE}...")
    
    if not LOG_FILE.exists():
        print("[FORGE] Log file not found.")
        data = {"total_tasks": 0, "success_rate": 0, "tool_usage": {}}
    else:
        log_entries = []
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    log_entries.append(json.loads(line))
                except:
                    continue
        
        if not log_entries:
            print("[FORGE] Log file empty.")
            data = {"total_tasks": 0, "success_rate": 0, "tool_usage": {}}
        else:
            df = pd.DataFrame(log_entries)
            
            # 1. Total Tasks
            total_tasks = len(df)
            
            # 2. Success Rate
            def get_status(row):
                try:
                    return row.get("terminal_io_state", {}).get("final_status", "unknown")
                except:
                    return "error"
            
            df["status"] = df.apply(get_status, axis=1)
            success_count = len(df[df["status"] == "succeeded"])
            success_rate = round((success_count / total_tasks) * 100, 1) if total_tasks > 0 else 0
            
            data = {
                "total_tasks": total_tasks,
                "success_rate": success_rate,
                "success_count": success_count,
                "failed_count": total_tasks - success_count,
                "recent_tasks": df.tail(10).to_dict(orient="records")
            }
    
    print(f"[FORGE] Synthesis complete. Success Rate: {data['success_rate']}%")
    
    # OUTPUT as JS
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json_str = json.dumps(data, indent=2)
        f.write(f"window.TELEMETRY_DATA = {json_str};")
    print(f"[FORGE] Telemetry written to {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze()
