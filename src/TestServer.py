from NetworkingClient import NetworkingClient
import threading
import random
import time

class TestServer:
    def __init__(self):
        self.investor_list = []
        self.trustfund_list = []
        self.invest_trustfund_pairing = {}
        self.response_dict = {}
        self.server_state = ""
        self.lock = threading.RLock()

        self.client = NetworkingClient(server='YLGW036484', port=5222)
        self.client.set_credentials(username='server', domain='YLGW036484', secret='1234', resource='Test Server')
        self.client.connect()
        self.client.register_message_handler(self)
        self.client.start_listening()

    # TODO limit how far it looks for commands
    def message_received(self, msg):
        # event for investors to register on the server
        msg_body = msg.getBody()
        if msg_body.find("--register:invest") is not -1:
            self.lock.acquire()
            if msg.getFrom() not in self.investor_list:
                self.investor_list.append(msg.getFrom())
                print "adding " + str(msg.getFrom()) + " to invest list"
            self.lock.release()
            return

        # event for trust funds to register on the server
        if msg_body.find("--register:trustfund") is not -1:
            self.lock.acquire()
            if msg.getFrom() not in self.trustfund_list:
                self.trustfund_list.append(msg.getFrom())
                print "adding " + str(msg.getFrom()) + " to trust fund list"
            self.lock.release()
            return

        # event when investors sends investment
        if msg_body.find("--invest:") is not -1:
            self.lock.acquire()
            self.response_dict[msg.getFrom()] = msg_body.lstrip("--invest:")
            print "investment from :" + msg.getFrom().getNode() + " he invested: " + msg_body.lstrip("--invest:")
            if len(self.response_dict) == len(self.invest_trustfund_pairing):
                self.server_state = "investor done"
            self.lock.release()
            return

        # trust funds pay investors
        if msg_body.find("--trustfundPay:") is not -1:
            self.lock.acquire()
            self.response_dict[msg.getFrom()] = msg_body.lstrip("--trustfundPay:")
            print "trustfund payment from " + msg.getFrom().getNode() + " he paid " + msg_body.lstrip("--trustfundPay:")
            if len(self.response_dict) == len(self.invest_trustfund_pairing):
                self.server_state = "trustfund done"
            self.lock.release()
            return

    def game_round(self):
        # TODO people always play with the same people, stops pairing when 1 of the lists is done
        # pairs people up and use a dictionary to keep track of the pairs
        self.lock.acquire()
        # TODO shuffle the list
        for trustfund, investor in zip(self.trustfund_list, self.investor_list):
            self.invest_trustfund_pairing[investor] = trustfund
        self.lock.release()

        self.lock.acquire()
        # send a message to every participant of whom they are trading with
        for investor in self.invest_trustfund_pairing:
            inv = str(investor)
            tru = str(self.invest_trustfund_pairing[investor])
            reci = self.client.id()
            invStr = "--paired:"+tru
            truStr = "--paired:"+inv
            self.client.send_message(to=inv, sender=reci, message=invStr)
            self.client.send_message(to=tru, sender=reci, message=truStr)
        self.lock.release()

        # send start signal to all investors
        self.lock.acquire()
        self.client.send_mass_messages(recipientList=self.investor_list, sender=self.client.id(), message="--state:invest")
        self.lock.release()

        self.lock.acquire()
        state_snapshot = self.server_state
        self.lock.release()
        while state_snapshot != "investor done":
            time.sleep(0.2)
            self.lock.acquire()
            state_snapshot = self.server_state
            self.lock.release()
        # sending investment information to trust fund
        self.lock.acquire()
        for investor in self.invest_trustfund_pairing:
            trustfund = str(self.invest_trustfund_pairing[investor])
            message = "--invested:" + self.response_dict[investor]
            self.client.send_message(to=trustfund, sender=self.client.id(), message=message)
        self.lock.release()
        # cleanup
        self.lock.acquire()
        self.server_state = "wait"
        # clearing responses to use the same dict for trust fund responses
        self.response_dict = {}
        self.lock.release()
        # send start signal to all trust funds
        self.lock.acquire()
        self.client.send_mass_messages(recipientList=self.trustfund_list, sender=self.client.id(), message="--trustfundStart")
        self.lock.release()

        # waiting for response from all trust funds
        self.lock.acquire()
        state_snapshot = self.server_state
        self.lock.release()
        while state_snapshot != "trustfund done":
            time.sleep(0.2)
            self.lock.acquire()
            state_snapshot = self.server_state
            self.lock.release()
        # all trust funds have shared, notifying investors
        self.lock.acquire()
        for trustfund in self.response_dict:
            # TODO den her del skal helt sikkert omskrives evt kig paa at lave invest_trustfund_pairing om til list af tuples
            # creates a list of tuples containing trust funds, investors from the invest_trustfund_pairing dict
            pairs = [(trustfunds, investors) for (investors, trustfunds) in self.invest_trustfund_pairing.iteritems()]
            # turns in into a dict, it is now reverse of invest_trustfund_pairing
            tempDict = dict(pairs)
            investor = tempDict[trustfund]
            self.client.send_message(to=investor, sender=self.client.id(), message="--payment:"+self.response_dict[trustfund])
        # clean up
        self.response_dict = {}
        self.lock.release()

        print "end of game round"

if __name__ == '__main__':
    test_server = TestServer()
    user_input = raw_input()
    if user_input == "start":
        test_server.game_round()
        test_server.game_round()
    raw_input()
