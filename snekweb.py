import traceback
import threading
import logging
import json

from flask import Flask
from flask import render_template
from flask_sockets import Sockets


from rmq import Rmq

# Load app
app = Flask(__name__)
app.jinja_env.auto_reload = True
sockets = Sockets(app)

# Logging
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)
log = app.logger


@app.route('/')
def index():
    return render_template('index.html')


@sockets.route('/ws/<snekboxid>')
def websocket_route(ws, snekboxid):
    localdata = threading.local()
    localdata.thread_ws = ws

    rmq = Rmq()

    def message_handler(ch, method, properties, body, thread_ws):
        msg = body.decode('utf-8')
        log.debug(f"message_handler: {msg}")
        thread_ws.send(msg)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    consumer_parameters = {'queue': snekboxid,
                           'callback': message_handler,
                           'thread_ws': localdata.thread_ws}
    consumer = threading.Thread(target=rmq.consume, kwargs=consumer_parameters)
    consumer.daemon = True
    consumer.start()

    try:
        while not ws.closed:
            message = ws.receive()
            if message:
                snek_msg = json.dumps({snekboxid: message})
                log.info(f"User {snekboxid} sends message\n{message.strip()}")
                rmq.publish(snek_msg)

    except Exception:
        log.info(traceback.format_exc())

    finally:
        if not ws.closed:
            ws.close()


if __name__ == '__main__':
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
