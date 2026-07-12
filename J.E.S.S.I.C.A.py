import os
import sys
import time
import math
import threading
import speech_recognition as sr
import pygame
from openai import OpenAI

# ====================================================================
# CONFIGURATION: Paste your OpenAI API key inside the quotes below
# ====================================================================
OPENAI_API_KEY = "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"
# ====================================================================

# Initialize OpenAI
try:
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-proj-YOUR_ACTUAL_OPENAI_KEY_HERE":
        raise ValueError("API key variable is empty or placeholder text.")
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print("\n[-] Error initializing OpenAI Client. Check your API Key.")
    sys.exit(1)

# Initialize Pygame Components
pygame.init()
WIDTH, HEIGHT = 500, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("J.A.R.V.I.S. - MARK III HUD")
clock = pygame.time.Clock()

# UI Shared Thread Variables
jarvis_status = "SYNCHRONIZING..."
jarvis_text_display = "Systems initializing, sir."
is_listening = False
rotation_angle = 0
pulse_radius = 0
pulse_direction = 1
running = True

def speak_text(text):
    """Speaks text using native Windows PowerShell execution layers."""
    global jarvis_status, jarvis_text_display
    jarvis_status = "SPEAKING..."
    jarvis_text_display = text
    
    safe_text = text.replace('"', '').replace("'", "").replace("\n", " ")
    powershell_command = (
        f'powershell -Command "Add-Type –AssemblyName System.Speech; '
        f'$sim = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
        f'$sim.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male); '
        f'$sim.Rate = 1; '
        f'$sim.Speak(\'{safe_text}\')"'
    )
    os.system(powershell_command)

def ai_voice_loop():
    """Background thread handler for the listening and processing steps."""
    global jarvis_status, jarvis_text_display, is_listening, running
    
    # Small buffer initialization delay
    time.sleep(2)
    speak_text("Systems operational, sir. OpenAI engine synchronization is complete.")
    
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False 
    recognizer.energy_threshold = 350 
    
    while running:
        jarvis_status = "AWAITING INSTRUCTION..."
        jarvis_text_display = "Listening channel active."
        is_listening = True
        
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            try:
                # Capture microphone input
                audio = recognizer.listen(source, timeout=4, phrase_time_limit=7)
                is_listening = False
                jarvis_status = "DECODING AUDIO..."
                jarvis_text_display = "Processing translation sequence..."
                
                user_prompt = recognizer.recognize_google(audio)
                jarvis_text_display = f'You: "{user_prompt}"'
                time.sleep(0.5)
                
                if any(word in user_prompt.lower() for word in ["exit", "shutdown", "quit", "goodbye"]):
                    speak_text("Powering down system modules. Goodbye, sir.")
                    running = False
                    pygame.quit()
                    sys.exit(0)
                
                # Request response from OpenAI Core
                jarvis_status = "QUERYING CORE ENGINE..."
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a witty, highly intelligent, and ultra-concise male AI assistant named JARVIS. "
                                "Provide brief, casual answers (1-2 sentences maximum). "
                                "Do not use markdown bolding, lists, asterisks, symbols, or bullet points."
                            )
                        },
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
                
                reply = response.choices[0].message.content.strip()
                speak_text(reply)
                
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                is_listening = False
                continue
            except Exception as e:
                is_listening = False
                print(f"Error: {e}")
                continue

# Spin up the background voice processor thread
voice_thread = threading.Thread(target=ai_voice_loop, daemon=True)
voice_thread.start()

