import xmpp
import sys
import time
import multiprocessing


class NetworkingClient:
    def __init__(self, server="", port=5222):
        self.server = server
        self.port = port
        self.jid = xmpp.JID
        self.secret = None
        self.client = xmpp.Client
        self.msg_handler = None
        self.listening_process = None
        self.stop_all_processes = multiprocessing.Value('i', 0)
        self.lock = multiprocessing.Lock()

    def set_credentials(self, jid=None, username=None, domain=None, resource=None, secret=None):
        if jid is not None:
            pass
        else:
            self.jid = xmpp.JID(node=username, domain=domain, resource=resource)
            self.secret = secret

    # connects and initialize the client for business
    # does it in multiple steps:
    # 1. tcp connection
    # 2. xmpp user authentication
    # 3. sends presence to server
    # 4. registers event handlers
    def connect(self):
        # step 1
        if self.server is not None:
            # TODO client debug flag
            # port?
            self.client = xmpp.Client(server=self.server, port=self.port, debug=[])
            con = self.client.connect(server=(self.server, self.port))
            if not con:
                # TODO exception
                print "No connection made", con
                sys.exit(0)
            else:
                print "connected with: " + con
                # step 2
                self.authenticate()
                # step 3
                self.client.sendInitPresence()
                # step 4
                self.register_handlers()

    def authenticate(self):
        if self.jid is not None:
            auth = self.client.auth(self.jid.getNode(), self.secret, self.jid.getResource())
            if not auth:
                print "could not authenticate"
                sys.exit(0)
            else:
                print "authenticated using: " + auth

    def register_handlers(self):
        print "handler registered"
        self.client.RegisterHandler("message", self.on_message)

    def disconnect(self):
        # Stop any spawned listener threads
        self.lock.acquire(block=True)
        self.stop_all_processes.value = 1
        self.lock.release()
        # sleeping 1 sec before disconnect, this removes errors that can happen on older servers
        time.sleep(1)
        self.client.disconnect()
        print "disconnected"
        # Forcing processes to close if not yet terminated
        #self.listening_process.terminate()

    # TODO timestamp/time-to-live for discarding old messages
    def send_message(self, to, message="", subject=""):
        msg = xmpp.Message()
        if to is not None and to != "":
            msg.setTo(to)
            msg.setBody(message)
            msg.setSubject(subject)
            if self.client.connected:
                self.client.send(msg)
        else:
            # TODO exception on wrong to parameter
            pass

    # raises TypeError exception if handlers aren't setup properly
    def on_message(self, client, msg):
        # TODO checking message type and dealing with them, f.x. if msg.type == "chat" do x
        self.msg_handler(msg, 1234)

    # TODO might need a generic add handler method, to support building addons
    def register_message_handler(self, function, *args):
        self.msg_handler = function

    def _listen(self, timeout=1):
        self.lock.acquire(block=True)
        stopped = self.stop_all_processes.value
        self.lock.release()
        while stopped is not 1:
            self.client.Process(timeout)
            time.sleep(0.3)
            self.lock.acquire(block=True)
            stopped = self.stop_all_processes.value
            self.lock.release()
            print "Listening loop, stop signal is: ", stopped

    def start_listening(self):
        self.listening_process = multiprocessing.Process(target=self._listen)
        print "preparing to spawn listening process, current pid: ", str(self.listening_process.pid)
        self.listening_process.start()
        print "process started, current pid: ", str(self.listening_process.pid)
