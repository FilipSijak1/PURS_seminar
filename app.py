from flask import Flask, request, redirect, url_for, render_template, session, make_response, jsonify
from flask import g
import MySQLdb



app = Flask("app")
app.secret_key = '_5#y2L"F4Q8z-n-xec]/'

@app.before_request
def before_request_func():
    g.connection = MySQLdb.connect(host = "localhost", user = "app",
                                   passwd = "1234", db = "app")
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

@app.get('/login')
def login_page():
    response = render_template('login.html', title='Login stranica'), 200
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('registration.html', title='Registracija')
    
    response = make_response()
    user_data = request.json  # Čitanje JSON podataka iz zahtjeva

    # Provjerava se jesu li svi potrebni podaci prisutni
    required_fields = ['ime', 'prezime', 'korisnicko_ime', 'lozinka', 'ponovljena_lozinka', 'email']
    if all(field in user_data for field in required_fields):
        # Provjera podudaranja lozinki
        if user_data['lozinka'] != user_data['ponovljena_lozinka']:
            response.data = 'Lozinke se ne podudaraju'
            response.status_code = 400
        else:
            try:
                # Čitanje sadržaja SQL datoteke
                with app.open_resource('templates/registerUser.sql', mode='r') as file:
                    query = file.read()

                # Izvršavanje SQL upita s podacima korisnika
                g.cursor.execute(query, (user_data['ime'], user_data['prezime'], user_data['korisnicko_ime'], user_data['lozinka'], user_data['email']))
                g.connection.commit()
                response.data = 'Uspješno ste registrirali korisnika'
                response.status_code = 201
            except Exception as e:
                response.data = f'Greška prilikom registracije: {str(e)}'
                response.status_code = 500
    else:
        response.data = 'Nisu pruženi svi potrebni podaci'
        response.status_code = 400
    
    return response





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
