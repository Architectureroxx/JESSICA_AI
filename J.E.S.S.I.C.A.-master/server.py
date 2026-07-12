import os
import sys
import time
import threading
import psutil
import re
import urllib.parse
import webbrowser
import ctypes
import subprocess
import sqlite3
import ollama
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn
from yt_dlp import YoutubeDL

# --- EXTENSION INJECTIONS ---
import sounddevice as sd
import scipy.io.wavfile as wav
import acoustid
import mss
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import requests
import pygetwindow as gw
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="J.E.S.S.I.C.A. Web Matrix Core", version="9.0.0")

# ALLOW VERCEL FRONTEND TO TALK TO YOUR LOCAL LAPTOP BACKEND
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permits Vercel deployment routing calls
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandPayload(BaseModel):
    command: str

SYSTEM_ALERTS_QUEUE = []
LOCAL_KNOWLEDGE_BASE = {
    "project notes": "Jessica Project Matrix v8.6.0 fully functional local routing layers.",
    "schedule": "System configuration checks optimized for Monday plant care routine alignment.",
    "clearance rules": "Blue mode grants master access."
}

DB_FILE = "jessica_memory.db"

def initialize_database_pool():
    conn = sqlite3.connect(DB_FILE)
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
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
        conn.commit()
        conn.close()
    except Exception as e: 
        print(f"[-] Database write slip: {e}")

def pull_recent_db_chat_history(limit=8):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM chat_history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        history = []
        for row in rows[::-1]: 
            history.append({'role': row[0], 'content': row[1]})
        return history
    except Exception: 
        return []

def set_pc_master_volume(level: int):
    try:
        ctypes.windll.ole32.CoInitialize(None) 
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return True
    except Exception as e:
        print(f"[-] Volume hardware alignment fault: {e}")
        return False

def scrape_live_tech_headlines() -> str:
    try:
        url = "https://news.ycombinator.com/"
        req = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=4)
        soup = BeautifulSoup(req.text, 'html.parser')
        links = soup.find_all('span', class_='titleline')
        return " // ".join([el.get_text() for el in links[:3]])
    except Exception: return "Web downlink pipeline structural timeout."

def scrape_local_weather_kanpur() -> str:
    try: 
        return requests.get("https://wttr.in/Kanpur?format=%C+%t", timeout=4).text.strip()
    except Exception: 
        return "Atmospheric connection timed out."

VK_MEDIA_STOP = 0xB2; VK_MEDIA_PLAY_PAUSE = 0xB3; KEYEVENTF_KEYUP = 0x0002
GLOBAL_APP_REGISTRY = {
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "calculator": "calc", "notepad": "notepad", "chrome": "chrome", 
    "task manager": "taskmgr", "file explorer": "explorer"
}

def execute_hardware_media_stop():
    ctypes.windll.user32.keybd_event(VK_MEDIA_STOP, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_STOP, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)

def search_and_launch_windows_shortcut(app_name: str) -> bool:
    search_paths = [
        os.path.join(os.environ.get('PROGRAMDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
        os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs')
    ]
    clean_app_name = app_name.lower().replace(" ", "")
    for base_path in search_paths:
        if not os.path.exists(base_path): continue
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".lnk"):
                    clean_file_name = file.lower().replace(".lnk", "").replace(" ", "")
                    if clean_app_name in clean_file_name or clean_file_name in clean_app_name:
                        try: os.startfile(os.path.join(root, file)); return True
                        except Exception: pass
    return False

def record_and_identify_song(duration=10, sample_rate=44100) -> str:
    temp_filename = "jessica_audio_buffer.wav"
    try:
        recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=2, dtype='int16')
        sd.wait(); wav.write(temp_filename, sample_rate, recording)
        results = acoustid.match("8Xa4id9gaa", temp_filename)
        if os.path.exists(temp_filename): os.remove(temp_filename)
        for score, recording_id, title, artist in results:
            if title and artist: return f"Track Identified: '{title}' by {artist}."
        return "No tracking metadata located in the music database."
    except Exception as e:
        if os.path.exists(temp_filename): os.remove(temp_filename)
        return f"Acoustic subsystem error: {str(e)}"

def execute_live_screen_search():
    try:
        time.sleep(0.3)
        with mss.mss() as sct: sct.shot(output="jessica_screen_buffer.png")
        webbrowser.open("https://images.google.com/")
        return "Live screen capture compiled. Drag 'jessica_screen_buffer.png' into the browser window."
    except Exception as e: return f"Screen vision processing failure: {str(e)}"

