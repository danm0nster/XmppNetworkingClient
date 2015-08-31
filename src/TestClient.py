from NetworkingClient import NetworkingClient
import time

clientType = "trustfund"
username = 'test2'
domain = 'YLGW036484'
server = "server@YLGW036484"
client_state = "wait"
money_per_round = 100.0
money_invested_this_round = 0.0
total_money = 0.0
investment_received = 0.0
investment_multiplier = 3.0


# limit how far it looks for commands
def message_received(msg):
    # making variables global to access them from thread
    # TODO don't use globals
    global client_state
    global clientType
    global investment_received
    global investment_received
    global total_money
    # only respond to messages from "server client"
    if msg.getFrom() == "server@ylgw036484/Test Server":
        msg_body = msg.getBody()
        if msg_body.find("--paired:") is not -1:
            print "Now trading with: " + msg_body.lstrip("--paired:")

        if msg_body.find("--state:invest") is not -1 and clientType == "investor":
            client_state = "investor_invest"

        if msg_body.find("--invested:") is not -1 and clientType == "trustfund":
            investment_received = 0.0
            investment_received = float(msg_body.lstrip("--invested:"))

        if msg_body.find("--trustfundStart")is not -1:
            client_state = "trustfund_invest"

        if msg_body.find("--payment") is not -1 and clientType == "investor":
            print "You received: " + msg_body.lstrip("--payment:") + " from: " + str(msg.getFrom())
            total_money += float(msg_body.lstrip("--payment:"))
            print "Your total sum of money is: " + str(total_money)
            client_state = "wait"


if __name__ == '__main__':
    client = NetworkingClient(server='YLGW036484', port=5222)
    client.set_credentials(username=username, domain=domain, secret='1234', resource='Test Server')
    client.connect()
    client.register_message_handler(message_received)
    client.start_listening()
    client.send_message(to=server, sender=client.id(), message="--register:"+clientType)

    while client_state != "stop":
        # if investor and investing state, try getting number until successful
        if client_state == "investor_invest" and clientType == "investor":
            invest_percentage = 0
            # sanitizing input
            while True:
                try:
                    invest_percentage = int(raw_input("Please enter percentage to invest (must be between 0 and 100): "))
                    if invest_percentage not in range(0, 101):
                        print "must be a number between 0 and 100"
                    else:
                        break
                except ValueError:
                    print "That's not a number and you know it ;)"

            # calculates how much money to send and how much to keep
            money_invested_this_round = money_per_round * (float(invest_percentage)/100.0)
            total_money = total_money + money_per_round - money_invested_this_round
            # sending message with amount for trust fund
            client.send_message(to=server, sender=client.id(), message="--invest:"+str(money_invested_this_round))
            print "you have invested: ", money_invested_this_round
            print "you have kept: ", (money_per_round - money_invested_this_round)
            money_invested_this_round = 0.0
            client_state = "wait"

        # trust funds got investment from investor
        if client_state == "trustfund_invest" and clientType == "trustfund":
            investment_received *= investment_multiplier
            print "You received: " + str(investment_received)
            print "The investor shared: " + str(investment_received / (money_per_round * investment_multiplier) * 100.0) \
                  + "% of his money"
            # sanitizing input, by making the input into an int, catching a ValueError if it can't
            # then checking if the variable is within the amount wanted. Breaks out on valid input
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
            money_earned = total_money + investment_received * (1-(float(invest_percentage)/100.0))
            total_money += money_earned
            print "You earned: " + str(money_earned) + " from that investment"
            print "Your total money is: " + str(total_money)
            # sends message with amount for the investor
            client.send_message(to=server, sender=client.id(), message="--trustfundPay:"
                                                                       + str(investment_received - money_earned))
            money_earned = 0.0
            client_state = "wait"
        time.sleep(0.5)
