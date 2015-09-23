from NetworkingClient import NetworkingClient
import sys
import time


class PresenceClient(object):
    def __init__(self):
        # Username is the first part of the JID it will use
        self.username = 'test1'
        # Domain name of the server
        self.domain = 'YLGW036487'
        # Port number to connect to, 5222 is default
        self.port = 5222
        # server to connect to
        self.server = 'server@YLGW036487'

        # Making a new instance of the NetworkingClient, providing it with domain and port
        self.network = NetworkingClient(server=self.domain, port=self.port)
        # starts a connection, and only continues if it is on a tls encrypted line
        if self.network.connect() == 'tls':
            # checks if authenticated with sasl authentication
            if 'sasl' == self.network.authenticate(username=self.username, domain=self.domain, secret='1234', resource='Test Server'):
                pass
                # On the client side we just use the default subscription handler
                # which accepts all subscriptions and subscribes back to the subscriber
                # it will use the default subscription handler if we don't specify any<br /><br />

                # Here we set the disconnect handler on the client side, remember not to invoke it with ()
                self.network.set_disconnect_handler(self.disconect_handler)
        else:
            # if no tls connection could be made, print a message and exit the program
            print 'could not open tls connection'
            sys.exit(0)

    # As with the server it is for handling unexpected disconnects from people in your roster
    def disconect_handler(self):
        # For this demonstration it just prints out a message. <br />
        # But you could make a client try to reconnect or in other ways handle that it has no connection
        print 'Server disconnected'

if __name__ == '__main__':
    client = PresenceClient()
    # sends a subscription to the server
    print 'sending subscription request'
    client.network.subscribe(jid=client.server)
    # waits for a message from the server
    while not client.network.check_for_messages():
        # using this to avoid excessive cpu use while doing nothing
        time.sleep(0.1)
    # prints the message from the server
    print 'got message: ', client.network.pop_message().body
    # after receiving a message from the server we will unsubscribe from the server using it's Jabber ID. <br />
    client.network.unsubscribe(jid=client.server)
    print 'unsubscribed'
    # To test the disconnect handler on the server side, make the client wait some time, and close it down while it's waiting
    time.sleep(40)
    print 'disconnecting'
    client.network.disconnect()
    # raw_input is just here to keep the program running
    raw_input('end')
