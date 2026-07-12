import cv2
import numpy as np
import os

if not os.path.exists("profile"):
    os.makedirs("profile")

# Load existing training maps if they exist to append to them cleanly
model_path = "profile/biometric_model.yml"
cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# 1. Collect Security Clearance Credentials
print("=== JARVIS MULTI-USER ENROLLMENT CORE ===")
try:
    user_id = int(input("[?] Enter a unique numerical ID for this operator (e.g., 2, 3, 4): "))
    user_name = input("[?] Enter the Operator's Name: ").strip()
except ValueError:
    print("[!] Invalid ID array format. Must be an integer number.")
    exit()

# Append the new user mapping token to a local registry database file
registry_path = "profile/user_registry.txt"
with open(registry_path, "a", encoding="utf-8") as f:
    f.write(f"{user_id}:{user_name}\n")

print(f"\n[*] Calibrating camera array for {user_name}. Look straight at the lens...")
video_capture = cv2.VideoCapture(0)

faces_data = []
labels = []
captured_count = 0

while captured_count < 40: # Takes 40 data points across different facial angles
    ret, frame = video_capture.read()
    if not ret: continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5)
    
    for (x, y, w, h) in faces:
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (200, 200))
        
        faces_data.append(face_roi)
        labels.append(user_id) # Ties this face array sequence to the specified User ID
        captured_count += 1
        
        # Overlay visual target frames on screen
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 150), 2)
        cv2.putText(frame, f"EVALUATING: {captured_count}/40", (x, y-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 150), 2)
        
    cv2.imshow("Multi-User Biometric Calibration Array", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

video_capture.release()
cv2.destroyAllWindows()

if len(faces_data) > 0:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    # If a previous model file exists, we merge old and new matrices together
    if os.path.exists(model_path):
        print("[*] Merging profile arrays with current database clusters...")
        # LBPH allows incremental updates using the update() call!
        recognizer.read(model_path)
        recognizer.update(faces_data, np.array(labels))
    else:
        recognizer.train(faces_data, np.array(labels))
        
    recognizer.save(model_path)
    print(f"\n[SUCCESS] Profile generated! {user_name} is registered under ID: {user_id}.")
else:
    print("[ERROR] Optical matrix dropped focus. No face data logged.")