import traceback
import queue
import threading
import time
import json

from rmq.publisher import publish
from rmq.consumer import consume

from flask import Flask
from flask import render_template
from flask_sockets import Sockets

from config import HOST
from config import PORT
from config import EXCHANGE
from config import EXCHANGE_TYPE
from config import QUEUE
from config import RETURN_QUEUE
from config import ROUTING_KEY

app = Flask(__name__)
app.jinja_env.auto_reload = True
sockets = Sockets(app)


@app.route('/')
def index():
    return render_template('index.html')

@sockets.route('/ws/<snekboxid>')
def websocket_route(ws, snekboxid):
    RMQ_queue = queue.Queue(maxsize=0)

    def message_handler(ch, method, properties, body):
        msg = body.decode('utf-8')
        RMQ_queue.put(msg)
        ch.basic_ack(delivery_tag = method.delivery_tag)

    consumer = threading.Thread(target=consume, kwargs={'host':HOST, 'queue':snekboxid, 'callback':message_handler})
    consumer.daemon = True
    consumer.start()

    def relay_to_ws(ws):
        global client_list
        while True:
            try:
                msg = RMQ_queue.get(False)
                if msg:
                    ws.send(msg)
            except queue.Empty:
                time.sleep(0.1)
                pass

    relay = threading.Thread(target=relay_to_ws, args=(ws,))
    relay.daemon = True
    relay.start()

    try:
        while not ws.closed:
            message = ws.receive()
            if message:
                snek_msg = json.dumps({snekboxid:message})
                print(f"forwarding {snek_msg} to rabbitmq")
                publish(snek_msg, host=HOST, queue=QUEUE, routingkey=ROUTING_KEY, exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE)

    except:
        print(traceback.format_exc())

    finally:
        if not ws.closed:
            ws.close()

# if __name__ == '__main__':
#     from gevent import pywsgi
#     from geventwebsocket.handler import WebSocketHandler
#     server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
#     server.serve_forever()
