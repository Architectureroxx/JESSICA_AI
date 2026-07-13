import os
import sys
import time
import threading
import psutil
import re
import urllib.parse
import webbrowser
import ctypes
import sqlite3
import ollama
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import requests

app = FastAPI(title="J.E.S.S.I.C.A. Local Network Core Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandPayload(BaseModel):
    command: str

live_metrics = {"cpu": 0.0, "ram": 0.0}
DB_FILE = "jessica_memory.db"

def initialize_database_pool():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT,
                        content TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

initialize_database_pool()

def log_transaction_to_db(role: str, content: str):
    def async_db_worker():
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
            conn.commit()
            conn.close()
        except Exception: pass
    threading.Thread(target=async_db_worker, daemon=True).start()

def pull_recent_db_chat_history(limit=4):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [{'role': row[0], 'content': row[1]} for row in rows[::-1]]
    except Exception: return []

def set_pc_master_volume(level: int):
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        ctypes.windll.ole32.CoInitialize(None) 
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
    except Exception: pass

def scrape_local_weather_kanpur():
    try: return requests.get("https://wttr.in/Kanpur?format=%C+%t", timeout=3).text.strip()
    except Exception: return "Offline Matrix."

def telemetry_metrics_worker():
    global live_metrics
    while True:
        live_metrics["cpu"] = psutil.cpu_percent(interval=1)
        live_metrics["ram"] = psutil.virtual_memory().percent

threading.Thread(target=telemetry_metrics_worker, daemon=True).start()

@app.get("/")
def serve_mobile_dashboard():
    return FileResponse("index.html")

@app.get("/api/telemetry")
def get_telemetry():
    return live_metrics

@app.post("/api/command")
def process_command(payload: CommandPayload):
    phrase_lower = payload.command.lower().strip()

    if "weather" in phrase_lower:
        return {"response": f"Kanpur atmospheric reading parameters: {scrape_local_weather_kanpur()}."}

    elif "youtube" in phrase_lower or "play" in phrase_lower:
        video_query = re.sub(r'\b(jessica|play|search|for|on|youtube|song|video)\b', '', phrase_lower).strip()
        if not video_query: video_query = "lofi music"
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(video_query)}")
        return {"response": f"Executing direct video playback pipeline on your laptop for {video_query}."}

    elif "mute" in phrase_lower or "silence" in phrase_lower:
        set_pc_master_volume(0)
        return {"response": "System sound channels fully attenuated."}

    # Intelligence execution fallback via local Ollama
    system_instruction = "You are J.E.S.S.I.C.A., an advanced offline AI matrix core. Respond in 1-2 sentences."
    try:
        history = pull_recent_db_chat_history(4)
        full_context = [{'role': 'system', 'content': system_instruction}] + history + [{'role': 'user', 'content': payload.command}]
        response = ollama.chat(model='llama3.1', messages=full_context, options={'temperature': 0.1})
        generated_text = response['message']['content'].strip()
        log_transaction_to_db("user", payload.command)
        log_transaction_to_db("assistant", generated_text)
        return {"response": generated_text}
    except Exception:
        return {"response": "Local intelligence core processing fault checked."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
