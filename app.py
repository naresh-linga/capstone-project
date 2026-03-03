import cv2
import time
import threading
import mysql.connector
import numpy as np
import smtplib
import base64
from flask import Flask, render_template, Response, jsonify, request, session, redirect, url_for
from ultralytics import YOLO
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

app = Flask(__name__)
app.secret_key = 'accident_ai_secure_2025'

# ==================== CONFIGURATION ====================
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "nareshlinga864@gmail.com",
    "sender_password": "gzlm ggsu usvn qduk", 
    "receiver_email": "99220040907@klu.ac.in"
}
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Naresh@2003",
    "database": "accident_ai"
}
MODEL_PATH = 'best.pt'
ACCIDENT_LABEL = 'accident'
CONFIDENCE_THRESHOLD = 0.40
ALERT_COOLDOWN = 60

# ==================== GLOBAL STATE ====================
state = {
    "camera_active": False,
    "model": None,
    "last_alert_time": 0
}

# ==================== DATABASE SETUP (AUTO-FIX) ====================
def init_db():
    print("⚙️ Initializing Database System...")
    try:
        # 1. Create Database if missing
        conn = mysql.connector.connect(host=DB_CONFIG["host"], user=DB_CONFIG["user"], password=DB_CONFIG["password"])
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.close()

        # 2. Connect to Database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 3. Create Tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME,
                source VARCHAR(50),
                label VARCHAR(100),
                confidence FLOAT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE,
                password VARCHAR(255)
            )
        """)
        
        # 4. Create Admin User
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password) VALUES ('admin', 'admin123')")
            conn.commit()
            print("👤 Admin user created.")

        # 5. SELF-HEALING: Check if 'source' column exists
        try:
            cursor.execute("SELECT source FROM detections LIMIT 1")
        except mysql.connector.Error:
            print("⚠️ 'source' column missing. Upgrading database schema...")
            cursor.execute("ALTER TABLE detections ADD COLUMN source VARCHAR(50) DEFAULT 'webcam'")
            conn.commit()
            print("✅ Database upgraded successfully.")
            
        conn.close()
        
        # 6. Load Model
        print(f"🔄 Loading {MODEL_PATH}...")
        try:
            state["model"] = YOLO(MODEL_PATH)
            print("✅ Model Loaded.")
        except Exception as e:
            print(f"⚠️ Model Load Failed: {e}")
            
    except Exception as e:
        print(f"❌ Init Error: {e}")

# Run initialization
init_db()

# ==================== ROUTES ====================

@app.route('/')
def index():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                session['logged_in'] = True
                session['username'] = user['username']
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error="Invalid Credentials")
        except Exception as e:
            return render_template('login.html', error="Database Connection Failed")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    state["camera_active"] = False
    return redirect(url_for('login'))

# ==================== PAGE ROUTES ====================
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/monitor')
def monitor():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('monitor.html')

@app.route('/analytics')
def analytics():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('analytics.html')

@app.route('/about')
def about():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('about.html')

# ==================== API ROUTES ====================

@app.route('/api/stats')
def get_stats():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # 1. Total Count
        cursor.execute("SELECT COUNT(*) as total FROM detections")
        total = cursor.fetchone()['total']
        
        # 2. Accident Count
        cursor.execute(f"SELECT COUNT(*) as accidents FROM detections WHERE label='{ACCIDENT_LABEL}'")
        accidents = cursor.fetchone()['accidents']
        
        # 3. Recent Logs
        cursor.execute("SELECT timestamp, label, confidence, source FROM detections ORDER BY id DESC LIMIT 8")
        logs = cursor.fetchall()
        
        conn.close()
        return jsonify({"total": total, "accidents": accidents, "logs": logs})
    except Exception as e:
        print(f"Error getting stats: {e}")
        return jsonify({"total": 0, "accidents": 0, "logs": []})

@app.route('/api/camera/<action>')
def control_camera(action):
    state["camera_active"] = (action == 'start')
    return jsonify({"status": "active" if state["camera_active"] else "stopped"})

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ==================== PHOTO ANALYSIS ====================
@app.route('/api/analyze_image', methods=['POST'])
def analyze_image():
    if 'file' not in request.files: return jsonify({"error": "No file uploaded"})
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "No file selected"})
    
    try:
        img_bytes = file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        detected_objects = []
        max_conf = 0
        is_accident = False

        if state["model"]:
            results = state["model"].predict(img, conf=CONFIDENCE_THRESHOLD)
            
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0]) * 100
                    cls_id = int(box.cls[0])
                    label = state["model"].names[cls_id]
                    
                    detected_objects.append({"label": label, "conf": conf})
                    
                    if conf > max_conf: max_conf = conf
                    if label.lower() == ACCIDENT_LABEL.lower():
                        is_accident = True
                    
                    color = (0, 0, 255) if label.lower() == ACCIDENT_LABEL.lower() else (0, 255, 0)
                    cv2.rectangle(img, (x1, y1), (x2, y2), color, 4)
                    cv2.putText(img, f"{label} {conf:.1f}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
            # --- LOG TO DATABASE ---
            if detected_objects:
                label_to_log = ACCIDENT_LABEL if is_accident else detected_objects[0]['label']
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO detections (timestamp, source, label, confidence) VALUES (%s, %s, %s, %s)",
                        (datetime.now(), "upload", label_to_log, max_conf)
                    )
                    conn.commit()
                    conn.close()
                    print(f"✅ Photo Logged: {label_to_log}")
                except Exception as e:
                    print(f"❌ DB Log Error: {e}")
                    
            # --- TRIGGER AUTONOMOUS EMAIL FOR PHOTO UPLOAD ---
            if is_accident:
                print(f"🚨 Accident detected in photo! Triggering email... {max_conf:.2f}%")
                threading.Thread(target=send_email_thread, args=(img, max_conf, "Photo Upload Analysis")).start()

            _, buffer = cv2.imencode('.jpg', img)
            img_str = base64.b64encode(buffer).decode('utf-8')
            
            return jsonify({
                "image": f"data:image/jpeg;base64,{img_str}",
                "detections": detected_objects
            })
        else:
            return jsonify({"error": "Model not loaded"})
    except Exception as e:
        return jsonify({"error": str(e)})

# ==================== HELPERS ====================
def send_email_thread(frame, confidence, source="Live Camera"):
    try:
        # Use 'related' to allow inline embedded images
        msg = MIMEMultipart('related')
        msg['Subject'] = f"🚨 URGENT: Accident Detected Alert ({confidence:.1f}%)"
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['receiver_email']

        # Create alternative part for HTML
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        # Modern Real-time HTML Email Template
        html = f"""
        <html>
          <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
              
              <div style="background-color: #e74c3c; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 26px; font-weight: bold;">🚨 ACCIDENT DETECTED</h2>
              </div>
              
              <div style="padding: 25px;">
                <p style="font-size: 16px; color: #444; line-height: 1.5;">
                  Immediate attention is required. An accident has been autonomously detected by the AI monitoring system.
                </p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #f8f9fa; border-radius: 8px; overflow: hidden;">
                  <tr>
                    <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-weight: bold; color: #333; width: 40%;">Detection Source</td>
                    <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; color: #555;">{source}</td>
                  </tr>
                  <tr>
                    <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; font-weight: bold; color: #333;">AI Confidence Score</td>
                    <td style="padding: 12px 15px; border-bottom: 1px solid #e9ecef; color: #e74c3c; font-weight: bold;">{confidence:.2f}%</td>
                  </tr>
                  <tr>
                    <td style="padding: 12px 15px; font-weight: bold; color: #333;">Time of Detection</td>
                    <td style="padding: 12px 15px; color: #555;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                  </tr>
                </table>

                <div style="text-align: center; margin-top: 25px;">
                  <span style="display: inline-block; background-color: #333; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px;">Visual Evidence</span><br>
                  <img src="cid:accident_image" alt="Accident Snapshot" style="max-width: 100%; height: auto; border-radius: 8px; border: 2px solid #e9ecef;">
                </div>
              </div>
              
              <div style="background-color: #2c3e50; padding: 15px; text-align: center;">
                <p style="margin: 0; font-size: 12px; color: #bdc3c7;">Automated Real-time Alert &bull; Accident AI Detection System</p>
              </div>

            </div>
          </body>
        </html>
        """
        
        msg_alternative.attach(MIMEText(html, 'html'))

        # Attach Image for inline viewing
        _, encoded = cv2.imencode('.jpg', frame)
        img = MIMEImage(encoded.tobytes())
        img.add_header('Content-ID', '<accident_image>')
        img.add_header('Content-Disposition', 'inline', filename='snapshot.jpg')
        msg.attach(img)

        # Send Email
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.sendmail(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['receiver_email'], msg.as_string())
        
        print(f"📧 Real-time Email Alert Sent Successfully for {source}")
    except Exception as e:
        print(f"❌ Email Error: {e}")

def log_detection(label, confidence):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO detections (timestamp, source, label, confidence) VALUES (%s, %s, %s, %s)",
                       (datetime.now(), "webcam", label, confidence))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ DB Error: {e}")

def generate_frames():
    cap = cv2.VideoCapture(0)
    while True:
        if not state["camera_active"]:
            blank = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank, "SYSTEM STANDBY", (180, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (100,100,100), 2)
            _, buffer = cv2.imencode('.jpg', blank)
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.5)
            continue

        success, frame = cap.read()
        if not success: break

        if state["model"]:
            results = state["model"].predict(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
            annotated_frame = frame.copy()
            detected = False
            max_conf = 0

            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0]) * 100
                    cls_id = int(box.cls[0])
                    label = state["model"].names[cls_id]

                    color = (0, 0, 255) if label.lower() == ACCIDENT_LABEL.lower() else (0, 255, 0)
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, f"{label} {conf:.1f}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    if label.lower() == ACCIDENT_LABEL.lower():
                        detected = True
                        max_conf = conf

            if detected:
                if time.time() - state["last_alert_time"] > ALERT_COOLDOWN:
                    state["last_alert_time"] = time.time()
                    print(f"🚨 Accident! {max_conf:.2f}%")
                    threading.Thread(target=log_detection, args=(ACCIDENT_LABEL, max_conf)).start()
                    # Updated to pass "Live Camera Feed" to clearly distinguish source
                    threading.Thread(target=send_email_thread, args=(annotated_frame, max_conf, "Live Camera Feed")).start()
            
            frame = annotated_frame

        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
