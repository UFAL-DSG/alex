from autobahn.twisted.websocket import WebSocketClientProtocol, \
    WebSocketClientFactory
import sys
sys.path.insert(0, '../../../')
from alex.utils.audio import load_wav
from alex.utils import various
from wsio_messages_pb2 import ClientToAlex
import time


class MyClientProtocol(WebSocketClientProtocol):
    cfg = {
        'Audio': {
            'sample_rate': 16000,
            'samples_per_frame': 256,
        }
    }

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    def onOpen(self):
        print("WebSocket connection open.")
        time.sleep(2.0)
        def hello():
            filename = sys.argv[1]
            wav = load_wav(self.cfg, filename)
            wav = various.split_to_bins(
                wav, 2 * self.cfg['Audio']['samples_per_frame'])

            # frame by frame send it
            buff = ""
            for i, frame in enumerate(wav):
                buff += frame

                if i % 1 == 0 and buff:
                    msg = ClientToAlex()
                    msg.speech.body = buff
                    self.sendMessage(msg.SerializeToString(), isBinary=True)

                    buff = ""

                    time.sleep(1 / 16000)



            # send some silence so that VAD recognizes end of recording
            #for _ in range(20):
            #    x += b"\x00\x00" * self.cfg['Audio']['samples_per_frame']

            print 'msg ready'


            #self.factory.reactor.callLater(1, hello)

        # start sending messages every second ..
        hello()

    def onMessage(self, payload, isBinary):
        print 'x'
        if isBinary:
            print("Binary message received: {0} bytes".format(len(payload)))
        else:
            print("Text message received: {0}".format(payload.decode('utf8')))

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


if __name__ == '__main__':

    import sys

    from twisted.python import log
    from twisted.internet import reactor

    log.startLogging(sys.stdout)

    factory = WebSocketClientFactory("ws://localhost:9000", debug=False)
    factory.protocol = MyClientProtocol

    reactor.connectTCP("127.0.0.1", 9000, factory)
    reactor.run()