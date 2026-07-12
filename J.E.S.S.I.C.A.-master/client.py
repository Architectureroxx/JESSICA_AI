import os
import sys
import time
import math
import json
import re
import webbrowser
import ctypes
import subprocess
import sqlite3
import threading
import requests
import urllib.parse
import speech_recognition as sr
import pygame
import cv2
import numpy as np
import pyaudio         
import psutil
import mss
import pygetwindow as gw
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup

try:
    import ollama
except ImportError:
    print("[-] Missing library dependency. Please execute: pip install ollama")

boot_phase_progress = 0.0
audio_sync_lock = threading.Lock()

def play_procedural_boot_sound():
    global boot_phase_progress
    for step in range(101):
        with audio_sync_lock: 
            boot_phase_progress = step / 100.0
        time.sleep(0.002)

threading.Thread(target=play_procedural_boot_sound, daemon=True).start()

# --- Graphics Framework Initialization ---
pygame.init()
pygame.mixer.init() 
info_object = pygame.display.Info()
WIDTH, HEIGHT = info_object.current_w, info_object.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("J.E.S.S.I.C.A. Core Matrix Dashboard v8.5")
clock = pygame.time.Clock()

jarvis_status = "ENGINE ONLINE. FIRMWARE BOOTING..."
jarvis_text_display = "Calibrating monitor frame buffers..."
is_listening = True 
rotation_angle = 0
running = True
current_emoji_symbol = "[-]" 
is_booting = True

clearance_level = "lockdown"
HUD_COLOR = (255, 30, 30)

COLOR_BLUE = (0, 180, 230)
COLOR_YELLOW = (235, 185, 30)
COLOR_RED = (255, 30, 30)

user_name = "UNAUTHORIZED OPERATOR PROFILE"
face_scan_status = "Perimeter tracking scanning environment..."
live_telemetry_metrics = {"cpu": 0.0, "ram": 0.0, "disk": 0.0}

yellow_activated_flag = False
yellow_question_counter = 0
last_manual_override_time = 0.0

hud_input_string_buffer = ""
is_input_field_active = False

live_audio_amplitude = 0
audio_bar_heights = [2] * 12  
scrolling_ticker_text = "MAINFRAME DATABASE STORAGE ONLINE // FILE ACTUATION LOAD MATRIX ACTIVE // CLICK ENTRY PROMPT LINE TO TYPE DIRECTLY // "
ticker_x = WIDTH
current_video_frame = None
frame_lock = threading.Lock()

text_stream_queue = []
status_update_queue = []

DB_FILE = "jessica_memory.db"
LOCAL_KNOWLEDGE_BASE = {
    "project notes": "Jessica Project Matrix v8.6.0 fully functional local routing layers.",
    "schedule": "System configuration checks optimized for Monday plant care routine alignment.",
    "clearance rules": "Blue mode grants master access. Yellow mode locks terminal down after 5 inquiries."
}

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
    except Exception: 
        pass

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
        ctypes.CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return True
    except Exception:
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
    try: return requests.get("https://wttr.in/Kanpur?format=%C+%t", timeout=4).text.strip()
    except Exception: return "Atmospheric connection timed out."

GLOBAL_APP_REGISTRY = {
    "word": "winword", "excel": "excel", "powerpoint": "powerpnt",
    "calculator": "calc", "notepad": "notepad", "chrome": "chrome", 
    "task manager": "taskmgr", "file explorer": "explorer"
}

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

