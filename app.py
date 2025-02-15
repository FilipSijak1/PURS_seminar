from flask import Flask, request, redirect, url_for, render_template, session, make_response, jsonify
from flask import g
import MySQLdb
from hashlib import sha256
import requests
import paho.mqtt.client as mqtt
import json
from database.queries import LOGIN_QUERY, REGISTER_QUERY, CHECK_LOCATION_EXISTS_QUERY, INSERT_LOCATION_QUERY, UPDATE_LOCATION_QUERY, CHECK_EMAIL_QUERY, CHECK_USERNAME_QUERY, GET_LOCATION_QUERY
from logging_config import setup_logging

app = Flask("app")
app.secret_key = '_5#y2L"F4Q8z-n-xec]//'

# logging setup
app.logger, script_logger = setup_logging()

# MQTT setup
mqtt_broker = "192.168.0.3"
mqtt_port = 1883
sensor_data_topic = "sensor/data"
watering_status_topic = "control/watering_status"

moisture_level = None
water_level = None
watering_status = None

# Global variable to store user_id
user_id = None

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    app.logger.info(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(sensor_data_topic)

# Callback for received messages
def on_message(client, userdata, msg):
    global moisture_level, water_level, user_id
    app.logger.info(f"Message received on topic {msg.topic}")
    if msg.topic == sensor_data_topic:
        data = msg.payload.decode().split(',')
        moisture_level = int(data[0])
        water_level = int(data[1])
        app.logger.info(f"Received sensor data: moisture_level={moisture_level}, water_level={water_level}")
        check_conditions_and_publish(user_id)

# MQTT client setup
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

# Function to check conditions and publish the watering status
def check_conditions_and_publish(user_id):
    global moisture_level, water_level, watering_status
    app.logger.info("Checking conditions and publishing watering status")
    if moisture_level is not None and water_level is not None:
        weather_ok = fetchWeatherForSavedLocation(user_id)
        mqtt_ok = checkMQTTDataAndWater()
        new_watering_status = "true" if weather_ok and mqtt_ok else "false"
        if new_watering_status != watering_status:
            watering_status = new_watering_status
            mqtt_client.publish(watering_status_topic, watering_status)
            app.logger.info(f"Watering status changed to: {watering_status}")
        else:
            app.logger.info("Watering status remains unchanged")
    else:
        app.logger.info("Moisture level or water level is None")

# Example function to fetch weather for saved location
def fetchWeatherForSavedLocation(user_id):
    try:
        connection = MySQLdb.connect(host="localhost", user="app", passwd="1234", db="app")
        cursor = connection.cursor()
        cursor.execute(GET_LOCATION_QUERY, (user_id,))
        location = cursor.fetchone()
        app.logger.info(f"Fetched location for user_id: {user_id} - {location}")

        if location:
            location = location[0]  # Assume there is only one saved location per user
            APIKey = 'f48314147c7960704569a1010beefbdb'
            fetch_url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={APIKey}"
            # Fetch weather data for the saved location
            response = requests.get(fetch_url)
            weather_data = response.json()
            app.logger.info(f"Weather data fetched: {weather_data}")

            # Process weather data
            weather_condition = weather_data['weather'][0]['main']
            temperature = weather_data['main']['temp']

            # Check weather conditions
            if weather_condition in ['Clouds', 'Rain'] or temperature < 10 or temperature > 27:
                app.logger.info("Weather conditions not suitable for watering.")
                return False
            else:
                app.logger.info("Weather conditions suitable for watering.")
                return True
        else:
            app.logger.info("No location found for user.")
            return None
    except Exception as e:
        app.logger.error(f"Error fetching weather data: {str(e)}")
        return None
    finally:
        cursor.close()
        connection.close()

# Function to check MQTT data and decide on watering
def checkMQTTDataAndWater():
    global moisture_level, water_level
    try:
        # Check conditions
        if water_level < 25:
            return False
        elif moisture_level > 50:
            return False
        else:
            return True
    except Exception as e:
        app.logger.error(f"Error checking MQTT data: {str(e)}")
        return False

@app.before_request
def before_request_func():
    g.connection = MySQLdb.connect(host="localhost", user="app",
                                   passwd="1234", db="app")
    g.cursor = g.connection.cursor()
    if request.path.startswith('/static'):
        return  # Skip the login check for static files
    if request.path == '/login':
        return
    if session.get('username') is None and request.path != '/register':
        return redirect(url_for('login_page'))

@app.teardown_request
def teardown_request_func(exception=None):
    if hasattr(g, 'cursor'):
        g.cursor.close()
    if hasattr(g, 'connection'):
        g.connection.close()

@app.get('/')
def index():
    response = render_template('index.html')
    return response, 200

@app.get('/logout')
def logout():
    session.pop('username')
    return redirect(url_for('login_page'))

@app.get('/login')
def login_page():
    # Check if the user is already logged in
    if 'username' in session:
        return redirect(url_for('index'))
    
    # If not logged in, display the login page
    response = render_template('login.html', title='Login Page')
    return response

@app.get('/vremenska_prognoza')
def vremenska_prognoza():
    response = render_template('vremenska_prognoza.html')
    return response, 200

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html', title='Registration')
    
    response = make_response()
    user_data = request.json  # Read JSON data from the request

    # Copy user_data and remove passwords for logging
    log_data = user_data.copy()
    log_data.pop('lozinka', None)
    log_data.pop('ponovljena_lozinka', None)
    app.logger.info(f"Received user data: {log_data}")

    # Check if all required fields are present
    required_fields = ['ime', 'prezime', 'korisnicko_ime', 'lozinka', 'ponovljena_lozinka', 'email']
    if all(field in user_data for field in required_fields):
        # Check if passwords match
        if user_data['lozinka'] != user_data['ponovljena_lozinka']:
            response.data = 'Passwords do not match'
            response.status_code = 400
        else:
            try:
                # Check if a user with the same email already exists
                g.cursor.execute(CHECK_EMAIL_QUERY, (user_data['email'],))
                existing_email = g.cursor.fetchone()
                app.logger.info(f"Existing email: {existing_email}")

                # Check if a user with the same username already exists
                g.cursor.execute(CHECK_USERNAME_QUERY, (user_data['korisnicko_ime'],))
                existing_username = g.cursor.fetchone()
                app.logger.info(f"Existing username: {existing_username}")

                if existing_email:
                    response.data = 'A user with that email address already exists'
                    response.status_code = 400
                elif existing_username:
                    response.data = 'A user with that username already exists'
                    response.status_code = 400
                else:
                    # Execute SQL query with user data
                    hashed_lozinka = sha256(user_data['lozinka'].encode()).hexdigest()
                    app.logger.info(f"Hashed password: {hashed_lozinka}")
                    g.cursor.execute(REGISTER_QUERY, (user_data['ime'], user_data['prezime'], user_data['korisnicko_ime'], hashed_lozinka, user_data['email']))
                    g.connection.commit()
                    response.data = 'User successfully registered'
                    response.status_code = 201
            except Exception as e:
                app.logger.error(f"Error during registration: {str(e)}")
                response.data = f'Error during registration: {str(e)}'
                response.status_code = 500
    else:
        response.data = 'Not all required data provided'
        response.status_code = 400
    
    return response

@app.route('/login', methods=['POST'])
def login():
    global user_id
    response = make_response()
    username = request.form.get('korisnicko_ime')
    password = request.form.get('lozinka')

    try:
        # Check if a user with the entered username exists
        g.cursor.execute(CHECK_USERNAME_QUERY, (username,))
        user = g.cursor.fetchone()

        if user:
            # Hash the password for comparison
            hashed_password = sha256(password.encode()).hexdigest()
            app.logger.info(f"Executing query: {LOGIN_QUERY} with username: {username} and hashed password: {hashed_password}")

            g.cursor.execute(LOGIN_QUERY, (username, hashed_password))
            user = g.cursor.fetchone()

            # Debugging: Print the result from the database
            app.logger.info(f"Query result: {user}")

            if user:
                session['username'] = user[3]  # Save username in session
                session['user_id'] = user[0]
                user_id = user[0]  # Store user_id in global variable
                
                # After user login, automatically fetch weather data for saved location
                fetchWeatherForSavedLocation(user[0])

                return redirect(url_for('index'))
            else:
                response.data = 'Incorrect username or password'
                response.status_code = 401
        else:
            response.data = 'User does not exist'
            response.status_code = 404
    except Exception as e:
        app.logger.error(f"Error during login: {str(e)}")
        response.data = f'Error during login: {str(e)}'
        response.status_code = 500

    return response

@app.route('/update_weather', methods=['POST'])
def update_weather():
    response = make_response()
    weather_data = fetchWeatherForSavedLocation(session['user_id'])  # Fetch weather data using fetchWeatherForSavedLocation function

    try:
        if weather_data:
            response.data = 'Weather data successfully updated'
            response.status_code = 200
        else:
            response.data = 'Weather data not available'
            response.status_code = 404
    except Exception as e:
        response.data = f'Error updating weather data: {str(e)}'
        response.status_code = 500
    
    return response

@app.route('/get_saved_location', methods=['GET'])
def get_saved_location():
    try:
        # Fetch saved location from the database
        g.cursor.execute(GET_LOCATION_QUERY, (session['user_id'],))
        location = g.cursor.fetchone()[0]  
        return jsonify({'location': location}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_sensor_data')
def get_sensor_data():
    global moisture_level, water_level
    return jsonify({
        'moisture_level': moisture_level if moisture_level is not None else 0,
        'water_level': water_level if water_level is not None else 0
    })

@app.route('/log_event', methods =['POST'])
def log_event():
    try:
        event_data = request.json
        app.logger.info(f"Received event data: {event_data}")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        app.logger.error(f"Error logging event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/save_location', methods=['POST'])
def save_location():
    try:
        location_data = request.json
        user_id = session.get('user_id')
        app.logger.info(f"Saving location for user_id: {user_id} - {location_data}")
        
        if 'location' not in location_data:
            response = jsonify({'error': 'Location data is missing'})
            response.status_code = 400
            return response
        
        # Check if a location already exists for the user
        g.cursor.execute(CHECK_LOCATION_EXISTS_QUERY, (user_id,))
        location_exists = g.cursor.fetchone()[0] > 0
        
        if location_exists:
            # Update existing location
            g.cursor.execute(UPDATE_LOCATION_QUERY, (location_data['location'], user_id))
        else:
            # Insert new location
            g.cursor.execute(INSERT_LOCATION_QUERY, (user_id, location_data['location']))
        
        g.connection.commit()
        app.logger.info("Location saved successfully")
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        app.logger.error(f"Error saving location: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
