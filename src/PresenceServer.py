from NetworkingClient import NetworkingClient
import sys
import re
import time

# This is a small sample of how to use presence in a client server solution <br />
class PresenceServer(object):
    def __init__(self):
        # Username is the first part of the JID it will use
        self.username = 'server'
        # Domain name of the server
        self.domain = 'YLGW036484'
        # Port number to connect to, 5222 is default
        self.port = 5222

        # Making a new instance of the NetworkingClient, providing it with domain and port
        self.network = NetworkingClient(server=self.domain, port=self.port)
        # starts a connection, and only continues if it is on a tls encrypted line
        if self.network.connect() == 'tls':
            # checks if authenticated with sasl authentication
            if 'sasl' == self.network.authenticate(username=self.username, domain=self.domain, secret='1234', resource='Test Server'):
                # changes subscription behaviour, notice the lack of ()
                # this is important since we do not want to invoke it yet
                self.network.set_subscription_validator(self.server_subscription_acceptance)
                self.network.set_subscription_validator("lol")
        else:
            # if no tls connection could be made, print a message and exit the program
            print 'could not open tls connection'
            sys.exit(0)

    # It must take 1 parameter which is the jid the request comes from
    def server_subscription_acceptance(self, jid):
        # server only subscribes back to people named test1 and test 2<br />
        # to accomplish this, first make a regex search to find them.
        # since it will be a Jabber ID instance, we have to stringfy it. <br />
        # This means that the server will only know the status from test1 and test2.<br />
        # Therefore it will only send subscriber information to those 2.
        # But both test1, test2, test3 and test4 will know of the serves status
        match = re.search('test[1^2]', str(jid))
        # if a match is found we allow the subscription and subscribe back
        if match:
            return (True, True)
        else:
            # if a match is not found, we allow the subscription but do not subscribe back
            return (True, False)

if __name__ == '__main__':
    server = PresenceServer()
    # waits until it has 2 subscribers
    while len(server.network.get_subscriptions_from_self()) != 2:
        # using this to avoid excessive cpu use while doing nothing
        time.sleep(0.1)
    server.network.send_presence(username='test1', domain='YLGW036484', typ="TRYING STUFF LOL")
    time.sleep(2)
    # sending a message to everyone that the server has a subscription to
    server.network.send_mass_messages(server.network.get_subscriptions_from_self(), server.network.id(), 'test message')
    # raw_input is just here to keep the program running
    raw_input('end')