def speak_text(text, mood_icon="[-]"):
    global status_update_queue, text_stream_queue
    status_update_queue.append("SPEAKING...")
    
    voice_clean = re.sub(r'\[.*?\]', '', text).strip()
    voice_clean = voice_clean.replace('"', '').replace("'", "")
    
    if not voice_clean:
        return

    text_stream_queue.append(voice_clean)

    def async_speech_worker(phrase):
        vbs_path = "jessica_voice_temp.vbs"
        try:
            with open(vbs_path, "w", encoding="cp1252") as f:
                f.write(f'Set sapi = CreateObject("SAPI.SpVoice")\n')
                # FIXED: Configured index reference parameters to natively target the local system's female speech voice
                f.write(f'Set sapi.Voice = sapi.GetVoices.Item(1)\n')
                f.write(f'sapi.Rate = 1\n')
                f.write(f'sapi.Speak "{phrase}"\n')
            
            subprocess.run(["cscript.exe", "//Nologo", vbs_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(vbs_path):
                os.remove(vbs_path)
        except Exception:
            pass
        status_update_queue.append("SYSTEM INSTANTIATED")
        
    threading.Thread(target=async_speech_worker, args=(voice_clean,), daemon=True).start()

def run_ollama_inference_worker(user_phrase):
    global text_stream_queue, status_update_queue, running, yellow_activated_flag, yellow_question_counter, clearance_level, HUD_COLOR, user_name
    phrase_lower = user_phrase.lower().strip()

    if any(cmd in phrase_lower for cmd in ["shutdown", "exit", "close the window", "quit jessica"]):
        speak_text("Powering down console modules. Goodbye, Master Utkrisht.", "[OFF]")
        time.sleep(1.8)
        running = False
        pygame.quit()
        os._exit(0)

    elif "volume up" in phrase_lower or "increase volume" in phrase_lower or "louder" in phrase_lower:
        try: requests.post("http://127.0.0.1:5000/api/command", json={"command": user_phrase}, timeout=5)
        except Exception: pass
        speak_text("Audio hardware channels calibrated. Volume adjusted.", "[JESSICA]")
        return

    elif "volume down" in phrase_lower or "decrease volume" in phrase_lower or "lower volume" in phrase_lower:
        try: requests.post("http://127.0.0.1:5000/api/command", json={"command": user_phrase}, timeout=5)
        except Exception: pass
        speak_text("Audio hardware channels calibrated. Volume dropped.", "[JESSICA]")
        return

    elif "mute" in phrase_lower or "silence" in phrase_lower:
        try: requests.post("http://127.0.0.1:5000/api/command", json={"command": user_phrase}, timeout=5)
        except Exception: pass
        speak_text("System sound channels fully attenuated.", "[JESSICA]")
        return

    elif "youtube" in phrase_lower or "play" in phrase_lower:
        video_query = re.sub(r'\b(jessica|play|search|for|on|youtube|song|bgm|track|video)\b', '', phrase_lower).strip()
        if not video_query:
            video_query = "music"
        
        try:
            requests.post("http://127.0.0.1:5000/api/command", json={"command": user_phrase}, timeout=5)
        except Exception:
            webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(video_query)}")
        
        speak_text(f"Executing direct YouTube stream playback for {video_query} instantly.", "[JESSICA]")
        return

    elif "weather" in phrase_lower:
        speak_text("Accessing atmospheric sensory arrays.", "[JESSICA]")
        current_weather = scrape_local_weather_kanpur()
        speak_text(f"Current weather reporting: {current_weather}", "[JESSICA]")
        return

    elif "clear workspace" in phrase_lower or "minimize windows" in phrase_lower:
        open_windows = gw.getAllWindows()
        for window in open_windows:
            if window.title and not window.isMinimized and "jessica" not in window.title.lower():
                try: window.minimize()
                except Exception: pass
        speak_text("Desktop application clutter compressed safely.", "[JESSICA]")
        return

    local_context = ""
    for key, ctx in LOCAL_KNOWLEDGE_BASE.items():
        if key in phrase_lower:
            local_context = f"\n[Context]: {ctx}"
            
    system_instruction = (
        "You are J.E.S.S.I.C.A. (Just an Educated System Service In Computer Applications), an advanced predictive AI infrastructure core running entirely offline.\n"
        "Your sole owner and master is Architectureroxx, also known as Utkrisht Verma.\n\n"
        "Keep your response extremely crisp, natural, clinical, and under two short sentences."
    )

    try:
        history_chain = pull_recent_db_chat_history(8)
        if not history_chain: 
            history_chain.append({'role': 'system', 'content': system_instruction})
        history_chain.append({'role': 'user', 'content': f"{user_phrase}{local_context}"})

        response_stream = ollama.chat(model='llama3.1', messages=history_chain, options={'temperature': 0.1}, stream=True)
        
        full_response_text = ""
        current_sentence_buffer = ""
        
        for chunk in response_stream:
            token = chunk['message']['content']
            full_response_text += token
            current_sentence_buffer += token
            
            if any(punct in token for punct in ['.', '?', '!']):
                clean_clause = re.sub(r'\[.*?\]', '', current_sentence_buffer).strip()
                if clean_clause and len(clean_clause) > 2:
                    speak_text(clean_clause, "[JESSICA]")
                current_sentence_buffer = ""

        if current_sentence_buffer.strip():
            clean_clause = re.sub(r'\[.*?\]', '', current_sentence_buffer).strip()
            if clean_clause:
                speak_text(clean_clause, "[JESSICA]")

        log_transaction_to_db("user", f"{user_phrase}")
        log_transaction_to_db("assistant", full_response_text.strip())

    except Exception as e:
        print(f"[-] AI Generation Core Fault: {e}")
        status_update_queue.append("SYSTEM ERROR")
        text_stream_queue.append(f"Inference Initialization Error: {str(e)}. Attempting 'llama3.1' hook fallback...")
        speak_text("Mainframe link fault. Verify model tag strings.", "[ERR]")

def execute_direct_prompt_submission(user_phrase):
    global text_stream_queue, status_update_queue, yellow_activated_flag, yellow_question_counter, clearance_level, HUD_COLOR, user_name, last_manual_override_time
    if not user_phrase.strip(): return
    
    input_clean = user_phrase.lower().strip()
    
    if any(word in input_clean for word in ["deactivate yellow", "cancel session"]):
        yellow_activated_flag = False; clearance_level = "lockdown"; HUD_COLOR = COLOR_RED
        yellow_question_counter = 0; last_manual_override_time = 0.0; user_name = "TERMINAL LOCKOUT ENFORCED"
        speak_text("Deactivating proxy parameters.", "[ERR]")
        return
        
    if "activate yellow" in input_clean:
        clearance_level = "yellow"; HUD_COLOR = COLOR_YELLOW; yellow_activated_flag = True
        yellow_question_counter = 0; last_manual_override_time = time.time(); user_name = "VOCALLY VERIFIED PROXY SESSION"
        speak_text("Lockdown overridden. Yellow segment active.", "[AMBER]")
        return

    if clearance_level == "lockdown" and not yellow_activated_flag:
        speak_text("Request denied. Core authentication missing.", "[ERR]")
        return

    if clearance_level == "yellow" and yellow_activated_flag:
        if yellow_question_counter >= 5: 
            speak_text("Request denied. Proxy transaction limits reached.", "[ERR]")
            return
        yellow_question_counter += 1

    status_update_queue.append("ROUTING INTEGRITY STREAM...")
    text_stream_queue.append("Accessing offline intelligence matrices...")
    
    ai_thread = threading.Thread(target=run_ollama_inference_worker, args=(user_phrase,))
    ai_thread.daemon = True
    ai_thread.start()

def telemetry_metrics_worker():
    global live_telemetry_metrics, running
    while running:
        try:
            live_telemetry_metrics["cpu"] = psutil.cpu_percent(interval=1)
            live_telemetry_metrics["ram"] = psutil.virtual_memory().percent
        except Exception: 
            pass
        time.sleep(1)

threading.Thread(target=telemetry_metrics_worker, daemon=True).start()

def security_optical_scanner_worker():
    global user_name, face_scan_status, current_video_frame, clearance_level, HUD_COLOR, running, is_booting, last_manual_override_time, yellow_activated_flag
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    video_capture = cv2.VideoCapture(0, cv2.CAP_MSMF)
    HISTORY_SIZE = 45; detection_history = ["lockdown"] * HISTORY_SIZE; last_greeted_state = None

    while running:
        ret, frame = video_capture.read()
        if not ret: continue
        mirrored_frame = cv2.flip(frame, 1)
        gray_frame = cv2.cvtColor(mirrored_frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray_frame, 1.15, 6, minSize=(60, 60))
        
        if is_booting:
            scan_overlay = np.zeros((90, 120, 3), dtype=np.uint8)
            cv2.putText(scan_overlay, "CHARGING", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 180, 230), 1)
            with frame_lock: current_video_frame = scan_overlay
            time.sleep(0.04); continue

        if time.time() - last_manual_override_time < 15.0:
            display_frame = cv2.resize(mirrored_frame, (120, 90))
            with frame_lock: current_video_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            time.sleep(0.05); continue

        current_frame_state = "lockdown"
        if len(faces) > 0:
            for (x, y, w, h) in faces: 
                current_frame_state = "blue"
                cv2.rectangle(mirrored_frame, (x, y), (x+w, y+h), (0, 180, 230), 2)

        detection_history.pop(0); detection_history.append(current_frame_state)
        from collections import Counter
        consensus_state, frequency = Counter(detection_history).most_common(1)[0]

        if yellow_activated_flag: 
            clearance_level = "yellow"
            HUD_COLOR = COLOR_YELLOW
        else:
            if consensus_state == "blue" and frequency >= (HISTORY_SIZE * 0.40):
                clearance_level = "blue"
                HUD_COLOR = COLOR_BLUE
                user_name = "UTKRISHT VERMA [MASTER ACCESS]"
                face_scan_status = "LIVENESS TRACKING REVERIFIED // CORE SECURITY LAYER STABLE"
            else:
                clearance_level = "lockdown"
                HUD_COLOR = COLOR_RED
                user_name = "TERMINAL LOCKOUT ENFORCED // SAFE MODE ACTIVE"
                face_scan_status = "SAY 'ACTIVATE YELLOW' TO OVERRIDE SECURE LOCKDOWN MODE"

        display_frame = cv2.resize(mirrored_frame, (120, 90))
        with frame_lock: current_video_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        time.sleep(0.03)
    video_capture.release()

