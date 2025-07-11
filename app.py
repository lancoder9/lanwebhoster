from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
import os, subprocess, uuid

app = Flask(__name__)
UPLOAD_FOLDER = 'static/hosted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    entries = []
    for fname in os.listdir(UPLOAD_FOLDER):
        if fname.endswith(".meta"):
            with open(os.path.join(UPLOAD_FOLDER, fname), 'r') as f:
                name, icon, file = f.read().splitlines()
                entries.append({'name': name, 'icon': icon, 'file': file})
    return render_template('index.html', projects=entries)

@app.route('/host', methods=['GET', 'POST'])
def host():
    if request.method == 'POST':
        projname = request.form['project']
        projfile = request.files['project_file']
        iconfile = request.files['icon_file']
        if projfile and iconfile and projname:
            proj_id = str(uuid.uuid4())[:8]
            proj_filename = f"{proj_id}_{projfile.filename}"
            icon_filename = f"{proj_id}_{iconfile.filename}"
            proj_path = os.path.join(UPLOAD_FOLDER, proj_filename)
            icon_path = os.path.join(UPLOAD_FOLDER, icon_filename)
            projfile.save(proj_path)
            iconfile.save(icon_path)
            with open(os.path.join(UPLOAD_FOLDER, f"{proj_id}.meta"), 'w') as f:
                f.write(f"{projname}\n{icon_filename}\n{proj_filename}")
    return render_template('host.html')

@app.route('/hostedsite/<path:filename>')
def hostedsite(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/hostedsite/console')
def console():
    return render_template('console.html')

@app.route('/execute', methods=['POST'])
def execute():
    command = request.json['command']
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=10)
        return jsonify(output=output.decode())
    except subprocess.CalledProcessError as e:
        return jsonify(output=e.output.decode())
    except Exception as e:
        return jsonify(output=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
