import os

def attempt_automatically_finding_the_ip_of_rmq():
    try:
        import docker
        client = docker.from_env()
        containers = client.containers.get('snekbox_pdrmq_1')
        HOST = list(containers.attrs.get('NetworkSettings').get('Networks').values())[0]['IPAddress']
        return HOST
    except:
        return '172.17.0.2'

USERNAME = 'guest'
PASSWORD = 'guest'
HOST = os.environ.get('RMQ_HOST', attempt_automatically_finding_the_ip_of_rmq())
PORT = 5672
EXCHANGE_TYPE = 'direct'

QUEUE = 'input'
EXCHANGE = QUEUE
ROUTING_KEY = QUEUE

RETURN_QUEUE = 'return'
RETURN_EXCHANGE = RETURN_QUEUE
RETURN_ROUTING_KEY = RETURN_QUEUE
