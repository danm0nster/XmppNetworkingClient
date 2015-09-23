from NetworkingClient import NetworkingClient
import time
import random


class BlockingServer(object):
    def __init__(self):
        # Username is the first part of the JID it will use
        self.username = 'server'
        # Domain name of the server
        self.domain = 'YLGW036487'
        # Port number to connect to, 5222 is default
        self.port = 5222

        # General Variables
        self.state = "signup"
        self.investor_list = []
        self.trust_fund_list = []
        self.response_dict = {}
        self.investor_trust_fund_pairing = {}

        # Making a new instance of the NetworkingClient, providing it with domain and port
        self.network = NetworkingClient(server=self.domain, port=self.port)
        # starts a connection but doesn't receive messages
        print 'connected with', self.network.connect()
        # logging in
        print 'authenticated with ', \
            self.network.authenticate(username=self.username, domain=self.domain, secret='1234', resource='Test Server')

    # given a dictionary calculates if it has the same amount of entries as the shortest list of participant types
    def _have_all_responses(self, dict):
        if len(self.investor_list) <= len(self.trust_fund_list):
            if len(dict) == len(self.investor_list):
                return True
        else:
            if len(dict) == len(self.trust_fund_list):
                return True
        return False

    def game_round(self):
        # handling signup messages until start signal is given
        while self.state == "signup":
            # check for new signup messages
            if self.network.check_for_messages():
                msg = self.network.pop_message()
                # check if a investor registers
                if msg.body.find('--register:investor') is not -1:
                    print "adding investor"
                    self.investor_list.append(msg.sender)
                # checks if a trust fund registers
                elif msg.body.find('register:trustfund') is not -1:
                    print "adding trustfund"
                    self.trust_fund_list.append(msg.sender)
                # my start condition, in this case it's the number of players
                if len(self.investor_list) + len(self.trust_fund_list) == 4:
                    self.state = "pairing"
            time.sleep(0.1)

        # pairing investors and trust funds
        if self.state == 'pairing':
            # mixing investors and trustfunds for random pairing
            random.shuffle(self.investor_list)
            random.shuffle(self.trust_fund_list)
            for investor, trustfund in zip(self.investor_list, self.trust_fund_list):
                self.investor_trust_fund_pairing[investor] = trustfund

            # sending information to clients about their pairings
            for investor in self.investor_trust_fund_pairing:
                print str(investor) + "\tmatched with:\t" + str(self.investor_trust_fund_pairing[investor])
                self.network.send_message(to=investor, sender=self.network.id(), message='--paired:' + str(self.investor_trust_fund_pairing[investor]))
                self.network.send_message(to=self.investor_trust_fund_pairing[investor], sender=self.network.id(), message='--paired:' + str(investor))

            # sending the start signal for investors
            for investor in self.investor_trust_fund_pairing:
                self.network.send_message(to=investor, sender=self.network.id(), message='--invest:start')
            # changing server state to wait for responses
            self.state = "wait"

        # clearing the response dictionary before use
        self.response_dict = {}
        # waiting for responses from investors
        print 'getting investments'
        while self.state == 'wait':
            if self.network.check_for_messages():
                msg = self.network.pop_message()
                if msg.body.find('--investor:invest') is not -1:
                    investor = msg.sender
                    investment = msg.body.lstrip('--investor:invest')
                    self.response_dict[investor] = investment
                    print investor, 'invested: ', investment
                    # when all investors have responded change state
                    if self._have_all_responses(self.response_dict):
                        self.state = 'notify trustfunds'
            time.sleep(0.1)

        print 'getting responses from trust funds'
        # notifying trust funds of investments
        while self.state == 'notify trustfunds':
            # need to go through each investment and find the corresponding trust fund
            for investor in self.response_dict:
                trust_fund = self.investor_trust_fund_pairing[investor]
                self.network.send_message(to=trust_fund, sender=self.network.id(), message='--investment:'+self.response_dict[investor])
            self.state = 'trustfunds_shared'
            time.sleep(0.1)

        # clearing response dict for reuse
        self.response_dict = {}
        # notifying investors of received share from trust funds
        print 'sending responses to investors'
        while self.state == 'trustfunds_shared':
            if self.network.check_for_messages():
                msg = self.network.pop_message()
                if msg.body.find('--trustfund_pay:') is not -1:
                    # switching keys and values in the pairing dictionary, to find the trust fund -> invester link
                    trustfund_pairing_dict = dict((tru, inv) for inv, tru in self.investor_trust_fund_pairing.iteritems())
                    investor = trustfund_pairing_dict[msg.sender]
                    self.response_dict[investor] = msg.body.lstrip('--trustfund_pay:')
                    if self._have_all_responses(self.response_dict):
                        print 'received all responses, sending payment to investors'
                        for investor in self.response_dict:
                            self.network.send_message(to=investor, sender=self.network.id(), message='--trustfund_pay:'+self.response_dict[investor])
                        self.state = 'pairing'
            time.sleep(0.1)

if __name__ == "__main__":
    server = BlockingServer()
    while True:
        server.game_round()
