from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
import sqlite3
import os
import datetime
import csv
import openpyxl
import logging

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'data/entries.db'

# Error Logging Setup
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    filename='logs/errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize Database
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''DROP TABLE IF EXISTS entries''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_number TEXT,
            car_type TEXT,
            car_code TEXT,
            inspector_id TEXT,
            pull_area TEXT,
            discharge_area TEXT,
            notes TEXT,
            reference_number TEXT,
            date_time TEXT,
            photo TEXT,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Generate Reference Number
def generate_reference():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM entries WHERE date_time LIKE ?", (f"{today}%",))
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"{today}-{str(count).zfill(4)}"

# Home Route
@app.route('/')
def home():
    reference_number = request.args.get('reference_number')
    return render_template('form.html', reference_number=reference_number)

# Submit Route
@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Retrieve Form Data
        car_number = request.form['carNumber']
        car_type = request.form['carType']
        car_code = request.form['carCode']
        inspector_id = request.form['inspectorId']
        pull_area = request.form['pullArea']
        discharge_area = request.form['dischargeArea']
        notes = request.form.get('notes', '')
        location = request.form.get('location', '')
        photo = request.files['photo'] if 'photo' in request.files else None

        # Save Photo
        photo_path = None
        if photo and photo.filename != '':
            photo_folder = 'static/uploads/'
            if not os.path.exists(photo_folder):
                os.makedirs(photo_folder)
            photo_path = os.path.join(photo_folder, photo.filename)
            photo.save(photo_path)

        # Generate Reference Number and Date
        reference_number = generate_reference()
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert Data into Database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO entries (car_number, car_type, car_code, inspector_id, pull_area, discharge_area, notes, reference_number, date_time, photo, location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (car_number, car_type, car_code, inspector_id, pull_area, discharge_area, notes, reference_number, date_time, photo_path, location))
        conn.commit()
        conn.close()

        # Return JSON Response for AJAX
        return jsonify({'reference_number': reference_number})
    except Exception as e:
        logging.error(f"Error in form submission: {e}")
        return jsonify({'error': str(e)}), 400

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash("Please enter both username and password")
                return render_template('login.html')
                
            if username == 'admin' and password == 'password123':
                session['logged_in'] = True
                return redirect(url_for('dashboard'))
            
            flash("Invalid username or password")
        except Exception as e:
            flash("An error occurred. Please try again.")
            logging.error(f"Login error: {str(e)}")
    return render_template('login.html')

# Dashboard Route
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    entries = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', entries=entries)

# Export to CSV Route
@app.route('/export_csv')
def export_csv():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    entries = cursor.fetchall()
    conn.close()

    # Prepare CSV Output
    output = [['ID', 'Car Number', 'Car Type', 'Car Code', 'Inspector ID', 'Pull Area', 'Discharge Area', 'Notes', 'Reference Number', 'Date & Time', 'Photo']]
    for entry in entries:
        output.append(entry)

    response = make_response('\n'.join([','.join(map(str, row)) for row in output]))
    response.headers["Content-Disposition"] = "attachment; filename=entries.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=True)
