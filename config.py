import os


def autodiscover():
    container_names = ["rmq", "pdrmq", "snekbox_pdrmq_1"]
    try:
        import docker
        client = docker.from_env()
        for name in container_names:
            container = client.containers.get(name)
            if container.status == "running":
                host = list(container.attrs.get('NetworkSettings').get('Networks').values())[0]['IPAddress']
                return host
    except Exception:
        return '127.0.0.1'


USERNAME = os.environ.get('RMQ_USERNAME', 'rabbits')
PASSWORD = os.environ.get('RMQ_PASSWORD', 'rabbits')
HOST = os.environ.get('RMQ_HOST', autodiscover())
PORT = 5672
QUEUE = 'input'
EXCHANGE = QUEUE
ROUTING_KEY = QUEUE
EXCHANGE_TYPE = 'direct'
