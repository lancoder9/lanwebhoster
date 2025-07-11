from dnslib.server import DNSServer, DNSHandler, BaseResolver, DNSLogger
from dnslib import RR, QTYPE, A

HOST_IP = '10.0.0.6'  # Your LAN IP
DOMAIN = 'apps.lan.'

class AppsLanResolver(BaseResolver):
    def resolve(self, request, handler):
        reply = request.reply()
        qname = request.q.qname
        if str(qname) == DOMAIN:
            reply.add_answer(RR(rname=qname, rtype=QTYPE.A, rclass=1, ttl=300, rdata=A(HOST_IP)))
        return reply

resolver = AppsLanResolver()
logger = DNSLogger(prefix=False)
server = DNSServer(resolver, port=53, address='0.0.0.0', logger=logger)
server.start_thread()

print(f'DNS server running - resolving {DOMAIN} to {HOST_IP}')
print('Press Ctrl+C to quit')

try:
    while True:
        pass
except KeyboardInterrupt:
    print('DNS Server stopped')
