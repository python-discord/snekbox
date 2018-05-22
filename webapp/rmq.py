import os
import pika

USERNAME      = 'guest'
PASSWORD      = 'guest'
HOST          = os.environ.get('RMQ_HOST', '172.17.0.2')
PORT          = 5672
EXCHANGE      = 'exchange'
EXCHANGE_TYPE = 'direct'
QUEUE         = 'text'
ROUTING_KEY   = 'bacon'

try:
    import docker
    client = docker.from_env()
    containers = client.containers.get('snekbox_pdrmq_1')
    print("Attempting to get rabbitmq host automatically")
    HOST = list(containers.attrs.get('NetworkSettings').get('Networks').values())[0]['IPAddress']
    print(f"found {HOST}")
except:
    pass

def send(message):
    credentials = pika.PlainCredentials(USERNAME, PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(HOST, PORT, '/', credentials))
    properties = pika.BasicProperties(content_type='text/plain', delivery_mode=1)

    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, durable=False)
    channel.exchange_declare(exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE)
    channel.queue_bind(exchange=EXCHANGE, queue=QUEUE, routing_key=ROUTING_KEY)

    result = channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY,
                body=message,
                properties=properties
    )

    if result:
        print(f"""Connecting to\nhost:     {HOST}\nport:     {PORT}\nexchange: {EXCHANGE}\nqueue:    {QUEUE}""", flush=True)
        print(f"Sent: '{message}'")
    else:
        print("not delivered")

    connection.close()

#send('print("bacon is delicious")')
