from flask import Flask, render_template,request,redirect,url_for,session
from database import db
from flask_mail import Mail, Message
import random
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import bcrypt


app = Flask(__name__)
app.secret_key = 'xyz'

s=URLSafeTimedSerializer(app.secret_key)

# data={'uttej@gmail.com':'12345','chary@gmail.com':'123','abc@gmail.com':'123'}

# products={'milk','bread'}

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'uttejmedarapu511@gmail.com'
app.config['MAIL_PASSWORD'] = 'kpzp ehbt fzpi jetk'
app.config['MAIL_DEFAULT_SENDER'] = 'uttejmedarapu511@gmail.com'

mail = Mail(app)

def generate_otp():
    # print('generate_otp called.......')
    return str(random.randint(100000, 999999))

def send_otp_email(name, email, otp):
    print('send_otp_email called.......')
    try:
        msg = Message('OTP for Verification', recipients=[email])
        msg.body = f"Hello {name}!\nYour OTP is: {otp}"
        mail.send(msg)
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' in session and 'user_id' in session:
        user_id = session['user_id']
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM notes WHERE user_id = %s ORDER BY created_at DESC"
        cursor.execute(query, (user_id,))
        notes = cursor.fetchall()
        cursor.close()
        return render_template('dashboard.html', username=session['username'], notes=notes)
    return redirect(url_for('login'))

@app.route('/createnote', methods=['POST'])
def create_note():
    if 'user_id' in session:
        content = request.form.get('content')
        user_id = session['user_id']
        cursor = db.cursor()
        cursor.execute("INSERT INTO notes (user_id, content) VALUES (%s, %s)", (user_id, content))
        db.commit()
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cursor=db.cursor(dictionary=True)
    if request.method == 'POST':
        new_content = request.form.get('content')
        cursor.execute("UPDATE notes SET content=%s WHERE id=%s AND user_id=%s",(new_content,
        note_id,session['user_id']))
        db.commit()
        return redirect(url_for('dashboard'))
    cursor.execute("SELECT * FROM notes WHERE id=%s AND user_id=%s",(note_id,session ['user_id']))
    note=cursor.fetchone()
    cursor.close()
    if note:
        return render_template('editnote.html', note=note)
    return redirect(url_for('dashboard'))

@app.route('/delete_note/<int:note_id>')
def delete_note(note_id):
    if 'user_id' in session:
        cursor = db.cursor()
        cursor.execute("DELETE FROM notes WHERE id=%s AND user_id=%s",(note_id, session ['user_id']))
        db.commit()
    return redirect(url_for('dashboard'))


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password =bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt()).decode('utf-8')

        cursor = db.cursor()
        cursor.execute("SELECT id,username FROM users WHERE email=%s and password=%s", (email,))
        user = cursor.fetchone()
        # print(user)

        if user:
            return render_template('registration.html', error='Email already registered')

        # session['username'] = username
        cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
        db.commit()

        return redirect(url_for('login'))
    
    return render_template('registration.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cursor = db.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.checkpw(password.encode('utf-8'),user[2].encode('utf-8')):
            session['username'] = user[1]
            session['user_id'] = user[0]
            otp = generate_otp()
            session['otp']= otp
            if send_otp_email(user[1], email, otp):
                return redirect(url_for('verify'))
        else:
            return render_template('login.html', error='Invalid login credentials')

    return render_template('login.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    # error = request.args.get('error')

    if request.method == 'POST':
        entered_otp = request.form.get('otp')

        if 'otp' in session and session['otp'] == entered_otp:
            del session['otp']
            return redirect(url_for('dashboard'))
        else:
            return render_template('verify.html', error="Invalid OTP, please try again.")

    return render_template('verify.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        email = request.form.get('email')
        cursor = db.cursor()
        cursor.execute("SELECT username FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        if user:
            session['email']= email
            token = s.dumps(email, salt='password-reset-salt')
            reset_url = url_for('resetpassword', token = token, _external = True)

            msg = Message('password reset request', recipients=[email])
            msg.body =f'click the link to reset the password: {reset_url} \n\n This link will expire in 1 hour.'
            mail.send(msg)

            return render_template('forgotpassword.html', error="link sent to your email, please check")
        return render_template('forgotpassword.html', error="Email not registered")
    return render_template('forgotpassword.html')

@app.route('/resetpassword/<token>', methods=['GET', 'POST'])
def resetpassword(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)
    except SignatureExpired:
        return render_template('resetpassword.html', message="Token expired. Request a new link.", message_type="error")

    if request.method == 'POST':
        password = request.form.get('password')
        confirmpassword = request.form.get('confirmpassword')
        if password == confirmpassword:
            email = session.get('email')
            if email:
                cursor = db.cursor()
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("UPDATE users SET password=%s WHERE email=%s", (hashed_password, email))
                db.commit()
                session.pop('email', None)
                return redirect(url_for('login'))
        else:
            return render_template('resetpassword.html', error="Passwords do not match")

    return render_template('resetpassword.html')


if __name__=='__main__':
    app.run(debug=True)


# to run virtual environment
# 1)Set-ExecutionPolicy Unrestricted -Scope Process
# 2)venv\Scripts\Activate.ps1
# 3)python app.py