SHARED_AUDIO_BUFFER = []
BUFFER_LOCK = threading.Lock()

def audio_frequency_visualizer_worker():
    global live_audio_amplitude, audio_bar_heights, running, is_listening, is_booting, SHARED_AUDIO_BUFFER
    time.sleep(1.0)
    p = pyaudio.PyAudio()
    stream = None
    try:
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
    except Exception:
        pass

    while running:
        if is_listening and stream is not None and not is_booting:
            try:
                data_bytes = stream.read(1024, exception_on_overflow=False)
                data = np.frombuffer(data_bytes, dtype=np.int16)
                with BUFFER_LOCK:
                    SHARED_AUDIO_BUFFER.append(data_bytes)
                    if len(SHARED_AUDIO_BUFFER) > 30: 
                        SHARED_AUDIO_BUFFER.pop(0)
                data_float = data.astype(np.float32)
                if len(data_float) > 0 and np.mean(data_float**2) > 0:
                    live_audio_amplitude = min(int(np.sqrt(np.mean(data_float**2)) / 12), 60)
                    for i in range(len(audio_bar_heights)): 
                        target = np.random.randint(2, max(5, live_audio_amplitude))
                        audio_bar_heights[i] += (target - audio_bar_heights[i]) * 0.4
            except Exception: pass
        else:
            live_audio_amplitude = 0
            for i in range(len(audio_bar_heights)): audio_bar_heights[i] += (2 - audio_bar_heights[i]) * 0.2
        time.sleep(0.02)
    p.terminate()

