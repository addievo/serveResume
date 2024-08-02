from flask import Flask, request, send_file, render_template, redirect, url_for, session, flash
import os
import git
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Change this to a random secret key

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = {'docx', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['USERNAME'] = 'addie'
app.config['PASSWORD'] = 'addie'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == app.config['USERNAME'] and password == app.config['PASSWORD']:
            session['logged_in'] = True
            return redirect(url_for('edit'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


@app.route('/')
def serve_pdf():
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'resume.pdf')
    if os.path.exists(filepath):
        return send_file(filepath)
    else:
        return "No PDF file found", 404


@app.route('/edit')
@login_required
def edit():
    return render_template('files.html')


@app.route('/download/<file_type>')
@login_required
def download_file(file_type):
    if file_type not in ALLOWED_EXTENSIONS:
        return "Invalid file type", 400
    filename = f'resume.{file_type}'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath)
    else:
        return f"No {file_type.upper()} file found", 404


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'docx_file' not in request.files or 'pdf_file' not in request.files:
        return "Both DOCX and PDF files are required", 400

    docx_file = request.files['docx_file']
    pdf_file = request.files['pdf_file']

    if docx_file and allowed_file(docx_file.filename) and pdf_file and allowed_file(pdf_file.filename):
        docx_filename = 'resume.docx'
        pdf_filename = 'resume.pdf'
        docx_file.save(os.path.join(app.config['UPLOAD_FOLDER'], docx_filename))
        pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))

        # Push the updated files to GitHub
        repo = git.Repo('.')
        repo.git.add(os.path.join(app.config['UPLOAD_FOLDER'], docx_filename))
        repo.git.add(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))
        repo.git.commit('-m', 'Updated resume files')
        origin = repo.remote(name='origin')
        origin.push()

        return redirect(url_for('edit'))
    else:
        return "Invalid file types", 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5203)