# --- Core Pygame Interface Render Functions ---
def draw_arc_reactor(surface, cx, cy, radius, angle):
    """Draws a glowing geometric sci-fi vector ring inspired by the Mark III arc reactor core."""
    # Base Outer Cyan Glow Rings
    pygame.draw.circle(surface, (0, 70, 100), (cx, cy), radius + 8, 2)
    pygame.draw.circle(surface, (0, 180, 230), (cx, cy), radius, 3)
    pygame.draw.circle(surface, (0, 220, 255), (cx, cy), radius - 15, 1)
    
    # Render 10 mechanical triangular power segments along the radius wheel
    num_segments = 10
    for i in range(num_segments):
        seg_angle = math.radians(i * (360 / num_segments) + angle)
        
        # Calculate coordinate vectors for geometric lines
        x1 = cx + int((radius - 12) * math.cos(seg_angle))
        y1 = cy + int((radius - 12) * math.sin(seg_angle))
        x2 = cx + int((radius - 3) * math.cos(seg_angle - 0.15))
        y2 = cy + int((radius - 3) * math.sin(seg_angle - 0.15))
        x3 = cx + int((radius - 3) * math.cos(seg_angle + 0.15))
        y3 = cy + int((radius - 3) * math.sin(seg_angle + 0.15))
        
        # Draw the glowing power shards
        pygame.draw.polygon(surface, (0, 200, 250), [(x1, y1), (x2, y2), (x3, y3)], 0)
        pygame.draw.polygon(surface, (200, 245, 255), [(x1, y1), (x2, y2), (x3, y3)], 1)

    # Core Central Node Ring
    pygame.draw.circle(surface, (150, 240, 255), (cx, cy), 18, 0)
    pygame.draw.circle(surface, (255, 255, 255), (cx, cy), 12, 0)

def draw_listening_wave(surface, cx, cy, active):
    """Draws an animated breathing soundwave perimeter around the active interface."""
    global pulse_radius, pulse_direction
    if active:
        pulse_radius += 1 * pulse_direction
        if pulse_radius > 15 or pulse_radius < 0:
            pulse_direction *= -1
        
        # Pulsing soundwave tracking halos
        pygame.draw.circle(surface, (0, 255, 180), (cx, cy), 140 + pulse_radius, 1)
        pygame.draw.circle(surface, (0, 255, 180), (cx, cy), 155 - pulse_radius, 1)

def wrap_text(text, font, max_width):
    """Helper method to format text wrap boundaries so status paragraphs fit cleanly inside window bounds."""
    words = text.split(' ')
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if font.size(test_line)[0] < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines

# Setup UI Typography
font_title = pygame.font.SysFont("Courier New", 18, bold=True)
font_status = pygame.font.SysFont("Segoe UI", 13, bold=True)
font_body = pygame.font.SysFont("Segoe UI", 14)

# --- Main Pygame Render Loop ---
while running:
    screen.fill((5, 12, 20)) # Dark Blue/Grey Stark Background
    
    # Catch window exit clicks safely
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Progress rotational framework markers
    if jarvis_status == "SPEAKING...":
        rotation_angle += 4.5  # Spin faster when talking
    else:
        rotation_angle += 1.0  # Slow idle cruise speed
        
    # Draw Interface Elements
    CX, CY = WIDTH // 2, HEIGHT // 2 - 40
    draw_listening_wave(screen, CX, CY, is_listening)
    draw_arc_reactor(screen, CX, CY, 110, rotation_angle)
    
    # Lower Data Tray Panel Layout Border
    pygame.draw.rect(screen, (0, 50, 80), (15, 340, WIDTH - 30, 145), 1, border_radius=8)
    
    # Text Interface Updates
    text_headline = font_title.render("MARK III SYSTEM PROFILE", True, (0, 220, 255))
    screen.blit(text_headline, (30, 350))
    
    # Status Header Tracker Color Swaps
    status_color = (0, 255, 150) if "AWAITING" in jarvis_status or "SPEAKING" in jarvis_status else (255, 150, 0)
    text_status = font_status.render(f"STATUS: {jarvis_status}", True, status_color)
    screen.blit(text_status, (30, 375))
    
    # Clean Body Paragraph Rendering 
    wrapped_lines = wrap_text(jarvis_text_display, font_body, WIDTH - 70)
    y_offset = 400
    for line in wrapped_lines[:3]: # Keep to top 3 lines to fit the tray perfectly
        rendered_line = font_body.render(line, True, (200, 230, 245))
        screen.blit(rendered_line, (30, y_offset))
        y_offset += 20
        
    pygame.display.flip()
    clock.tick(60) # Locked frame lock index context

pygame.quit()