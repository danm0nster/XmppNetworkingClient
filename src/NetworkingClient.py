import xmpp
import time
import threading
import Queue


class NetworkingClient(object):
    """ Class for interacting with the xmpp networking

    Each instance of this object will hold the connection to one xmpp server

    """
    def __init__(self, server=None, port=5222):
        self.server = server
        self.port = port
        self.jid = None
        self.secret = None
        self.client = xmpp.Client
        self.messages = Queue.Queue()
        self.iq_handler = None
        self._pres_manager = None
        self._roster = None

    def authenticate(self, jid=None, username=None, domain=None, resource=None, secret=None):
        """ Authenticates to the network

        Successful authentication to the xmpp server is needed before you can interact
        with others on the network.
        It will try sasl authentication first, if this fails it tries a mix of digest, 0k and plain

        Args:
            jid(JID): The full jid you want to log in with, if this is specified username, domain and resource is not needed
            username(string): username of the jid, redundant if jid parameter is set
            domain(string): domain of the jid, redundant if jid parameter is set
            resource(string): the resource you want to use, optional only needed if you have multiple entities sharing a jid
            secret(string): password for the given jid

        Return:
            string: 'sasl', 'fallback' or None if it fails

        """
        if jid is not None:
            self.jid = jid
        else:
            self.jid = xmpp.JID(node=username, domain=domain, resource=resource)
            self.secret = secret

        if self.jid is not None:
            auth = self.client.auth(self.jid.getNode(), self.secret, self.jid.getResource())
            if not auth:
                return -1
            else:
                # initializes for use after auth
                self.client.sendInitPresence()
                self._register_handlers()
                self._start_listening()
                if auth == 'sasl':
                    return auth
                else:
                    return 'fallback'

    def connect(self):
        """ Connects to the xmpp network

        It will try to make a secure channel using tls first. If this fails it will make a regular tcp connection

        Returns:
            string: 'tls', 'tcp' or None depending on what connection type succeeded

        """
        if self.server is not None:
            # TODO might want to give client debug flag option
            self.client = xmpp.Client(server=self.server, port=self.port, debug=[])
            con = self.client.connect(server=(self.server, self.port))

            # making helper classes, order is relevant, since roster is used by the others
            self._roster = self._RosterManager(self.client)
            self.iq_handler = self._IQHandler(self._roster, self.client)
            self._pres_manager = self._PresenceManager(self._roster, self.client)
            return con

    def _register_handlers(self):
        self.client.RegisterHandler("message", self._on_message)
        self.client.RegisterHandler('presence', self._pres_manager._on_presence)
        self.client.RegisterHandler('iq', self.iq_handler._on_iq)

    def disconnect(self):
        """Disconnects from the network

        It will sleep for 1 second before calling for the disconnect, due to
        compatibility with older xmpp servers
        """
        self.send_presence(typ=u'FlagOffline')
        time.sleep(1)
        self.client.disconnect()

    # TODO time-to-live might be a nice feature
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

    def send_mass_messages(self, recipient_list, sender, message="", subject=""):
        """ Sends a message to many recipients

        Sends a message to many recipients given a list of valid jid elements

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

    def id(self):
        """ Returns the jid

        Access to the jid you are currently logged in as

        Returns:
            jid: jid instance if it has been set, otherwise None
        """
        return str(self.jid)

    def _blocking_listen(self, timeout=1.0):
        while True:
            time.sleep(0.01)
            self.client.Process(timeout)

    def _start_listening(self):
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
            Message: returns a message, None if there are no messages
        """
        try:
            result = self.messages.get()
        except Queue.Empty:
            return None
        else:
            return Message(body=result.getBody(), subject=result.getBody(), sender=result.getFrom())

    def send_presence(self, typ=None, jid=None, username=None, domain=None):
        """ Sends a presence to a specified user or everyone in roster that has a subscription for it

            If jid is specified username and domain is not used. If jid is not specified,
            it sends to username + domain combination.

            If typ is not defined it sends an empty presence.

            Args:
                typ(string): The type of presence
                jid(JID): Jabber ID to send to, if given username + domain is not used
                username(string): username of jid to send presence to, not needed if jid is specified
                domain(string): domain of jid to send presence to, not needed if jid is specified
        """
        if jid is not None:
            self.client.send(xmpp.Presence(jid, typ))
        elif username is not None and domain is not None:
            self.client.send(xmpp.Presence(xmpp.JID(node=username, domain=domain), typ))
        else:
            for jid in self.get_subscriptions_to_self():
                self.client.send(xmpp.Presence(jid, typ))

    # ################### Roster method callers ###################
    # Methods here calls other methods in RosterManager, this is to simplify how users use the this

    def check_if_online(self, jid):
        """ Checks if a given jid in your roster is online

        Args:
            jid(jid): Jabber ID you want to check on

        Returns:
            bool: True if online and in roster, False otherwise
        """
        return self._roster.check_if_online(jid)

    def get_subscriptions_to_self(self):
        """ Returns a list of subscriptions to self

        This is the list of clients that wants to push messages to you

        Returns:
            list: list of subscriptions to self
        """
        return self._roster.get_my_subscribers()
        return self._roster.get_my_subscribers()

    def get_subscriptions_from_self(self):
        """ Returns a list of subscription from self

        This is the list of clients you want to push to

        Returns:
            list: list of subscriptions from self
        """
        return self._roster.get_my_subscriptions()

    def subscribe(self, jid=None, username=None, domain=None):
        """ Subscribes to the given Jabber ID

        If the other user allows it, you will be subscribed to their online presence,
        This means that when they are online you will have them in your roster.
        You can push messages to anyone who is in your roster and online.

        If jid is given username and domain will not be used.
        If no jid is provided it will use the username and domain given.

        Args:
            jid(JID): If given will send subscription to this Jabber ID
            username(string): Used together with domain to send subscription
            domain(string) Used together with username to send subscription
        """
        return self._roster.subscribe(jid=jid, username=username, domain=domain)

    def unsubscribe(self, jid=None, username=None, domain=None):
        """ Unsubscribes to the given Jabber ID

        If jid is given username and domain will not be used.
        If no jid is provided it will use the username and domain given.

        Args:
            jid(JID): If given will send unsubscription to this Jabber ID
            username(string): Used together with domain to send unsubscription
            domain(string) Used together with username to send unsubscription
        """
        if jid is not None:
            self._pres_manager.flag_offline(jid)
        elif username is not None and domain is not None:
            self._pres_manager.flag_offline(xmpp.JID(node=username, domain=domain))
        self._roster.unsubscribe(jid=jid, username=username, domain=domain)

    # internal class for handling the roster
    class _RosterManager(object):
        def __init__(self, client):
            # the total roster is every subscription, including people who are offline
            self._total_roster = {}
            self._pending = {}
            # subset of total roster, everyone who is online, sorted by type of connection
            self._online_roster = {'to': [], 'from': [], 'both': []}
            self.client = client

        # appends a given jid to the total roster
        def _append_to_total(self, jid, subscription_type):
            self._total_roster[jid] = subscription_type
            # if jid is in pending, delete it from there and add to online
            if jid in self._pending:
                self._online_roster[subscription_type] = jid
                try:
                    del self._pending[jid]
                except KeyError:
                    pass

        # When contact goes online, add it to the online roster
        def _on_contact_online(self, jid):
            # if statement here in case presence is received before the roster update IQ
            if jid in self._total_roster:
                self._online_roster[self._total_roster[jid]].append(jid)
            else:
                self._pending[jid] = None

        def check_if_online(self, jid):
            temp_roster_list = []
            temp_roster_list.extend(self._online_roster['to'])
            temp_roster_list.extend(self._online_roster['from'])
            temp_roster_list.extend(self._online_roster['both'])
            if jid in temp_roster_list:
                return True
            else:
                return False

        def get_my_subscribers(self):
            result_list = []
            result_list.extend(self._online_roster['from'])
            result_list.extend(self._online_roster['both'])
            return result_list

        def get_my_subscriptions(self):
            result_list = []
            result_list.extend(self._online_roster['to'])
            result_list.extend(self._online_roster['both'])
            return result_list

        # used for removing a jid from memory when unsubscribed
        def _remove(self, jid):
            try:
                jid = jid.getStripped()
            except AttributeError:
                pass
            if jid in self._online_roster['to']:
                self._online_roster['to'].remove(jid)
            if jid in self._online_roster['from']:
                self._online_roster['from'].remove(jid)
            if jid in self._online_roster['both']:
                self._online_roster['both'].remove(jid)

        def unsubscribe(self, username=None, domain=None, jid=None):
            if jid is not None:
                self.client.send(xmpp.Presence(jid, 'unsubscribe'))
            elif username is not None and domain is not None:
                self.client.send(xmpp.Presence(xmpp.JID(node=username, domain=domain), 'unsubscribe'))

        def subscribe(self, jid=None, username=None, domain=None):
            if jid is not None:
                self.client.send(xmpp.Presence(jid, 'subscribe'))
            else:
                self.client.send(xmpp.Presence(xmpp.JID(node=username, domain=domain), 'subscribe'))

    # ################### Presence method callers ###################
    # Methods here calls other methods in PresenceManager, this is to simplify how users use the this

    def set_subscription_validator(self, function):
        """ Sets the method to be called for subscription validation

        The validator function needs to return a tuple in the format of (bool, bool)
        Where the first bool determines if the subscription will be allowed.
        The second bool will determine if a subscription will be send back to sender.

        Args:
            function(function object): The function to be called on new subscriptions
        """
        self._pres_manager.set_subscription_validator(function)

    def set_disconnect_handler(self, function):
        """ Given a function, set it's as the disconnect handler

        This function will be called whenever someone you are subscribed to disconnects.
        If someone is subscribed to you, but you are not subscribed to them, and they disconnect this function
        will not be called.

        If someone shuts down cleanly by calling the disconnect method. The disconnect function will not be called.

        Args:
            function(function): The function to be called when a disconnect happens
        """
        self._pres_manager.set_disconnect_handler(function)

    class _PresenceManager(object):
        """ Internal class for handing presence
        """
        def __init__(self, roster, client):
            self.roster = roster
            self.client = client
            self._subscription_validator = self._subscription_validator_func
            self._disconnect_handler = None
            self._offline_flags = {}

        def _on_presence(self, dispatcher, pres):
            print pres
            name = pres.getFrom()
            name = name.getStripped()

            if pres.getType() is None:
                self.roster._on_contact_online(name)
            elif pres.getType() == 'subscribe':
                # tries the given validator function, if it isn't a function it will revert to the default function
                try:
                    validator = self._subscription_validator(name)
                except TypeError:
                    validator = self._subscription_validator_func(name)
                if validator[0] is True:
                    self.client.send(xmpp.Presence(typ='subscribed', to=name))
                if validator[1] is True:
                    self.client.send(xmpp.Presence(typ='subscribe', to=name))

            elif pres.getType() == 'unsubscribe':
                self.client.send(xmpp.Presence(typ='unsubscribed', to=name))

            elif pres.getType() == 'FlagOffline':
                self._offline_flags[name] = None

            elif pres.getType() == 'unavailable':
                # Remove name from online roster
                try:
                    self.roster._remove(name)
                except ValueError:
                    pass
                # check if we have received a flag for clean disconnect
                if name in self._offline_flags:
                    try:
                        self._offline_flags.pop(name)
                    except KeyError:
                        pass
                else:
                    # if not try to call disconnect handler
                    try:
                        self._disconnect_handler()
                    except TypeError:
                        pass

            elif pres.getType() == 'unsubscribed':
                try:
                    self.roster._remove(name)
                except ValueError:
                    pass

        def set_disconnect_handler(self, function):
            self._disconnect_handler = function

        def flag_offline(self, jid):
            jid = jid.lower()
            self._offline_flags[jid] = None

        def _subscription_validator_func(self, jid):
            return (True, True)

        def set_subscription_validator(self, function):
            self._subscription_validator = function

    class _IQHandler(object):
        """ Internal class for limited handling of IQ stanza's
        """
        def __init__(self, roster, client):
            self.roster = roster
            self.client = client

        def _on_iq(self, dispatcher, iq):
            # gets all item elements from the query element
            items = iq.getTag('query').getTags('item')
            # then iterates over the items
            for item in items:
                jid = item.getAttr('jid')
                if item.getAttr('subscription') == 'both':
                    self.roster._append_to_total(jid, 'both')
                elif item.getAttr('subscription') == 'to':
                    self.roster._append_to_total(jid, 'to')
                elif item.getAttr('subscription') == 'from':
                    self.roster._append_to_total(jid, 'from')
            raise xmpp.NodeProcessed  # <-- must be there for underlying control of flow


class Message(object):
    """ Message from the network

    For making network messages from the network.

    Attributes:
        body(string): The body of the message
        subject(string): The subject of the message
        Sender(JID): The Jabber ID of who sent the message
    """
    def __init__(self, body="", subject="", sender=None):
        self.body = body
        self.subject = subject
        self.sender = sender