def voice_client_processing_loop():
    global is_booting, running, SHARED_AUDIO_BUFFER, clearance_level, yellow_activated_flag
    while is_booting: time.sleep(0.1)
    recognizer = sr.Recognizer()
    
    recognizer.energy_threshold = 300  
    recognizer.pause_threshold = 0.5   
    
    while running:
        audio_data_captured = b""
        with BUFFER_LOCK:
            if len(SHARED_AUDIO_BUFFER) > 0: 
                audio_data_captured = b"".join(SHARED_AUDIO_BUFFER)
                SHARED_AUDIO_BUFFER.clear()
        
        if audio_data_captured:
            try:
                raw_speech_chunk = sr.AudioData(audio_data_captured, 16000, 2)
                phrase = recognizer.recognize_google(raw_speech_chunk, language="en-US").strip()
                if phrase:
                    print(f"[Speech Detected]: {phrase}")
                    if clearance_level == "lockdown" and not yellow_activated_flag and "activate yellow" not in phrase.lower():
                        continue
                    execute_direct_prompt_submission(phrase)
            except Exception: 
                pass
        time.sleep(0.1)

threading.Thread(target=security_optical_scanner_worker, daemon=True).start()
threading.Thread(target=audio_frequency_visualizer_worker, daemon=True).start()
threading.Thread(target=voice_client_processing_loop, daemon=True).start()

