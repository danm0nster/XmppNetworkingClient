from NetworkingClient import NetworkingClient
import time


class BlockingClient(object):
    def __init__(self):
        # connection variables
        self.username = 'test4'
        self.domain = 'YLGW036484'
        self.server = "server@YLGW036484"
        self.port = 5222

        self.client_type = "investor"
        self.state = "wait"
        self.money_per_round = 100.0
        self.total_money = 0.0
        self.trust_fund_multiplication = 3.0

        # connecting
        self.network = NetworkingClient(server=self.domain, port=self.port)
        con = self.network.connect()
        if con == 'tls':
            print 'connected with tls'
        auth = self.network.authenticate(username=self.username, domain=self.domain, secret='1234', resource='Test Server')
        if auth == 'sasl':
            print 'authenticated with sasl'

    def start_when_ready(self):
        # register with server
        self.network.send_message(to=self.server, sender=self.network.id(), message="--register:"+self.client_type)
        # wait for pairing info
        while self.state != 'exit':
            if self.network.check_for_messages():
                msg = self.network.pop_message()
                if msg.getBody().find('--paired:') is not -1:
                    print 'Paired with ' + msg.getBody().lstrip('--paired:')

                # if selected and investor, starting up investment process
                if self.client_type == 'investor' and msg.getBody().find('--invest:start') is not -1:
                    print 'You get ', self.money_per_round, 'to invest, or keep'
                    invest_percentage = 50
                    # getting input from user, breaking out of loop when input is valid
                    while True:
                        try:
                            invest_percentage = int(raw_input('Enter what percentage you wish to invest: '))
                            if invest_percentage not in range(0, 101):
                                print 'Must be a number between 0 and 100'
                            else:
                                break
                        except ValueError:
                            print 'That is not a number and you know it ;)'
                    # notify server of investment
                    print 'You have invested: ', self.money_per_round * float(invest_percentage/100.0)
                    print 'You have kept: ', self.money_per_round - self.money_per_round * float(invest_percentage/100.0)
                    self.total_money = self.total_money + self.money_per_round - self.money_per_round * float(invest_percentage/100.0)
                    self.network.send_message(to=self.server, sender=self.network.id(), message='--investor:invest'+str(self.money_per_round*float(invest_percentage/100.0)))

                # investor waiting for response from trust fund
                if self.client_type == 'investor' and msg.getBody().find('--trustfund_pay:') is not -1:
                    payment = float(msg.getBody().lstrip('--trustfund_pay:'))
                    print 'Trustfund payment of: ', payment
                    self.total_money += payment
                    print 'Your total amount of money is: ', self.total_money

                # if selected trust fund, receive investment and decide how much to pay back
                if self.client_type == 'trustfund' and msg.getBody().find('--investment:') is not -1:
                    investment_received = float(msg.getBody().lstrip('--investment:'))
                    investment_received *= self.trust_fund_multiplication
                    invest_percentage = 50
                    print "Received investment of: ", investment_received
                    print "The invester shared " + str(investment_received / (self.money_per_round * self.trust_fund_multiplication) * 100.0) + '% of his money'
                    while True:
                        try:
                            invest_percentage = int(raw_input('Enter what percentage you wish to split with the investor: '))
                            if invest_percentage not in range(0, 101):
                                print 'Must be a number between 0 and 100'
                            else:
                                break
                        except ValueError:
                            print "That is not a number and you know it ;)"
                    money_shared = investment_received * float(invest_percentage) / 100.0
                    self.total_money = self.total_money + investment_received - money_shared
                    print 'Your total amount of money is: ' + str(self.total_money)
                    print 'You shared: ', money_shared
                    self.network.send_message(to=self.server, sender=self.network.id(), message='--trustfund_pay:'+str(money_shared))
            time.sleep(0.1)

if __name__ == "__main__":
    client = BlockingClient()
    client.start_when_ready()
