from NetworkingClient import NetworkingClient
import time


def test_func(s1="default test value 1", s2="default test value 2", s3="default test value 3"):
    print s1
    print s2
    print s3

if __name__ == '__main__':
    client = NetworkingClient(server="YLGW036484", port=5222)
    client.set_credentials(username="test1", domain="YLGW036484", secret="1234", resource="Python development")
    client.connect()
    client.register_message_handler(test_func)
    client.start_listening()
    client.send_message(to="test2@YLGW036484", message="Test Message from test1", subject="TEST SUBJECT")
    time.sleep(10)
    client.disconnect()
