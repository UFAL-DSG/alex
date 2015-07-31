import sys

from twisted.python import log
from twisted.internet import reactor
from autobahn.twisted.websocket import WebSocketClientProtocol, WebSocketClientFactory

from wsrouter_protos_pb2 import WSRouterRequestProto, WSRouterRoutingResponseProto


class MyClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")

        #def hello():
        #    self.sendMessage(u"Hello, world!".encode('utf8'))
        #    self.sendMessage(b"\x00\x01\x03\x04", isBinary=True)
            #self.factory.reactor.callLater(1, hello)

        # start sending messages every second ..
        #hello()

        msg = WSRouterRequestProto()
        msg.type = WSRouterRequestProto.ROUTE_REQUEST
        self.sendMessage(msg.SerializeToString(), True)
        print('sent')

    def onMessage(self, payload, isBinary):
        if isBinary:
            msg = WSRouterRoutingResponseProto()
            msg.ParseFromString(payload)
            print 'router replied:'
            print '  addr', msg.addr
            print '  key', msg.key

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))






def main():
    log.startLogging(sys.stdout)

    factory = WebSocketClientFactory("ws://localhost:9001", debug=False)
    factory.protocol = MyClientProtocol

    reactor.connectTCP("127.0.0.1", 9001, factory)
    reactor.run()



if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()

    args = parser.parse_args()

    main(**vars(args))