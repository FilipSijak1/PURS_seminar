from flask import Flask, request, redirect, url_for, render_template, session, make_response, jsonify
from flask import g
import MySQLdb
from hashlib import sha256
import requests
import paho.mqtt.client as mqtt
import json
from database.queries import LOGIN_QUERY, REGISTER_QUERY, SAVE_LOCATION_QUERY, DELETE_LOCATION_QUERY, GET_LOCATION_QUERY, CHECK_EMAIL_QUERY, CHECK_USERNAME_QUERY
from logging_config import setup_logging

app = Flask("app")
app.secret_key = '_5#y2L"F4Q8z-n-xec]//'

# logging setup
app.logger, script_logger = setup_logging()

# MQTT setup
mqtt_broker = "your_MQTT_broker_address"
mqtt_port = 1883
mqtt_user = "your_MQTT_username"
mqtt_password = "your_MQTT_password"
moisture_topic = "sensor/moisture"
water_level_topic = "sensor/water_level"
watering_status_topic = "control/watering_status"

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(mqtt_user, mqtt_password)

moisture_level = None
water_level = None

# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    app.logger.info(f"Connected to MQTT broker with result code {rc}")
    client.subscribe(moisture_topic)
    client.subscribe(water_level_topic)

# Callback for received messages
def on_message(client, userdata, msg):
    global moisture_level, water_level
    app.logger.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")
    if msg.topic == moisture_topic:
        moisture_level = int(msg.payload.decode())
    elif msg.topic == water_level_topic:
        water_level = int(msg.payload.decode())
    check_conditions_and_publish()

# Function to check conditions and publish the watering status
def check_conditions_and_publish():
    global moisture_level, water_level
    if moisture_level is not None and water_level is not None:
        weather_ok = fetchWeatherForSavedLocation()
        mqtt_ok = checkMQTTDataAndWater()
        if weather_ok and mqtt_ok:
            mqtt_client.publish(watering_status_topic, "true")
        else:
            mqtt_client.publish(watering_status_topic, "false")

# MQTT client setup
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

# Log event endpoint
@app.route('/log_event', methods=['POST'])
def log_event():
    data = request.json
    script_logger.info(f"Client log: {data['message']}")
    return '', 204

# Save location endpoint
@app.route('/save_location', methods=['POST'])
def save_location():
    response = make_response()
    location_data = request.json
    app.logger.info(f"Received location data: {location_data}")

    try:
        # Delete the previous location from the database if it exists
        g.cursor.execute(DELETE_LOCATION_QUERY, (session['user_id'],))
        app.logger.info(f"Deleted previous location for user_id: {session['user_id']}")

        # Insert the new location into the database
        g.cursor.execute(SAVE_LOCATION_QUERY, (location_data['location'], session['user_id']))
        g.connection.commit()
        app.logger.info(f"Saved new location: {location_data['location']} for user_id: {session['user_id']}")
        response.data = 'Uspješno spremljena nova lokacija'
        response.status_code = 201
    except Exception as e:
        g.connection.rollback()
        app.logger.error(f"Error saving location: {str(e)}")
        response.data = f'Greška prilikom spremanja lokacije: {str(e)}'
        response.status_code = 500

    return response

# Example function to fetch weather for saved location
def fetchWeatherForSavedLocation():
    try:
        g.cursor.execute(GET_LOCATION_QUERY, (session['user_id'],))
        location = g.cursor.fetchone()
        app.logger.info(f"Fetched location for user_id: {session['user_id']} - {location}")

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

# Function to check MQTT data and decide on watering
def checkMQTTDataAndWater():
    global moisture_level, water_level
    try:
        # Check conditions
        if water_level < 25:
            app.logger.info("Water level too low, watering disabled.")
            return False
        elif moisture_level > 50:
            app.logger.info("Soil moisture too high, watering disabled.")
            return False
        else:
            app.logger.info("Conditions suitable for watering.")
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
    # Provjerava je li korisnik već prijavljen
    if 'username' in session:
        return redirect(url_for('index'))
    
    # Ako nije prijavljen, prikaži stranicu za prijavu
    response = render_template('login.html', title='Login stranica')
    return response

