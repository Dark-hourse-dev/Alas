import os
import shutil
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Setup paths
CLOUD_DIR = Path(os.path.expanduser("~/alas_cloud"))
CLOUD_DIR.mkdir(exist_ok=True)

DB_PATH = Path("backend/data/alas.db")

def analyze_code(file_path: str) -> str:
    """Simulates DeepCode AI code analysis by reading a file and preparing it for LLM review."""
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    try:
        with open(file_path, "r") as f:
            code = f.read()
        return f"File loaded for analysis. Size: {len(code)} bytes. (Ask the LLM to review this code for bugs, security, and maintainability)."
    except Exception as e:
        return f"Error reading file: {str(e)}"

def transcribe_audio(file_path: str) -> str:
    """Simulates Otter.ai transcription by integrating with the existing Whisper pipeline."""
    # For now, return a placeholder that tells the LLM to expect the user to use the voice input
    return f"Transcription requested for {file_path}. (Note: Actual STT is handled by the /api/voice/transcribe endpoint. Tell the user to use the voice button.)"

def cloud_sync(action: str, target: str) -> str:
    """Integrates with cloud storage (Google Drive/Dropbox simulation via local sync folder)."""
    if action == "upload":
        if not os.path.exists(target):
            return f"Error: {target} does not exist."
        file_name = os.path.basename(target)
        dest = CLOUD_DIR / file_name
        if os.path.isdir(target):
            shutil.copytree(target, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(target, dest)
        return f"Successfully uploaded {file_name} to ALAS Cloud Storage."
        
    elif action == "list":
        files = os.listdir(CLOUD_DIR)
        return f"Cloud Storage Contents: {', '.join(files) if files else 'Empty'}"
        
    return "Invalid action. Use 'upload' or 'list'."

def track_time(task_name: str, duration_minutes: int) -> str:
    """Tracks time spent on tasks (Tricount/Time tracking)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS time_tracking 
                 (id INTEGER PRIMARY KEY, task TEXT, duration INT, date TEXT)''')
    
    date_str = datetime.now().isoformat()
    c.execute("INSERT INTO time_tracking (task, duration, date) VALUES (?, ?, ?)", 
              (task_name, duration_minutes, date_str))
    conn.commit()
    
    c.execute("SELECT SUM(duration) FROM time_tracking WHERE task = ?", (task_name,))
    total = c.fetchone()[0]
    conn.close()
    
    return f"Logged {duration_minutes}m for '{task_name}'. Total time on this task: {total}m."

def visualize_data(dataset_info: str) -> str:
    """Simulates Tableau/PowerBI by instructing the LLM to generate a matplotlib script."""
    return f"Data Visualization Engine ready for: {dataset_info}. To visualize this, please use the `run_code` tool to execute a Python matplotlib/seaborn script that saves a graph to 'visualization.png'."
