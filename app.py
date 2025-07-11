from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, flash, url_for, abort, Response
import os
import subprocess
import uuid
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Needed for flash messages

UPLOAD_FOLDER = 'static/hosted'
ALLOWED_PROJECT_EXTENSIONS = {'html', 'zip'}
ALLOWED_ICON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'ico'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

def sanitize_filename(filename):
    return secure_filename(filename)

# Dummy authentication decorator (replace with real logic)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # if not logged_in: abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    entries = []
    for fname in os.listdir(UPLOAD_FOLDER):
        if fname.endswith(".meta"):
            meta_path = os.path.join(UPLOAD_FOLDER, fname)
            try:
                with open(meta_path, 'r') as f:
                    lines = f.read().splitlines()
                    if len(lines) != 3:
                        continue  # Skip malformed meta
                    name, icon, file = lines
                    # Check if files exist
                    icon_path = os.path.join(UPLOAD_FOLDER, icon)
                    file_path = os.path.join(UPLOAD_FOLDER, file)
                    if os.path.exists(icon_path) and os.path.exists(file_path):
                        entries.append({'name': name, 'icon': icon, 'file': file})
                    else:
                        # Clean up orphaned meta
                        os.remove(meta_path)
            except Exception:
                continue
    return render_template('index.html', projects=entries)

@app.route('/host', methods=['GET', 'POST'])
@login_required
def host():
    message = ""
    error = ""
    if request.method == 'POST':
        projname = request.form.get('project', '').strip()
        projfile = request.files.get('project_file')
        iconfile = request.files.get('icon_file')

        # Validate project name
        if not projname:
            error = "Project name is required."
        elif any(projname == entry['name'] for entry in get_projects()):
            error = "A project with this name already exists."
        # Validate and save files
        elif not (projfile and allowed_file(projfile.filename, ALLOWED_PROJECT_EXTENSIONS)):
            error = f"Invalid or missing project file. Allowed: {ALLOWED_PROJECT_EXTENSIONS}"
        elif not (iconfile and allowed_file(iconfile.filename, ALLOWED_ICON_EXTENSIONS)):
            error = f"Invalid or missing icon file. Allowed: {ALLOWED_ICON_EXTENSIONS}"
        else:
            try:
                proj_id = str(uuid.uuid4())[:8]
                proj_filename = f"{proj_id}_{sanitize_filename(projfile.filename)}"
                icon_filename = f"{proj_id}_{sanitize_filename(iconfile.filename)}"
                proj_path = os.path.join(UPLOAD_FOLDER, proj_filename)
                icon_path = os.path.join(UPLOAD_FOLDER, icon_filename)

                projfile.save(proj_path)
                iconfile.save(icon_path)
                # Write meta file
                with open(os.path.join(UPLOAD_FOLDER, f"{proj_id}.meta"), 'w') as f:
                    f.write(f"{projname}\n{icon_filename}\n{proj_filename}")
                message = "Project uploaded successfully!"
            except Exception as e:
                error = f"Upload failed: {str(e)}"
    return render_template('host.html', message=message, error=error)

def get_projects():
    entries = []
    for fname in os.listdir(UPLOAD_FOLDER):
        if fname.endswith(".meta"):
            try:
                with open(os.path.join(UPLOAD_FOLDER, fname), 'r') as f:
                    name, icon, file = f.read().splitlines()
                    entries.append({'name': name, 'icon': icon, 'file': file})
            except Exception:
                continue
    return entries

@app.route('/hostedsite/<path:filename>')
def hostedsite(filename):
    # Prevent directory traversal attacks and allow only known hosted files
    safe_filename = sanitize_filename(filename)
    allowed = any(
        safe_filename == entry['icon'] or safe_filename == entry['file']
        for entry in get_projects()
    )
    if not allowed:
        abort(404, description="File not found.")
    # Serve only allowed file types
    ext = safe_filename.rsplit('.', 1)[-1].lower()
    if ext not in (ALLOWED_PROJECT_EXTENSIONS | ALLOWED_ICON_EXTENSIONS):
        abort(403)
    return send_from_directory(UPLOAD_FOLDER, safe_filename)

@app.route('/hostedsite/console')
def console():
    return render_template('console.html')

@app.route('/execute', methods=['POST'])
@login_required
def execute():
    command = request.json.get('command', '')
    if not command:
        return jsonify(output="No command provided.")
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=10)
        return jsonify(output=output.decode())
    except subprocess.CalledProcessError as e:
        return jsonify(output=e.output.decode())
    except Exception as e:
        return jsonify(output=str(e))

# --- New section: Serve raw template HTML as plain text (source view) ---

@app.route('/view-template/<template_name>')
def view_template(template_name):
    allowed_templates = {'index.html', 'host.html', 'console.html'}
    if template_name not in allowed_templates:
        abort(404)
    template_path = os.path.join(app.root_path, 'templates', template_name)
    if not os.path.exists(template_path):
        abort(404)
    with open(template_path, 'r', encoding='utf-8') as f:
        code = f.read()
    # Display as plain text
    return Response(code, mimetype='text/plain')

# --- Optional: explicit /view/index, /view/host, /view/console for rendered templates ---

@app.route('/view/index')
def view_index():
    return render_template('index.html')

@app.route('/view/host')
def view_host_page():
    return render_template('host.html')

@app.route('/view/console')
def view_console_page():
    return render_template('console.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html', error=error), 404

@app.errorhandler(413)
def file_too_large(error):
    return render_template('413.html', error=error), 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
