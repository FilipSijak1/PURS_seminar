from flask import Flask, request, redirect, url_for, render_template, session, make_response, url_for
from flask import g
import MySQLdb
from hashlib import sha256



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
                # Provjera postojanja korisnika s istim emailom
                check_email_query = "SELECT * FROM korisnik WHERE email = %s"
                g.cursor.execute(check_email_query, (user_data['email'],))
                existing_email = g.cursor.fetchone()

                # Provjera postojanja korisnika s istim korisničkim imenom
                check_username_query = "SELECT * FROM korisnik WHERE korisnicko_ime = %s"
                g.cursor.execute(check_username_query, (user_data['korisnicko_ime'],))
                existing_username = g.cursor.fetchone()

                if existing_email:
                    response.data = 'Korisnik s tom email adresom već postoji'
                    response.status_code = 400
                elif existing_username:
                    response.data = 'Korisnik s tim korisničkim imenom već postoji'
                    response.status_code = 400
                else:
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

@app.post('/login')
def login():
    response = make_response()
    username = request.form.get('korisnicko_ime')
    password = request.form.get('lozinka')

    try:
        query = "SELECT * FROM korisnik WHERE korisnicko_ime = %s AND password = UNHEX(SHA2(%s, 256))"
        g.cursor.execute(query, (username, password))
        user = g.cursor.fetchone()

        if user:
            session['username'] = user[3]  # Save username in session
            return redirect(url_for('index'))
        else:
            response.data = 'Pogrešno korisničko ime ili lozinka'
            response.status_code = 401
    except Exception as e:
        response.data = f'Greška prilikom prijave: {str(e)}'
        response.status_code = 500
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
