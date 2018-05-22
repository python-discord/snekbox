import os

USERNAME      = 'guest'
PASSWORD      = 'guest'
HOST          = os.environ.get('RMQ_HOST', '172.17.0.2')
PORT          = 5672
EXCHANGE      = 'exchange'
EXCHANGE_TYPE = 'direct'
QUEUE         = 'text'
ROUTING_KEY   = 'bacon'
