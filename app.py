from flask import Flask, jsonify, render_template
from twilio.rest import Client
from flask_cors import CORS
import requests
import threading
import time

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Twilio credentials
ACCOUNT_SID = ''
AUTH_TOKEN = ''
FROM_PHONE_NUMBER = '+13344234287'

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Predefined temperature thresholds for alert
LOW_TEMPERATURE_THRESHOLD = 37.0  # Temperature below this value triggers an alert
HIGH_TEMPERATURE_THRESHOLD = 41.0  # Temperature above this value triggers an alert

# ThingSpeak credentials
THINGSPEAK_API_KEY = '5JCQJ8673T4OVGD0'
THINGSPEAK_CHANNEL_ID = '2593821'

# Last known temperature and alert flags
last_known_temperature = None
alert_sent_low = False
alert_sent_high = False

# Recipient phone number (you can set this dynamically as needed)
RECIPIENT_PHONE_NUMBER = ['+919074812182', ] # Replace with the actual recipient number

def check_temperature_alert():
    global last_known_temperature, alert_sent_low, alert_sent_high
    while True:
        temperature = get_temperature()
        
        if temperature is not None:
            # Check if temperature is below the low threshold and alert flag is not set
            if temperature < LOW_TEMPERATURE_THRESHOLD and not alert_sent_low:
                send_alert_message(RECIPIENT_PHONE_NUMBER, temperature)
                alert_sent_low = True
                alert_sent_high = False  # Reset high alert flag
            # Check if temperature is above the high threshold and alert flag is not set
            elif temperature > HIGH_TEMPERATURE_THRESHOLD and not alert_sent_high:
                send_alert_message(RECIPIENT_PHONE_NUMBER, temperature)
                alert_sent_high = True
                alert_sent_low = False  # Reset low alert flag
            # Reset flags if temperature returns to normal range
            elif LOW_TEMPERATURE_THRESHOLD <= temperature <= HIGH_TEMPERATURE_THRESHOLD:
                alert_sent_low = False
                alert_sent_high = False
            
            # Update last known temperature
            last_known_temperature = temperature
        
        time.sleep(300)  # Check temperature every 5 minutes

def send_alert_message(recipient, temperature):
    try:
        message_body = f"Alert: Dog's temperature is {temperature}°C. Please check."
        
        message = client.messages.create(
            body=message_body,
            from_=FROM_PHONE_NUMBER,
            to=recipient
        )
        
        print(f"Message sent to {recipient}: {message.sid}")
        return True
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return False

def get_temperature():
    try:
        url = f'https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json?api_key={THINGSPEAK_API_KEY}&results=1'
        response = requests.get(url)
        data = response.json()
        
        if 'feeds' in data and data['feeds']:
            temperature = float(data['feeds'][0]['field1'])  
            return temperature
        else:
            return None
    except Exception as e:
        print(f"Error fetching temperature: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-temperature', methods=['GET'])
def get_temperature_route():
    temperature = get_temperature()
    
    if temperature is not None:
        if temperature < LOW_TEMPERATURE_THRESHOLD or temperature > HIGH_TEMPERATURE_THRESHOLD:
            # Send alert message if temperature is outside safe range
            if send_alert_message(RECIPIENT_PHONE_NUMBER, temperature):
                return jsonify({'temperature': temperature, 'alert': True})
            else:
                return jsonify({'error': 'Failed to send alert message', 'temperature': temperature, 'alert': True})
        else:
            return jsonify({'temperature': temperature, 'alert': False})
    else:
        return jsonify({'error': 'Failed to fetch temperature'})

if __name__ == '__main__':
    # Start the temperature checking loop in a separate thread
    temperature_check_thread = threading.Thread(target=check_temperature_alert)
    temperature_check_thread.start()
    
    app.run(debug=True)
