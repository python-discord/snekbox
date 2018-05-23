import pika

def publish(message, username='guest', password='guest', host='localhost', port=5672, queue='', routingkey='', exchange='', exchange_type=''):
    credentials = pika.PlainCredentials(username, password)
    connection = pika.BlockingConnection(pika.ConnectionParameters(host, port, '/', credentials))
    properties = pika.BasicProperties(content_type='text/plain', delivery_mode=1)

    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=False)
    channel.exchange_declare(exchange=exchange, exchange_type=exchange_type)
    channel.queue_bind(exchange=exchange, queue=queue, routing_key=routingkey)

    result = channel.basic_publish(
                exchange=exchange,
                routing_key=routingkey,
                body=message,
                properties=properties
    )

    if result:
        print(f"Connecting to host: {host} port: {port} exchange: {exchange} queue: {queue}", flush=True)
    else:
        print("not delivered")

    connection.close()

