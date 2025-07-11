from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, flash, url_for, abort, Response
import os
import subprocess
import uuid
import socket
from threading import Thread
from werkzeug.utils import secure_filename
from functools import wraps

# Flask setup
app = Flask(__name__)
app.secret_key = 'super_secret_key'

UPLOAD_FOLDER = 'static/hosted'
ALLOWED_PROJECT_EXTENSIONS = {'html', 'zip'}
ALLOWED_ICON_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'ico'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# DNS setup
from dnslib.server import DNSServer, BaseResolver, DNSLogger
from dnslib import RR, QTYPE, A, DNSRecord

HOST_IP = '10.0.0.6'
DOMAIN = 'apps.lan.'

# --- DNS Resolver ---
class ProxyResolver:
    def __init__(self, forward_ip='1.1.1.1', forward_port=53):
        self.forward_ip = forward_ip
        self.forward_port = forward_port

    def resolve(self, request, handler):
        data = request.pack()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        sock.sendto(data, (self.forward_ip, self.forward_port))
        try:
            data, _ = sock.recvfrom(4096)
            return DNSRecord.parse(data)
        except socket.timeout:
            return request.reply()

class AppsLanResolver(BaseResolver):
    def __init__(self):
        self.forwarder = ProxyResolver()

    def resolve(self, request, handler):
        qname = request.q.qname
        reply = request.reply()
        if str(qname) == DOMAIN:
            reply.add_answer(RR(qname, QTYPE.A, rclass=1, ttl=300, rdata=A(HOST_IP)))
        else:
            return self.forwarder.resolve(request, handler)
        return reply

def run_dns_server():
    resolver = AppsLanResolver()
    logger = DNSLogger(prefix=False)
    server = DNSServer(resolver, port=53, address='0.0.0.0', logger=logger)
    server.start_thread()
    print(f"[DNS] apps.lan → {HOST_IP} (forwarding others to 1.1.1.1)")

# --- Helper Functions ---
def allowed_file(filename, allowed_exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_exts

def sanitize_filename(filename):
    return secure_filename(filename)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated

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

# --- Routes ---
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
                        continue
                    name, icon, file = lines
                    icon_path = os.path.join(UPLOAD_FOLDER, icon)
                    file_path = os.path.join(UPLOAD_FOLDER, file)
                    if os.path.exists(icon_path) and os.path.exists(file_path):
                        entries.append({'name': name, 'icon': icon, 'file': file})
                    else:
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

        if not projname:
            error = "Project name is required."
        elif any(projname == entry['name'] for entry in get_projects()):
            error = "A project with this name already exists."
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

                with open(os.path.join(UPLOAD_FOLDER, f"{proj_id}.meta"), 'w') as f:
                    f.write(f"{projname}\n{icon_filename}\n{proj_filename}")
                message = "Project uploaded successfully!"
            except Exception as e:
                error = f"Upload failed: {str(e)}"
    return render_template('host.html', message=message, error=error)

@app.route('/hostedsite/<path:filename>')
def hostedsite(filename):
    safe_filename = sanitize_filename(filename)
    allowed = any(
        safe_filename == entry['icon'] or safe_filename == entry['file']
        for entry in get_projects()
    )
    if not allowed:
        abort(404)
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
    return Response(code, mimetype='text/plain')

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

# --- Launch ---
if __name__ == '__main__':
    Thread(target=run_dns_server, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
