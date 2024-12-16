from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
import sqlite3
import os
import datetime
import csv
import openpyxl
import io
import json
import logging
from PIL import Image

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.permanent_session_lifetime = datetime.timedelta(days=1)
app.config['HCAPTCHA_SITE_KEY'] = '10000000-ffff-ffff-ffff-000000000001'
app.config['HCAPTCHA_SECRET_KEY'] = '0x0000000000000000000000000000000000000000'

DATABASE = 'data/entries.db'

# Enhanced Logging Setup
for dir_path in ['logs', 'logs/entries', 'logs/user_info']:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

# Error logger
error_logger = logging.getLogger('error_logger')
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler('logs/errors.log')
error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
error_logger.addHandler(error_handler)

# Entry logger (creates new file daily)
def get_entry_logger():
    logger = logging.getLogger('entry_logger')
    logger.setLevel(logging.INFO)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    handler = logging.FileHandler(f'logs/entries/{date_str}_entries.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    if logger.handlers:
        logger.handlers.clear()
    logger.addHandler(handler)
    return logger

# User info logger (creates new file daily)
def get_user_logger():
    logger = logging.getLogger('user_logger')
    logger.setLevel(logging.INFO)
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    handler = logging.FileHandler(f'logs/user_info/{date_str}_user_info.log')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    if logger.handlers:
        logger.handlers.clear()
    logger.addHandler(handler)
    return logger

def log_user_info(request):
    user_logger = get_user_logger()
    info = {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'referrer': request.referrer,
        'path': request.path,
        'method': request.method,
        'platform': request.user_agent.platform,
        'browser': request.user_agent.browser,
        'language': request.headers.get('Accept-Language')
    }
    user_logger.info(f"User Access - {json.dumps(info, indent=2)}")

# Initialize Database
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
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
            location TEXT,
            last_submission TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Generate Reference Number
def generate_reference():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Get count of entries for today only
    cursor.execute("SELECT COUNT(*) FROM entries WHERE date_time >= ? AND date_time < ?", 
                  (f"{today} 00:00:00", f"{today} 23:59:59"))
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"{today}-{str(count).zfill(4)}"

# Home Route
@app.route('/')
def home():
    log_user_info(request)
    reference_number = request.args.get('reference_number')
    return render_template('form.html', reference_number=reference_number)

# Submit Route
@app.route('/submit', methods=['POST'])
def submit():
    try:
        # Verify hCaptcha
        h_captcha_response = request.form.get('h-captcha-response')
        if not h_captcha_response:
            return jsonify({'error': 'Please complete the CAPTCHA'}), 400
            
        # Retrieve Form Data
        car_number = request.form['carNumber']
        
        # Check cooldown period
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT last_submission FROM entries WHERE car_number = ? ORDER BY last_submission DESC LIMIT 1", (car_number,))
        last_entry = cursor.fetchone()
        
        if last_entry:
            try:
                # Try multiple date formats
                date_formats = [
                    "%Y-%m-%d %H:%M:%S",  # Standard format
                    "%m/%d/%Y %I:%M:%S %p",  # US format
                    "%d/%m/%Y %H:%M:%S",  # UK format
                    "%Y/%m/%d %H:%M:%S",  # Asian format
                    "%d-%m-%Y %H:%M:%S",  # UAE format
                    "%Y.%m.%d %H:%M:%S"   # Alternative format
                ]
                
                last_time = None
                for date_format in date_formats:
                    try:
                        last_time = datetime.datetime.strptime(last_entry[0], date_format)
                        break
                    except ValueError:
                        continue
                        
                if last_time is None:
                    raise ValueError("Invalid date format")
                    
                current_time = datetime.datetime.now()
                time_diff = (current_time - last_time).total_seconds()
            except Exception as e:
                return jsonify({'error': str(e)}), 400
            
            if time_diff < 60:  # 60 seconds cooldown
                return jsonify({'error': 'Please wait 60 seconds before submitting another entry for the same car number'}), 429
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
            # Validate image format
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff'}
            file_ext = photo.filename.rsplit('.', 1)[1].lower()
            if file_ext not in allowed_extensions:
                return jsonify({'error': 'Invalid image format. Allowed formats: PNG, JPG, JPEG, GIF, WEBP, BMP, TIFF'}), 400

            photo_folder = 'static/uploads/'
            if not os.path.exists(photo_folder):
                os.makedirs(photo_folder)
            
            # Generate unique filename to avoid conflicts
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{photo.filename}"
            photo_path = os.path.join(photo_folder, safe_filename)
            
            try:
                with Image.open(photo) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'P', 'CMYK'): 
                        img = img.convert('RGB')
                    # Compress and save image
                    img.save(photo_path, 'JPEG', quality=85, optimize=True)
            except Exception as e:
                return jsonify({'error': f'Error processing image: {str(e)}'}), 400

        # Generate Reference Number and Date
        reference_number = generate_reference()
        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Insert Data into Database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO entries (car_number, car_type, car_code, inspector_id, pull_area, discharge_area, notes, reference_number, date_time, photo, location, last_submission)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (car_number, car_type, car_code, inspector_id, pull_area, discharge_area, notes, reference_number, date_time, photo_path, location, date_time))
        conn.commit()
        conn.close()

        # Log the entry
        entry_logger = get_entry_logger()
        entry_logger.info(
            f"New Entry - Reference: {reference_number}, Car: {car_number}, "
            f"Type: {car_type}, Inspector: {inspector_id}, "
            f"Areas: {pull_area}->{discharge_area}"
        )

        # Return JSON Response for AJAX
        return jsonify({'reference_number': reference_number})
    except Exception as e:
        logging.error(f"Error in form submission: {e}")
        return jsonify({'error': str(e)}), 400

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("Please enter both username and password")
            return render_template('login.html')
            
        if username == 'admin' and password == 'password123':
            session['logged_in'] = True
            session.permanent = True
            return redirect(url_for('dashboard'))
        
        flash("Invalid username or password")
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

# Export to Excel Route
@app.route('/export_excel')
def export_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    entries = cursor.fetchall()
    conn.close()

    # Create Excel workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['ID', 'Car Number', 'Car Type', 'Car Code', 'Inspector ID', 'Pull Area', 
               'Discharge Area', 'Notes', 'Reference Number', 'Date & Time', 'Photo', 'Location'])
    
    for entry in entries:
        ws.append(entry)

    # Create response
    response = make_response()
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    response.data = output.read()
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=entries.xlsx'
    return response

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8080, debug=True)