def wrap_text(text, font, max_width):
    words = text.split(' '); lines = []; current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if font.size(test_line)[0] < max_width: current_line = test_line
        else: lines.append(current_line); current_line = word
    if current_line: lines.append(current_line)
    return lines

font_title = pygame.font.SysFont("Courier New", 24, bold=True)
font_status = pygame.font.SysFont("Segoe UI", 16, bold=True)
font_body = pygame.font.SysFont("Segoe UI", 18)
font_vision = pygame.font.SysFont("Courier New", 14)
font_ticker = pygame.font.SysFont("Courier New", 15, bold=True)
font_widget = pygame.font.SysFont("Courier New", 14, bold=True)
font_input_text = pygame.font.SysFont("Courier New", 18, bold=True)

input_box_rect = pygame.Rect(40, HEIGHT - 230, WIDTH - 80, 42)

while running:
    with audio_sync_lock: current_progress = boot_phase_progress
    if is_booting and current_progress >= 0.99: 
        is_booting = False; clearance_level = "lockdown"; jarvis_status = "SYSTEM INSTANTIATED"
    
    if text_stream_queue:
        jarvis_text_display = text_stream_queue.pop(0)
    if status_update_queue:
        jarvis_status = status_update_queue.pop(0)

    screen.fill((4, 6, 12))
    mouse_pos = pygame.mouse.get_pos()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): 
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN and not is_booting:
            is_input_field_active = True if input_box_rect.collidepoint(mouse_pos) else False
        if event.type == pygame.KEYDOWN and not is_booting:
            if is_input_field_active:
                if event.key == pygame.K_RETURN:
                    submission_query = hud_input_string_buffer
                    hud_input_string_buffer = ""
                    if submission_query.strip():
                        execute_direct_prompt_submission(submission_query)
                elif event.key == pygame.K_BACKSPACE:
                    hud_input_string_buffer = hud_input_string_buffer[:-1]
                else:
                    if len(hud_input_string_buffer) < 95 and event.unicode:
                        hud_input_string_buffer += event.unicode

    if is_booting: rotation_angle += 15.0
    elif jarvis_status.startswith("SPEAKING"): rotation_angle += 4.5
    else: rotation_angle += 1.2
        
    CX, CY = WIDTH // 2, HEIGHT // 2 - 80
    if is_booting:
        HUD_COLOR = (int(current_progress * 130), int(current_progress * 220), int(current_progress * 255))
        laser_y = int(current_progress * HEIGHT)
        pygame.draw.line(screen, HUD_COLOR, (0, laser_y), (WIDTH, laser_y), 3)
        grid_space = int(40 + (current_progress * 45))
        for x_v in range(0, WIDTH, grid_space): pygame.draw.line(screen, (8, 22, 40), (x_v, 0), (x_v, HEIGHT), 1)
        for y_v in range(0, HEIGHT, grid_space): pygame.draw.line(screen, (8, 22, 40), (0, y_v), (WIDTH, y_v), 1)
        pygame.draw.circle(screen, HUD_COLOR, (CX, CY), int(current_progress * 280), 2)
        jarvis_status = f"COMPILING SYSTEM TURBINE IGNITION: {int(current_progress * 100)}%"

    if not is_booting: pygame.draw.circle(screen, HUD_COLOR, (CX, CY), 155 + int(live_audio_amplitude * 0.6), 1)
    pygame.draw.circle(screen, (int(HUD_COLOR[0]*0.2), int(HUD_COLOR[1]*0.2), int(HUD_COLOR[2]*0.2)), (CX, CY), 112, 2)
    pygame.draw.circle(screen, HUD_COLOR, (CX, CY), 100, 3)
    
    for i in range(12):
        seg_angle = math.radians(i * 30 + rotation_angle)
        pygame.draw.polygon(screen, HUD_COLOR, [(CX + int(82 * math.cos(seg_angle)), CY + int(82 * math.sin(seg_angle))), (CX + int(96 * math.cos(seg_angle - 0.1)), CY + int(96 * math.sin(seg_angle - 0.1))), (CX + int(96 * math.cos(seg_angle + 0.1)), CY + int(96 * math.sin(seg_angle + 0.1)))], 0)
    pygame.draw.circle(screen, (255, 255, 255), (CX, CY), 12, 0)

    cam_x, cam_y, cam_w, cam_h = WIDTH - 220, 60, 160, 120
    pygame.draw.rect(screen, (6, 14, 25), (cam_x, cam_y, cam_w, cam_h))
    with frame_lock:
        if current_video_frame is not None: 
            screen.blit(pygame.transform.scale(pygame.surfarray.make_surface(current_video_frame.swapaxes(0, 1)), (cam_w, cam_h)), (cam_x, cam_y))
    pygame.draw.rect(screen, HUD_COLOR, (cam_x - 2, cam_y - 2, cam_w + 4, cam_h + 4), 1)

    for idx, bar_h in enumerate(audio_bar_heights): 
        pygame.draw.rect(screen, HUD_COLOR, (60 + (idx * 11), 60 + (90 - int(bar_h * 1.5)), 6, int(bar_h * 1.5)))

    if not is_booting:
        tw_x, tw_y = WIDTH // 2 - 150, 20
        pygame.draw.rect(screen, (8, 14, 24), (tw_x, tw_y, 300, 45), border_radius=6)
        pygame.draw.rect(screen, HUD_COLOR, (tw_x, tw_y, 300, 45), 1, border_radius=6)
        screen.blit(font_widget.render(f"CPU: {live_telemetry_metrics['cpu']}%", True, HUD_COLOR), (tw_x + 25, tw_y + 14))
        screen.blit(font_widget.render(f"RAM: {live_telemetry_metrics['ram']}%", True, HUD_COLOR), (tw_x + 165, tw_y + 14))

    if not is_booting:
        border_thickness = 2 if is_input_field_active else 1
        field_bg_color = (12, 22, 38) if is_input_field_active else (6, 12, 22)
        pygame.draw.rect(screen, field_bg_color, input_box_rect, border_radius=6)
        pygame.draw.rect(screen, HUD_COLOR, input_box_rect, border_thickness, border_radius=6)
        if hud_input_string_buffer == "" and not is_input_field_active:
            placeholder_surface = font_input_text.render("Type something to know... [Hit Enter]", True, (75, 105, 135))
            screen.blit(placeholder_surface, (input_box_rect.x + 15, input_box_rect.y + 11))
        else:
            text_val_surface = font_input_text.render(hud_input_string_buffer + ("|" if (int(time.time() * 2) % 2 == 0 and is_input_field_active) else ""), True, (230, 245, 255))
            screen.blit(text_val_surface, (input_box_rect.x + 15, input_box_rect.y + 11))

    ticker_y = HEIGHT - 275
    ticker_surface = font_ticker.render(scrolling_ticker_text, True, HUD_COLOR)
    ticker_x -= 2.2
    if ticker_x < -ticker_surface.get_width(): ticker_x = WIDTH
    if not is_booting: screen.blit(ticker_surface, (int(ticker_x), ticker_y + 4))

    tray_y = HEIGHT - 180
    pygame.draw.rect(screen, HUD_COLOR, (40, tray_y, WIDTH - 80, 140), 1, border_radius=10)
    screen.blit(font_title.render(f"ACCESS LAYER: {clearance_level.upper()}", True, HUD_COLOR), (60, tray_y + 15))
    screen.blit(font_status.render(f"TARGET USER ID: {user_name}", True, HUD_COLOR), (60, tray_y + 45))
    screen.blit(font_vision.render(f"PERIMETER EXTRACTION: {face_scan_status}", True, HUD_COLOR), (60, tray_y + 70))
    
    wrapped_lines = wrap_text(jarvis_text_display, font_body, WIDTH - 140)
    y_offset = tray_y + 94
    for line in wrapped_lines[:2]: 
        screen.blit(font_body.render(line, True, (215, 235, 250)), (60, y_offset))
        y_offset += 20
        
    pygame.display.flip()
    clock.tick(60)
pygame.quit()