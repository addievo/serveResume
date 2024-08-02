from flask import Flask, send_file

app = Flask(__name__)

@app.route('/')
def serve_pdf():
    return send_file('./resume.pdf')

@app.route('/docx')
def serve_docx():
    return send_file('./Resume Updated.docx')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5203)
