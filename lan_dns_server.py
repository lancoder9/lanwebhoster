from dnslib.server import DNSServer, BaseResolver, DNSLogger
from dnslib import RR, QTYPE, A

HOST_IP = '10.0.0.6'
DOMAIN = 'apps.lan.'

class AppsLanResolver(BaseResolver):
    def resolve(self, request, handler):
        qname = request.q.qname
        reply = request.reply()
        if str(qname) == DOMAIN:
            reply.add_answer(RR(rname=qname, rtype=QTYPE.A, rclass=1, ttl=300, rdata=A(HOST_IP)))
            return reply
        return None  # No answer for other domains

def run_dns_server():
    resolver = AppsLanResolver()
    logger = DNSLogger(prefix=False)
    # Bind to localhost only or a custom port, e.g. 5300 (non-privileged)
    server = DNSServer(resolver, port=1000, address='0.0.0.0', logger=logger)
    server.start_thread()
    print(f"DNS server running, resolving {DOMAIN} → {HOST_IP}")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("DNS server stopped")
