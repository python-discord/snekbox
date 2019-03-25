from flask import Flask, jsonify, render_template, request

from snekbox.nsjail import NsJail

nsjail = NsJail()

# Load app
app = Flask(__name__)
app.use_reloader = False

# Logging
log = app.logger


@app.route('/')
def index():
    """Return a page with a form for inputting code to be executed."""

    return render_template('index.html')


@app.route('/result', methods=["POST", "GET"])
def result():
    """Execute code and return a page displaying the results."""

    if request.method == "POST":
        code = request.form["Code"]
        output = nsjail.python3(code)
        return render_template('result.html', code=code, result=output)


@app.route('/input', methods=["POST"])
def code_input():
    """Execute code and return the results."""

    body = request.get_json()
    output = nsjail.python3(body["code"])
    return jsonify(input=body["code"], output=output)
