import requests
import time
import os

print("📡 Background Notifier is running...")
print("Waiting for YOLOv8 to confirm an emergency...")

while True:
    # Check if the dashboard created the trigger file
    if os.path.exists("alert_trigger.txt"):
        try:
            # Read the severity score
            with open("alert_trigger.txt", "r") as f:
                severity = f.read().strip()
            
            if severity:
                print(f"🚨 Detected confirmed emergency (Severity: {severity})! Sending to phone...")
                
                # Send the notification via ntfy app
                message = f"EMERGENCY: Impact Severity {severity}/10 detected! Person verified in danger zone."
                response = requests.post("https://ntfy.sh/Shine_Impact_Alert", data=message)
                
                if response.status_code == 200:
                    print("✅ Ping sent successfully to your phone!")
                else:
                    print(f"❌ Failed to send. Server responded with: {response.status_code}")
                
            # Delete the file so it doesn't trigger over and over
            os.remove("alert_trigger.txt")
            
        except Exception as e:
            print(f"❌ Error processing alert: {e}")
            
    # Sleep for 1 second before checking again so we don't overload the laptop
    time.sleep(1)