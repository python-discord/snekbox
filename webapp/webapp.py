import traceback

from rmq import send as rmq_send
from flask import Flask
from flask import render_template
from flask_sockets import Sockets

app = Flask(__name__)
sockets = Sockets(app)

@app.route('/')
def index():
    return render_template('index.html')

@sockets.route('/ws')
def websocket_route(ws):
    try:
        while not ws.closed:
            message = ws.receive()

            if not message:
                continue
            print(f"received '{message}'")

            rmq_send(message)

    except:
        print(traceback.format_exec())

    finally:
        if not ws.closed:
            ws.close()

if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=5000, debug=True)
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class=WebSocketHandler)
    server.serve_forever()