def process_local_translation(text_payload: str) -> str:
    try:
        clean_text = re.sub(r'\b(jessica|translate|in|to|say|google|translation)\b', '', text_payload.lower()).strip()
        lang_map = {"hindi": "hi", "spanish": "es", "french": "fr", "german": "de", "punjabi": "pa"}
        target_code = "hi" 
        for lang_name, code in lang_map.items():
            if lang_name in text_payload.lower(): target_code = code; break
        return GoogleTranslator(source='auto', target=target_code).translate(clean_text)
    except Exception as e: return f"Translation matrix drop: {str(e)}"

def check_system_anomalies_loop():
    global SYSTEM_ALERTS_QUEUE
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 85.0: SYSTEM_ALERTS_QUEUE.append(f"Proactive Alert: Local processor load spiking at {cpu} percent.")
            time.sleep(15)
        except Exception: time.sleep(5)

threading.Thread(target=check_system_anomalies_loop, daemon=True).start()

@app.get("/jessica/proactive")
async def retrieve_proactive_alerts():
    global SYSTEM_ALERTS_QUEUE
    if SYSTEM_ALERTS_QUEUE: 
        return {"has_alert": True, "alert_text": SYSTEM_ALERTS_QUEUE.pop(0)}
    return {"has_alert": False, "alert_text": ""}

