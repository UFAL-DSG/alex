#import sys
#import urlparse
#from BaseHTTPServer import HTTPServer
#from SimpleHTTPServer import SimpleHTTPRequestHandler
#
#
#class WSRouterHTTPHandler(SimpleHTTPRequestHandler):
#    def do_GET(self):
#       parsedParams = urlparse.urlparse(self.path)
#       queryParsed = urlparse.parse_qs(parsedParams.query)
#
#       # request is either for a file to be served up or our test
#       if parsedParams.path == "/test":
#          self.processMyRequest(queryParsed)
#       else:
#          # Default to serve up a local file

from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory

import sys
import time

from twisted.python import log
from twisted.internet import reactor

from alex.components.hub.wsio_messages_pb2 import WSRouterRequestProto, WSRouterRoutingResponseProto, PingProto


class WSRouterServerProtocol(WebSocketServerProtocol):

    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            msg = WSRouterRequestProto()
            msg.ParseFromString(payload)

            if msg.type == WSRouterRequestProto.PING:
                self.factory.ping(msg.ping.addr, msg.ping.key, msg.ping.status)
            elif msg.type == WSRouterRequestProto.ROUTE_REQUEST:
                addr, key = self.factory.route_request()

                resp = WSRouterRoutingResponseProto()
                resp.addr = addr
                resp.key = key

                self.sendMessage(resp.SerializeToString(), True)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


class WSRouterServerFactory(WebSocketServerFactory):
    def __init__(self, addr, port, entry_timeout):
        super(WSRouterServerFactory, self).__init__(url="ws://%s:%d" % (addr, port), debug=False)
        self.protocol = WSRouterServerProtocol
        self.instances = {}
        self.timestamps = {}
        self.entry_timeout = entry_timeout

    def route_request(self):
        print self.instances
        for addr in self.instances.keys():
            key, status = self.instances[addr]
            entry_is_time_outed = time.time() - self.timestamps[addr] > self.entry_timeout

            if status == PingProto.AVAILABLE and not entry_is_time_outed:
                del self.instances[addr]
                return addr, key
            elif entry_is_time_outed:
                del self.instances[addr]
                del self.timestamps[addr]

        return "", ""

    def ping(self, addr, key, status):
        self.instances[addr] = (key, status)
        self.timestamps[addr] = time.time()

        print 'got ping', addr, key, status

#
#

class WSRouter(object):
    def __init__(self, addr, port, entry_timeout):
        self.addr = addr
        self.port = port
        self.entry_timeout = entry_timeout

    def run(self):
        factory = WSRouterServerFactory(self.addr, self.port, self.entry_timeout)
        log.startLogging(sys.stdout)

        reactor.listenTCP(self.port, factory)
        reactor.run()


