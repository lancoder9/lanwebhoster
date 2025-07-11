from flask import Flask, render_template
from threading import Thread
from dnslib.server import DNSServer, BaseResolver, DNSLogger
from dnslib import RR, QTYPE, A
import socket

HOST_IP = '10.0.0.6'
DOMAIN = 'apps.lan.'

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/host')
def host():
    return render_template('host.html')

@app.route('/hostedsite/console')
def console():
    return render_template('console.html')


# Manual ProxyResolver fallback if dnslib.resolver.ProxyResolver not available
class ProxyResolver:
    def __init__(self, forward_ip='8.8.8.8', forward_port=53):
        self.forward_ip = forward_ip
        self.forward_port = forward_port

    def resolve(self, request, handler):
        data = request.pack()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(3)
        sock.sendto(data, (self.forward_ip, self.forward_port))
        try:
            data, _ = sock.recvfrom(4096)
            reply = DNSRecord.parse(data)
            return reply
        except socket.timeout:
            return request.reply()


class AppsLanResolver(BaseResolver):
    def __init__(self):
        self.forwarder = ProxyResolver("1.1.1.1")  # Cloudflare DNS

    def resolve(self, request, handler):
        qname = request.q.qname
        reply = request.reply()
        if str(qname) == DOMAIN:
            reply.add_answer(RR(rname=qname, rtype=QTYPE.A, rclass=1, ttl=300, rdata=A(HOST_IP)))
            return reply
        else:
            return self.forwarder.resolve(request, handler)


def run_dns_server():
    resolver = AppsLanResolver()
    logger = DNSLogger(prefix=False)
    server = DNSServer(resolver, port=53, address='0.0.0.0', logger=logger)
    server.start_thread()
    print(f"[DNS] apps.lan → {HOST_IP} (forwarding others to 1.1.1.1)")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("DNS server stopped")


def run_flask_server():
    print("[WEB] Flask server running at http://apps.lan:9316")
    app.run(host='0.0.0.0', port=9316)


if __name__ == "__main__":
    dns_thread = Thread(target=run_dns_server, daemon=True)
    dns_thread.start()
    run_flask_server()

