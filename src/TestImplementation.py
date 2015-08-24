from NetworkingClient import NetworkingClient
import time


def test_func(s1="default test value", s2="default test value", s3="default test value"):
    print s1
    print s2
    print s3

client = NetworkingClient(server="YLGW036484", port=5222)
client.set_credentials(username="test1", domain="testing.test", secret="1234", resource="Python development")
client.connect()
client.register_message_handler(test_func)
client.start_listening()
client.send_message(to="test1@localhost", message="Test Message from test1", subject="TEST SUBJECT")
time.sleep(15)
client.disconnect()
