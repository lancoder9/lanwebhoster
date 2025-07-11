from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os, subprocess

app = Flask(__name__)
UPLOAD_FOLDER = 'static/hosted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    projects = os.listdir(UPLOAD_FOLDER)
    return render_template('index.html', projects=projects)

@app.route('/host', methods=['GET', 'POST'])
def host():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
    return render_template('host.html')

@app.route('/hostedsite/<project>')
def hostedsite(project):
    return send_from_directory(UPLOAD_FOLDER, project)

@app.route('/hostedsite/console')
def console():
    return render_template('console.html')

@app.route('/execute', methods=['POST'])
def execute():
    command = request.json['command']
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=10)
        return jsonify(output=result.decode())
    except subprocess.CalledProcessError as e:
        return jsonify(output=e.output.decode())
    except Exception as e:
        return jsonify(output=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
