from dnslib.resolver import ProxyResolver
from dnslib.server import BaseResolver
from dnslib import RR, QTYPE, A

HOST_IP = '10.0.0.6'     # Your local IP
DOMAIN = 'apps.lan.'     # Note the trailing dot — required for full FQDN

class AppsLanResolver(BaseResolver):
    def __init__(self):
        # Use Google's public DNS server as fallback for all other domains
        self.fallback = ProxyResolver("8.8.8.8")

    def resolve(self, request, handler):
        qname = request.q.qname  # The domain name being queried
        reply = request.reply()

        if str(qname) == DOMAIN:
            reply.add_answer(RR(
                rname=qname,
                rtype=QTYPE.A,
                rclass=1,
                ttl=300,
                rdata=A(HOST_IP)
            ))
            return reply
        else:
            # Forward all other queries to real DNS server (e.g. google.com)
            return self.fallback.resolve(request, handler)