@app.post("/api/command")
def process_mainframe_transaction(payload: CommandPayload, x_clearance_mode: str = Header(None)):
    user_phrase = payload.command
    print(f"[Local Mainframe] Processing query: {user_phrase}")
    
    phrase_lower = user_phrase.lower().strip()

    if "weather" in phrase_lower:
        weather_data = scrape_local_weather_kanpur()
        return {"response": f"Kanpur weather summary parameters: {weather_data}."}

    if "youtube" in phrase_lower or "play" in phrase_lower:
        video_query = re.sub(r'\b(jessica|play|search|for|on|youtube|song|bgm|track|video)\b', '', phrase_lower).strip()
        if not video_query:
            video_query = "lofi music"
        
        def async_youtube_autoplay(query):
            try:
                ydl_opts = {
                    'quiet': True, 
                    'default_search': 'ytsearch1', 
                    'skip_download': True,
                    'noplaylist': True
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if 'entries' in info and len(info['entries']) > 0:
                        direct_url = info['entries'][0]['webpage_url']
                    else:
                        direct_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                webbrowser.open(direct_url)
            except Exception:
                webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")

        threading.Thread(target=async_youtube_autoplay, args=(video_query,), daemon=True).start()
        return {"response": f"Initializing direct video playback pipeline for {video_query} instantly."}

    local_context = ""
    for key, ctx in LOCAL_KNOWLEDGE_BASE.items():
        if key in user_phrase.lower():
            local_context = f"\n[Context]: {ctx}"
    
    # SYSTEM INITIALIZATION MATRIX UPDATED FOR PERSONA DESIGNATION
    system_instruction = (
        "You are J.E.S.S.I.C.A. (Just an Educated System Service In Computer Applications), an advanced predictive AI infrastructure core running entirely offline.\n"
        "Your sole architect, creator, and master is Architectureroxx, also known as Utkrisht Verma.\n\n"
        "Analyze the user request and append EXACTLY ONE of these tags at the very end of your reply:\n"
        "- [CREATE_FILE] (if user explicitly asks to make, create, write, or start a new text file)\n"
        "- [APPEND_FILE] (if user asks to add content to an existing file)\n"
        "- [SET_VOLUME] (if user asks to adjust PC volume to a specific percentage)\n"
        "- [MUTE_SYSTEM] (if user asks to mute the audio sound)\n"
        "- [CLEAR_WORKSPACE] (if user asks to clear the desktop or minimize clutter)\n"
        "- [SYSTEM_SLEEP] (if user asks to sleep or hibernate the computer)\n"
        "- [TECH_NEWS] (if user asks for tech headlines)\n"
        "- [SCREEN_SEARCH] (if user asks to run a screen analysis search)\n"
        "- [TRANSLATE_TEXT] (if user asks to translate parameters)\n"
        "- [DETECT_MUSIC] (if user asks to recognize music sounds)\n"
        "- [LAUNCH_APP] (if user asks to open local applications)\n"
        "- [STOP_MUSIC] (if user asks to pause media tracks)\n"
        "- [PLAY_SPOTIFY] (if user asks to search tracks on Spotify)\n"
        "- [SYSTEM_TELEMETRY] (if asking for diagnostics CPU or memory analytics)\n"
        "- [NONE] (for general conversations)\n\n"
        "Formatting for file interactions:\n"
        "If you select [CREATE_FILE] or [APPEND_FILE], you MUST include instructions for the file name and content at the end of the response using this exact string format: FILENAME=name.txt CONTENT=text data\n"
        "Keep your spoken response crisp, natural, slightly clinical, and under three sentences."
    )

    try:
        history_chain = pull_recent_db_chat_history(8)
        if not history_chain: 
            history_chain.append({'role': 'system', 'content': system_instruction})
        history_chain.append({'role': 'user', 'content': f"{user_phrase}{local_context}"})

        response = ollama.chat(model='llama3', messages=history_chain, options={'temperature': 0.2})
        generated_text = response['message']['content'].strip()
        print(f"[Ollama Raw Output]: {generated_text}")
        
        intent = "NONE"
        tag_match = re.search(r'\[([A-Z_]+)\]', generated_text)
        if tag_match: intent = tag_match.group(1)
        
        clean_speech = re.sub(r'\[.*?\]', '', generated_text)
        clean_speech = re.sub(r'FILENAME=\S+ CONTENT=.*', '', clean_speech).strip()
        
        log_transaction_to_db("user", f"{user_phrase}")
        log_transaction_to_db("assistant", generated_text)

        if intent == "SET_VOLUME":
            volume_digits = re.findall(r'\d+', user_phrase)
            target_pct = int(volume_digits[0]) if volume_digits else 50
            set_pc_master_volume(target_pct)
            clean_speech = f"Audio hardware channels calibrated. Master volume set to {target_pct} percent."
            
        elif intent == "MUTE_SYSTEM" or "mute" in phrase_lower or "silence" in phrase_lower:
            set_pc_master_volume(0)
            clean_speech = "System sound channels fully attenuated."

        elif "volume down" in phrase_lower or "decrease volume" in phrase_lower or "lower volume" in phrase_lower:
            set_pc_master_volume(30)
            clean_speech = "Audio hardware channels calibrated. Volume dropped to 30 percent."

        elif intent == "CREATE_FILE" or intent == "APPEND_FILE":
            fn_match = re.search(r'FILENAME=(\S+)', generated_text)
            ct_match = re.search(r'CONTENT=(.*)', generated_text)
            file_name = fn_match.group(1) if fn_match else "jessica_document.txt"
            content_data = ct_match.group(1) if ct_match else "Data transaction verified."
            if not file_name.endswith(".txt") and not "." in file_name: file_name += ".txt"
            
            if intent == "CREATE_FILE":
                with open(file_name, "w", encoding="utf-8") as f: f.write(content_data + "\n")
                clean_speech = f"File created: '{file_name}' with parameter field inputs data."
            else:
                with open(file_name, "a", encoding="utf-8") as f: f.write(content_data + "\n")
                clean_speech = f"Background file injection successful inside '{file_name}' tracking tracks."

        elif intent == "CLEAR_WORKSPACE":
            open_windows = gw.getAllWindows()
            for window in open_windows:
                if window.title and not window.isMinimized and "jessica" not in window.title.lower():
                    try: window.minimize()
                    except Exception: pass
            clean_speech = "Desktop application clutter compressed safely."
        elif intent == "SYSTEM_SLEEP":
            clean_speech = "System standby protocols initialized. Hibernating core frames."
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif intent == "TECH_NEWS":
            clean_speech = f"Isolating trending network databurst headlines: {scrape_live_tech_headlines()}."
        elif intent == "SCREEN_SEARCH":
            clean_speech = f"Vision loops confirmed. {execute_live_screen_search()}"
        elif intent == "TRANSLATE_TEXT":
            clean_speech = process_local_translation(user_phrase)
        elif intent == "DETECT_MUSIC":
            clean_speech = record_and_identify_song(duration=10)
        elif intent == "STOP_MUSIC":
            execute_hardware_media_stop(); clean_speech = "Global media track signals killed."
        elif intent == "LAUNCH_APP":
            target_app = re.sub(r'\b(jessica|open|launch|start|run|app|program|software)\b', '', user_phrase.lower()).strip()
            launched = False
            if target_app in GLOBAL_APP_REGISTRY:
                try: subprocess.Popen(GLOBAL_APP_REGISTRY[target_app], shell=True); launched = True
                except Exception: pass
            if not launched: launched = search_and_launch_windows_shortcut(target_app)
            if launched: clean_speech = f"Initializing {target_app} binary tracks smoothly."
            else: clean_speech = f"Unable to isolate active executable routes for {target_app}."
        elif intent == "PLAY_SPOTIFY":
            track_query = re.sub(r'\b(jessica|play|spotify|on|song|music|track|artist)\b', '', user_phrase.lower()).strip()
            webbrowser.open(f"spotify:search:{urllib.parse.quote(track_query)}")
            clean_speech = f"Opening Spotify framework for {track_query} search metrics."
        elif intent == "SYSTEM_TELEMETRY":
            cpu = psutil.cpu_percent(); ram = psutil.virtual_memory().percent
            clean_speech = f"Mainframe analytics compiled. CPU workload is at {cpu} percent, memory allocation is at {ram} percent."

        return {"response": clean_speech}

    except Exception as e:
        print(f"[-] Ollama Framework Core Fault: {e}")
        return {"response": "Mainframe processing exception caught."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)