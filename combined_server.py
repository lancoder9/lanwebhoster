from flask import Flask, render_template
from threading import Thread
from dnslib.server import DNSServer, BaseResolver, DNSLogger
from dnslib import RR, QTYPE, A

HOST_IP = '10.0.0.6'
DOMAIN = 'apps.lan.'

app = Flask(__name__, template_folder='templates')

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/host')
def host_page():
    return render_template("host.html")

@app.route('/hostedsite/console')
def console_page():
    return render_template("console.html")

class AppsLanResolver(BaseResolver):
    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        if str(qname) == DOMAIN:
            reply.add_answer(RR(rname=qname, rtype=QTYPE.A, rclass=1, ttl=300, rdata=A(HOST_IP)))
        return reply

def run_dns_server():
    resolver = AppsLanResolver()
    logger = DNSLogger(prefix=False)
    server = DNSServer(resolver, port=53, address='0.0.0.0', logger=logger)
    server.start_thread()
    print(f"DNS server started: {DOMAIN} → {HOST_IP}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("DNS server stopped")

def run_flask_app():
    print("Starting Flask app on port 9316...")
    app.run(host='0.0.0.0', port=9316)

if __name__ == "__main__":
    dns_thread = Thread(target=run_dns_server, daemon=True)
    dns_thread.start()
    run_flask_app()
