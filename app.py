import os
import secrets  # For generating a random token
from flask import Flask, request, send_file, render_template, redirect, url_for, session, flash
import git
from functools import wraps
from datetime import timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Securely generate a random secret key

# Configuration
TOKEN_FILE = os.environ.get('AUTH_TOKEN_FILE', './utils/auth_token.txt')
UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'docx', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the directories exist
os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Session configuration for 90-day expiry
app.permanent_session_lifetime = timedelta(days=90)

# Token generation or loading
if not os.path.exists(TOKEN_FILE):
    token_value = secrets.token_hex(16)  # 32-character hex string
    with open(TOKEN_FILE, 'w') as f:
        f.write(token_value)
    app.logger.info("Generated new auth token.")
    print(f"Auth Token Generated: {token_value}")  # Echo the token to the console
else:
    with open(TOKEN_FILE, 'r') as f:
        token_value = f.read().strip()
    app.logger.info("Loaded existing auth token.")
    print(f"Auth Token Loaded: {token_value}")  # Optionally echo the loaded token

AUTH_TOKEN = token_value

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'auth_token' not in session or session['auth_token'] != AUTH_TOKEN:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login route that expects the auth token.
    If the user is already authenticated, redirect to /edit.
    """
    if 'auth_token' in session and session['auth_token'] == AUTH_TOKEN:
        # User is already logged in, redirect to /edit
        flash('You are already logged in.', 'info')
        return redirect(url_for('edit'))

    if request.method == 'POST':
        token_submitted = request.form.get('auth_token', '').strip()
        if token_submitted == AUTH_TOKEN:
            session.permanent = True  # Make the session permanent
            session['auth_token'] = AUTH_TOKEN
            flash('Logged in successfully.', 'success')
            return redirect(url_for('edit'))
        else:
            flash('Invalid token. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@token_required
def logout():
    """
    Logout route to clear the session.
    """
    session.pop('auth_token', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/')
def serve_pdf():
    """
    Serves the PDF file if present.
    """
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'resume.pdf')
    if os.path.exists(filepath):
        return send_file(filepath)
    else:
        return "No PDF file found.", 404

@app.route('/edit')
@token_required
def edit():
    """
    Render the file management page.
    """
    return render_template('files.html')

@app.route('/download/<file_type>')
@token_required
def download_file(file_type):
    """
    Allows downloading of DOCX or PDF if they exist.
    """
    if file_type not in ALLOWED_EXTENSIONS:
        flash('Invalid file type requested.', 'warning')
        return redirect(url_for('edit'))
    filename = f'resume.{file_type}'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        flash(f"No {file_type.upper()} file found.", 'warning')
        return redirect(url_for('edit'))

@app.route('/upload', methods=['POST'])
@token_required
def upload_file():
    """
    Handles uploading of DOCX and PDF files.
    """
    if 'docx_file' not in request.files or 'pdf_file' not in request.files:
        flash("Both DOCX and PDF files are required.", 'danger')
        return redirect(url_for('edit'))

    docx_file = request.files['docx_file']
    pdf_file = request.files['pdf_file']

    if not (docx_file and allowed_file(docx_file.filename)):
        flash("Invalid or missing DOCX file.", 'danger')
        return redirect(url_for('edit'))

    if not (pdf_file and allowed_file(pdf_file.filename)):
        flash("Invalid or missing PDF file.", 'danger')
        return redirect(url_for('edit'))

    # Define filenames and paths
    docx_filename = 'resume.docx'
    pdf_filename = 'resume.pdf'
    docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)

    # Save files
    docx_file.save(docx_path)
    pdf_file.save(pdf_path)
    app.logger.info("Files saved successfully.")

    # Attempt to push updates to Git
    try:
        repo = git.Repo('.')  # Ensure this directory is a Git repo
        repo.git.add(docx_path)
        repo.git.add(pdf_path)
        commit_message = 'Updated resume files'
        repo.git.commit('-m', commit_message)
        origin = repo.remote(name='origin')
        origin.push()
        flash("Files uploaded and pushed to repository successfully.", 'success')
        app.logger.info("Files pushed to Git repository successfully.")
    except git.exc.InvalidGitRepositoryError:
        app.logger.error("No valid Git repository found in the current directory.")
        flash("Internal Server Error: Git repository not found.", 'danger')
    except git.exc.GitCommandError as e:
        app.logger.error(f"Git command error: {e}")
        flash("Internal Server Error: Failed to push to Git repository.", 'danger')
    except Exception as e:
        app.logger.error(f"Unexpected error during Git push: {e}")
        flash("Internal Server Error: An unexpected error occurred.", 'danger')

    return redirect(url_for('edit'))

if __name__ == '__main__':
    # Run the Flask app
    app.run(host='0.0.0.0', port=5203)
