from NetworkingClient import NetworkingClient
import time


# limit how far it looks for commands
def message_received(msg):
    # TODO fix global
    global server_state
    global response_dict
    global invest_trustfund_pairing
    # event for investors to register on the server
    if msg.getBody().find("--register:invest") is not -1:
        if msg.getFrom() not in investor_list:
            investor_list.append(msg.getFrom())
            print "adding " + str(msg.getFrom()) + " to invest list"
            return

    # event for trust funds to register on the server
    if msg.getBody().find("--register:trustfund") is not -1:
        if msg.getFrom() not in trustfund_list:
            trustfund_list.append(msg.getFrom())
            print "adding " + str(msg.getFrom()) + " to trust fund list"
            return

    # event when investors sends investment
    if msg.getBody().find("--invest:") is not -1:
        response_dict[msg.getFrom()] = msg.getBody().lstrip("--invest:")
        print "investment from :" + msg.getFrom().getNode() + " he invested: " + msg.getBody().lstrip("--invest:")
        if len(response_dict) == len(invest_trustfund_pairing):
            server_state = "investor done"

    # trust funds pay investors
    if msg.getBody().find("--trustfundPay:") is not -1:
        response_dict[msg.getFrom()] = msg.getBody().lstrip("--trustfundPay:")
        print "trustfund payment from " + msg.getFrom().getNode() + " he paid " + msg.getBody().lstrip("--trustfundPay:")
        if len(response_dict) == len(invest_trustfund_pairing):
            server_state = "trustfund done"


def game_round():
    global server_state
    global response_dict
    # TODO people always play with the same people, stops pairing when 1 of the lists is done
    # pairs people up and use a dictionary to keep track of the pairs
    for trustfund, investor in zip(trustfund_list, investor_list):
        invest_trustfund_pairing[investor] = trustfund

    # send a message to every participant of whom they are trading with
    for investor in invest_trustfund_pairing:
        inv = str(investor)
        tru = str(invest_trustfund_pairing[investor])
        reci = client.id()
        invStr = "--paired:"+tru
        truStr = "--paired:"+inv
        client.send_message(to=inv, sender=reci, message=invStr)
        client.send_message(to=tru, sender=reci, message=truStr)

    # send start signal to all investors
    client.send_mass_messages(recipientList=investor_list, sender=client.id(), message="--state:invest")
    while server_state != "investor done":
        time.sleep(0.2)
    # sending investment information to trust fund
    for investor in invest_trustfund_pairing:
        trustfund = str(invest_trustfund_pairing[investor])
        message = "--invested:" + response_dict[investor]
        client.send_message(to=trustfund, sender=client.id(), message=message)
    # cleanup
    server_state = "wait"
    # clearing responses to use the same dict for trust fund responses
    response_dict = {}
    # send start signal to all trust funds
    client.send_mass_messages(recipientList=trustfund_list, sender=client.id(), message="--trustfundStart")

    # waiting for response from all trust funds
    while server_state != "trustfund done":
        time.sleep(0.2)
    # all trust funds have shared, notifying investors
    for trustfund in response_dict:
        # TODO den her del skal helt sikkert omskrives evt kig paa at lave invest_trustfund_pairing om til list af tuples
        # creater a list of tuples containing trust funds, investors from the invest_trustfund_pairing dict
        pairs = [(trustfunds, investors) for (investors, trustfunds) in invest_trustfund_pairing.iteritems()]
        # turns in into a dict, it is now reverse of invest_trustfund_pairing
        tempDict = dict(pairs)
        investor = tempDict[trustfund]
        client.send_message(to=investor, sender=client.id(), message="--payment:"+response_dict[trustfund])

    print "end of game round"


investor_list = []
trustfund_list = []
invest_trustfund_pairing = {}
response_dict = {}
server_state = ""

if __name__ == '__main__':
    client = NetworkingClient(server='YLGW036484', port=5222)
    client.set_credentials(username='server', domain='YLGW036484', secret='1234', resource='Test Server')
    client.connect()
    client.register_message_handler(message_received)
    client.start_listening()
    user_input = raw_input()
    if user_input == "start":
        game_round()
        game_round()
    raw_input()
