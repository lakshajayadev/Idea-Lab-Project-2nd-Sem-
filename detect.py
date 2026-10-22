import streamlit as st
import serial
import time
import requests
from PIL import Image
import os

# --- CONFIGURATION ---
SERIAL_PORT = 'COM7'  
BAUD_RATE = 115200

# --- THINGSPEAK CONFIGURATION ---
THINGSPEAK_WRITE_KEY = "EYKIPQR2Q6F1C451"

def update_thingspeak(severity):
    try:
        url = f"https://api.thingspeak.com/update?api_key={THINGSPEAK_WRITE_KEY}&field1={severity}"
        response = requests.get(url)
        if response.status_code == 200 and response.text != "0":
            return True, "Success"
        return False, f"ThingSpeak Error: {response.text}"
    except Exception as e:
        return False, str(e)

def mock_send_twilio_sms(severity):
    time.sleep(1) 
    payload = {
        "to": "Emergency Services",
        "from": "+1855MOCKSMS",
        "body": f"ALERT: High impact detected! Severity: {severity}/10. Visual confirmation: Person detected via YOLOv8.",
        "status": "delivered",
    }
    return payload

@st.cache_resource
def init_serial():
    try:
        return serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    except Exception as e:
        return None

@st.cache_resource
def load_yolo_model():
    from ultralytics import YOLO
    return YOLO('yolov8n.pt')

ser = init_serial()
model = load_yolo_model()

st.set_page_config(page_title="Impact Alert System", layout="wide")
st.title("🚨 Smart Impact Detection System")
st.markdown("---")

if 'triggered' not in st.session_state:
    st.session_state['triggered'] = False
if 'severity' not in st.session_state:
    st.session_state['severity'] = 0

if ser is not None and not st.session_state['triggered']:
    if ser.in_waiting > 0:
        lines = ser.readlines() 
        for raw_line in lines:
            line = raw_line.decode('utf-8', errors='ignore').strip()
            if "IMPACT_DETECTED" in line:
                try:
                    st.session_state['severity'] = line.split(":")[1]
                    st.session_state['triggered'] = True
                except IndexError:
                    pass

col1, col2 = st.columns(2)

with col1:
    st.header("Step 1: Hardware Sensor")
    st.write("Listening to ESP32 (MPU6050)...")
    
    if ser is None:
        st.error(f"Could not connect to {SERIAL_PORT}.")
    else:
        st.success(f"Connected to ESP32 on {SERIAL_PORT}")

    if st.session_state['triggered']:
        st.error(f"⚠️ HIGH IMPACT DETECTED! Severity Score: {st.session_state['severity']}")
    else:
        st.info("System Idle. Actively monitoring for hardware trigger...")

with col2:
    st.header("Step 2 & 3: YOLOv8 Vision & Alerts")
    
    if st.session_state['triggered']:
        uploaded_file = st.file_uploader("Upload Scene Image", type=["jpg", "png", "jpeg"])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Scene Captured", use_container_width=True)
            
            if st.button("🔍 Run YOLOv8 Analysis"):
                with st.spinner("YOLOv8 is analyzing the image..."):
                    results = model(image)
                    detected_classes = results[0].boxes.cls.tolist()
                    res_plotted = results[0].plot()
                    st.image(res_plotted, caption="YOLOv8 Detection Results", use_container_width=True)
                    
                    if 0 in detected_classes:
                        st.warning("⚠️ AI Vision confirmed: PERSON DETECTED. Initiating emergency sequence...")
                        
                        # 1. ThingSpeak IoT Push
                        with st.spinner("Syncing data to ThingSpeak Cloud..."):
                            ts_success, ts_msg = update_thingspeak(st.session_state['severity'])
                            if ts_success:
                                st.success("✅ Severity score uploaded to ThingSpeak Dashboard!")
                            else:
                                st.error(f"❌ ThingSpeak Failed: {ts_msg}")

                        # 2. Twilio Mock Push
                        with st.spinner("Authenticating with Twilio REST API..."):
                            response = mock_send_twilio_sms(st.session_state['severity'])
                        st.success("✅ Emergency SMS dispatched.")
                        st.json(response)
                        
                        # 3. TRIGGER THE BACKGROUND SCRIPT
                        with open("alert_trigger.txt", "w") as f:
                            f.write(str(st.session_state['severity']))
                        
                    else:
                        st.success("✅ AI Vision: No person detected. False Alarm.")
                
        st.markdown("---")
        if st.button("🔄 Reset System"):
            st.session_state['triggered'] = False
            st.session_state['severity'] = 0
            if ser is not None:
                ser.reset_input_buffer()
            st.rerun()
    else:
        st.write("Awaiting Step 1 trigger before activating vision system.")

if not st.session_state['triggered']:
    time.sleep(0.5)
    st.rerun()