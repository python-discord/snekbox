import pika
from config import (
    USERNAME,
    PASSWORD,
    HOST,
    PORT,
    EXCHANGE,
    EXCHANGE_TYPE,
    QUEUE,
    ROUTING_KEY,
)

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
        print(f"""Connecting to
            host: {HOST}
            port: {PORT}
            exchange: {EXCHANGE}
            queue: {QUEUE}""", flush=True)
        print(f"Sent: '{message}'")
    else:
        print("not delivered")

    connection.close()

send('print "bacon is delicious"')
