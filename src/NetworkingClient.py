import xmpp
import sys
import time
import threading
import multiprocessing
import Queue


class NetworkingClient(object):
    def __init__(self, server="", port=5222):
        self.server = server
        self.port = port
        self.jid = xmpp.JID
        self.secret = None
        self.client = xmpp.Client
        self.msg_handler = None
        self.listening_process = None
        self.stop_all_processes = False
        self.lock = multiprocessing.RLock()

        #### vars for blocking
        self.messages = Queue.Queue()

    # TODO check if valid jid?
    def set_credentials(self, jid=None, username=None, domain=None, resource=None, secret=None):
        """Sets the JID to be used for the class

        if given a JID it will use that, otherwise it will create a new JID from the other given parameters

        Args:
            jid (jid): jid instance to use.
            username (string): Username to create jid object.
            domain (string): Domain for the jid object.
            resource (string): Resource for the jid object.
            secret (string): password for the jid.
        """
        if jid is not None:
            self.jid = jid
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
                self._register_handlers()

    def authenticate(self):
        if self.jid is not None:
            auth = self.client.auth(self.jid.getNode(), self.secret, self.jid.getResource())
            if not auth:
                print "could not authenticate"
                sys.exit(0)
            else:
                print "authenticated using: " + auth

    def _register_handlers(self):
        self.client.RegisterHandler("message", self._on_message)

    def disconnect(self):
        """Disconnects from the network

        It will sleep for 1 second before calling for the disconnect, due to
        compatibility with older xmpp servers
        """
        # sleeping 1 sec before disconnect, this removes errors that can happen on older servers
        time.sleep(1)
        self.client.disconnect()

    # TODO timestamp/time-to-live for discarding old messages
    def send_message(self, to, sender, message="", subject=""):
        """ Sends a message

        message and subject is optional

        Args:
            to (jid): the jid of the recipient
            sender (jid): jid of who sent it
            message (string): message, defaults to the empty string
            subject (string): subject, defaults to the empty string

        Returns:
            int: -1 if unsuccessful, message id if successful
        """
        msg = xmpp.Message()
        if to is not None and to != "":
            msg.setTo(to)
            msg.setFrom(sender)
            msg.setBody(message)
            msg.setSubject(subject)
            if self.client.connected:
                return self.client.send(msg)
        return -1

    # TODO check on recipientList er en liste
    def send_mass_messages(self, recipient_list, sender, message="", subject=""):
        """ Sends a message to many recipients

        Sends a message to many recipients given a list of valid jids

        Args:
            recipient_list (list): List of recipients
            sender (jid): Where the message is from
            message (string): The message to be sent
            subject (string): The subject of the message
        """
        try:
            for s in recipient_list:
                self.send_message(to=s, sender=sender, message=message, subject=subject)
        except TypeError:
            return -1
        return 1

    # TODO might need a generic add handler method, to support building addons
    def register_message_handler(self, obj):
        self.msg_handler = obj.message_received

    def id(self):
        """ Returns the jid

        Access to the jid you are currently logged in as

        Returns:
            jid: jid instance if it has been set, otherwise None
        """
        return str(self.jid)

    def _blocking_listen(self, timeout=1.0):
        print "entering listen method"
        # TODO maybe remove busy waiting
        while True:
            self.client.Process(timeout)

    def blocking_listen_start(self):
        print "spawning thread"
        thread = threading.Thread(target=self._blocking_listen)
        thread.setDaemon(True)
        thread.start()

    def _on_message(self, dispatcher, msg):
        self.messages.put(msg)

    def check_for_messages(self):
        """Checks for messages

        Returns:
            bool: True if there are messages, False if there are no messages left
        """
        result = not self.messages.empty()
        return result

    def pop_message(self):
        """returns the oldest message

        pops a message from the underlying FIFO queue, thread safe.

        Returns:
            string: returns a message, None if there are no messages
        """
        try:
            result = self.messages.get()
        except Queue.Empty:
            return None
        else:
            return result
