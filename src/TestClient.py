from NetworkingClient import NetworkingClient
from multiprocessing import Value
import threading
import time


class TestClient:
    def __init__(self):
        self.clientType = "trustfund"
        self.client_state = "wait"
        self.lock = threading.RLock()
        self.money_per_round = Value('f', 100.0)
        self.money_invested_this_round = Value('f', 0.0)
        self.total_money = Value('f', 0.0)
        self.investment_received = Value('f', 0.0)
        self.investment_multiplier = Value('f', 3.0)

        # connection variables
        self.username = 'test3'
        self.domain = 'YLGW036484'
        self.server = "server@YLGW036484"
        self.port = 5222

        self.client = NetworkingClient(server=self.domain, port=self.port)
        self.client.set_credentials(username=self.username, domain=self.domain, secret='1234', resource='Test Server')
        self.client.connect()
        self.client.register_message_handler(self)
        self.client.start_listening()
        self.client.send_message(to=self.server, sender=self.client.id(), message="--register:"+self.clientType)

    # limit how far it looks for commands
    def message_received(self, msg):
        # only respond to messages from "server client"
        if str(msg.getFrom()).find(self.server.lower()) is not -1:
            msg_body = msg.getBody()
            # Checking pairing
            if msg_body.find("--paired:") is not -1:
                print "Now trading with: " + msg_body.lstrip("--paired:")
                return

            # signal to start investing, if you are an investor
            if msg_body.find("--state:invest") is not -1 and self.clientType == "investor":
                self.lock.acquire()
                self.client_state = "investor_invest"
                self.lock.release()
                return

            # Message informing amount invested by investor
            if msg_body.find("--invested:") is not -1 and self.clientType == "trustfund":
                self.investment_received.value = 0.0
                self.investment_received.value = float(msg_body.lstrip("--invested:"))
                return

            # Start signal for trust funds
            if msg_body.find("--trustfundStart")is not -1:
                self.lock.acquire()
                self.client_state = "trustfund_invest"
                self.lock.release()
                return

            # Investor notified of money made
            if msg_body.find("--payment") is not -1 and self.clientType == "investor":
                print "You received: " + msg_body.lstrip("--payment:") + " from: " + str(msg.getFrom())
                self.total_money.value = self.total_money.value +  float(msg_body.lstrip("--payment:"))
                print "Your total sum of money is: " + str(self.total_money.value)
                self.lock.acquire()
                self.client_state = "wait"
                self.lock.release()
                return

    def run(self):
        self.lock.acquire()
        state_snapshot = self.client_state
        self.lock.release()
        while state_snapshot != "stop":
            # if investor and investing state, try getting number until successful
            if state_snapshot == "investor_invest" and self.clientType == "investor":
                self.lock.acquire()
                invest_percentage = 0
                # sanitizing input
                while True:
                    try:
                        invest_percentage = int(raw_input("Please enter percentage"
                                                          " to invest (must be between 0 and 100): "))
                        if invest_percentage not in range(0, 101):
                            print "must be a number between 0 and 100"
                        else:
                            break
                    except ValueError:
                        print "That's not a number and you know it ;)"

                # calculates how much money to send and how much to keep
                self.money_invested_this_round.value = self.money_per_round.value * (float(invest_percentage)/100.0)
                self.total_money.value = self.total_money.value + self.money_per_round.value - self.money_invested_this_round.value
                # sending message with amount for trust fund
                # TODO testMsg fjernelse
                testMsg = self.client.send_message(to=self.server, sender=self.client.id(), message="--invest:"+str(self.money_invested_this_round.value))
                print "Message sent\t\t", testMsg
                print "you have invested: ", self.money_invested_this_round.value
                print "you have kept: ", (self.money_per_round.value - self.money_invested_this_round.value)
                self.money_invested_this_round.value = 0.0
                self.client_state = "wait"
                self.lock.release()

            # trust funds got investment from investor
            if state_snapshot == "trustfund_invest" and self.clientType == "trustfund":
                self.lock.acquire()
                self.investment_received.value = self.investment_received.value * self.investment_multiplier.value
                print "You received: " + str(self.investment_received.value)
                print "The investor shared: " + str(self.investment_received.value / (self.money_per_round.value * self.investment_multiplier.value) * 100.0) \
                      + "% of his money"
                # sanitizing input, by making the input into an int, catching a ValueError if it can't
                # then checking if the variable is within the amount wanted. Breaks out on valid input
                invest_percentage = 0
                while True:
                    try:
                        invest_percentage = int(raw_input("Please enter what percentage you "
                                                          "want to share (must be between 0 and 100): "))
                        if invest_percentage not in range(0, 101):
                            print "must be a number between 0 and 100"
                        else:
                            break
                    except ValueError:
                        pass
                money_earned = self.investment_received.value * (1-(float(invest_percentage)/100.0))
                self.total_money.value = self.total_money.value + money_earned
                print "You earned: " + str(money_earned) + " from that investment"
                print "Your total money is: " + str(self.total_money.value)
                # sends message with amount for the investor
                # TODO debug testMsg
                testMsg = self.client.send_message(to=self.server, sender=self.client.id(), message="--trustfundPay:"+str(self.investment_received.value-money_earned))
                print "Message sent\t\t", testMsg
                self.client_state = "wait"
                self.lock.release()
            time.sleep(0.5)
            self.lock.acquire()
            state_snapshot = self.client_state
            self.lock.release()

if __name__ == '__main__':
    test_client = TestClient()
    test_client.run()
