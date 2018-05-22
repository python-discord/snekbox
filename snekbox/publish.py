import pika
from config import USERNAME
from config import PASSWORD
from config import HOST
from config import PORT
from config import EXCHANGE
from config import EXCHANGE_TYPE
from config import QUEUE
from config import ROUTING_KEY

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
