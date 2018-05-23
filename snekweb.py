import traceback
import queue
import threading
import time

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
sockets = Sockets(app)
RMQ_queue = queue.Queue(maxsize=0)

def message_handler(ch, method, properties, body):
    msg = body.decode('utf-8')
    print(f"incoming: {msg} from rabbitmq", flush=True)
    RMQ_queue.put(msg)
    ch.basic_ack(delivery_tag = method.delivery_tag)

def relay_to_ws(ws):
    while not ws.closed:
        try:
            msg = RMQ_queue.get(False)
            if msg:
                print(f"sending {msg} to user", flush=True)
                ws.send(msg)
        except queue.Empty:
            time.sleep(0.1)
            pass

t1 = threading.Thread(target=consume, kwargs={'host':HOST, 'queue':RETURN_QUEUE, 'callback':message_handler})
t1.daemon = True
t1.start()

@app.route('/')
def index():
    return render_template('index.html')

@sockets.route('/ws')
def websocket_route(ws):
    t2 = threading.Thread(target=relay_to_ws, args=(ws, ))
    t2.daemon = True
    t2.start()

    try:
        while not ws.closed:

            message = ws.receive()

            if not message:
                continue
            print(f"forwarding '{message}' to rabbitmq")

            publish(message, host=HOST, queue=QUEUE, routingkey=ROUTING_KEY, exchange=EXCHANGE, exchange_type=EXCHANGE_TYPE)

    except:
        print(traceback.format_exc())

    finally:
        if not ws.closed:
            ws.close()

if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
