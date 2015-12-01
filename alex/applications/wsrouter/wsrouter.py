import sys
import time

from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory
from twisted.python import log
from twisted.internet import reactor

from alex.components.hub.wsio_messages_pb2 import WSRouterRequestProto, WSRouterRoutingResponseProto, PingProto


class WSRouterServerFactory(WebSocketServerFactory):
    def __init__(self, addr, port, entry_timeout):
        super(WSRouterServerFactory, self).__init__(url="ws://%s:%d" % (addr, port), debug=False)
        self.protocol = WSRouterServerProtocol
        self.instances = {}
        self.timestamps = {}
        self.entry_timeout = entry_timeout

    def route_request(self):
        print 'ROUTING', 'current instances:', self.instances
        for addr in self.instances.keys():
            key, status = self.instances[addr]
            entry_is_time_outed = time.time() - self.timestamps[addr] > self.entry_timeout

            if status == PingProto.AVAILABLE and not entry_is_time_outed:
                del self.instances[addr]
                return addr, key
            elif entry_is_time_outed:
                del self.instances[addr]
                del self.timestamps[addr]

        return "", ""  # In case no Alex is available.

    def ping(self, addr, key, status):
        self.instances[addr] = (key, status)
        self.timestamps[addr] = time.time()

        print '  > Got ping from', addr, key, 'with status', status


class WSRouterServerProtocol(WebSocketServerProtocol):
    """Handles messages sent by Alex instances and the clients."""
    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        if isBinary:
            self._process_message(payload)

    def _process_message(self, payload):
        msg = WSRouterRequestProto()
        msg.ParseFromString(payload)
        if msg.type == WSRouterRequestProto.PING:
            # Ping was received, update the list of available Alex instances.
            self.factory.ping(msg.ping.addr, msg.ping.key, msg.ping.status)
        elif msg.type == WSRouterRequestProto.ROUTE_REQUEST:
            # The message was a routing request. Find an available Alex and send back its address.
            addr, key = self.factory.route_request()

            resp = WSRouterRoutingResponseProto()
            resp.addr = addr
            resp.key = key
            self.sendMessage(resp.SerializeToString(), True)

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


class WSRouter(object):
    """Takes care of providing clients with the address of an available Alex instance."""
    def __init__(self, addr, port, entry_timeout):
        self.addr = addr
        self.port = port
        self.entry_timeout = entry_timeout

    def run(self):
        factory = WSRouterServerFactory(self.addr, self.port, self.entry_timeout)
        log.startLogging(sys.stdout)

        reactor.listenTCP(self.port, factory)
        reactor.run()