@app.get('/vremenska_prognoza')
def vremenska_prognoza():
    response = render_template('vremenska_prognoza.html')
    return response, 200

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html', title='Registracija')
    
    response = make_response()
    user_data = request.json  # Čitanje JSON podataka iz zahtjeva

    # Kopiramo user_data i uklanjamo lozinke za logiranje
    log_data = user_data.copy()
    log_data.pop('lozinka', None)
    log_data.pop('ponovljena_lozinka', None)
    app.logger.info(f"Received user data: {log_data}")

    # Provjerava se jesu li svi potrebni podaci prisutni
    required_fields = ['ime', 'prezime', 'korisnicko_ime', 'lozinka', 'ponovljena_lozinka', 'email']
    if all(field in user_data for field in required_fields):
        # Provjera podudaranja lozinki
        if user_data['lozinka'] != user_data['ponovljena_lozinka']:
            response.data = 'Lozinke se ne podudaraju'
            response.status_code = 400
        else:
            try:
                # Provjera postojanja korisnika s istim emailom
                g.cursor.execute(CHECK_EMAIL_QUERY, (user_data['email'],))
                existing_email = g.cursor.fetchone()
                app.logger.info(f"Existing email: {existing_email}")

                # Provjera postojanja korisnika s istim korisničkim imenom
                g.cursor.execute(CHECK_USERNAME_QUERY, (user_data['korisnicko_ime'],))
                existing_username = g.cursor.fetchone()
                app.logger.info(f"Existing username: {existing_username}")

                if existing_email:
                    response.data = 'Korisnik s tom email adresom već postoji'
                    response.status_code = 400
                elif existing_username:
                    response.data = 'Korisnik s tim korisničkim imenom već postoji'
                    response.status_code = 400
                else:
                    # Izvršavanje SQL upita s podacima korisnika
                    hashed_lozinka = sha256(user_data['lozinka'].encode()).hexdigest()
                    app.logger.info(f"Hashed password: {hashed_lozinka}")
                    g.cursor.execute(REGISTER_QUERY, (user_data['ime'], user_data['prezime'], user_data['korisnicko_ime'], hashed_lozinka, user_data['email']))
                    g.connection.commit()
                    response.data = 'Uspješno ste registrirali korisnika'
                    response.status_code = 201
            except Exception as e:
                app.logger.error(f"Error during registration: {str(e)}")
                response.data = f'Greška prilikom registracije: {str(e)}'
                response.status_code = 500
    else:
        response.data = 'Nisu pruženi svi potrebni podaci'
        response.status_code = 400
    
    return response

@app.route('/login', methods=['POST'])
def login():
    response = make_response()
    username = request.form.get('korisnicko_ime')
    password = request.form.get('lozinka')

    try:
        # Provjera postojanja korisnika s unesenim korisničkim imenom
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
                
                # Nakon prijave korisnika, automatski dohvatimo vremenske podatke za spremljenu lokaciju
                fetchWeatherForSavedLocation()

                return redirect(url_for('index'))
            else:
                response.data = 'Pogrešno korisničko ime ili lozinka'
                response.status_code = 401
        else:
            response.data = 'Korisnik ne postoji'
            response.status_code = 404
    except Exception as e:
        app.logger.error(f"Error during login: {str(e)}")
        response.data = f'Greška prilikom prijave: {str(e)}'
        response.status_code = 500

    return response

@app.route('/update_weather', methods=['POST'])
def update_weather():
    response = make_response()
    weather_data = fetchWeatherForSavedLocation()  # Dohvaćanje vremenskih podataka pomoću funkcije fetchWeatherForSavedLocation

    try:
        if weather_data:
            response.data = 'Podaci o vremenskoj prognozi su uspješno ažurirani'
            response.status_code = 200
        else:
            response.data = 'Podaci o vremenskoj prognozi nisu dostupni'
            response.status_code = 404
    except Exception as e:
        response.data = f'Greška prilikom ažuriranja podataka o vremenskoj prognozi: {str(e)}'
        response.status_code = 500
    
    return response

@app.route('/get_saved_location', methods=['GET'])
def get_saved_location():
    try:
        # Dohvati spremljenu lokaciju iz baze podataka
        g.cursor.execute(GET_LOCATION_QUERY, (session['user_id'],))
        location = g.cursor.fetchone()[0]  # Pretpostavljamo da postoji samo jedna spremljena lokacija po korisniku

        return jsonify({'location': location}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
