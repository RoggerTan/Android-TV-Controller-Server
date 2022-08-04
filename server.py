import os;
import sys;

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

from flask import Flask, request, make_response
from waitress import serve
from config import configHelper
from sending_keys import SendingKeySocket
from key_codes import *
import socket, ssl
import json
from OpenSSL.crypto import load_certificate, FILETYPE_PEM
from asn1crypto.x509 import Certificate
import hashlib
import base64

sslSock = None
sendingKeySocket = None
messageStatus = None
messageType = None

keyCodeDct = {
    'h': KEYCODE_HOME,
    'b': KEYCODE_BACK,
    'w': KEYCODE_DPAD_UP,
    's': KEYCODE_DPAD_DOWN,
    'a': KEYCODE_DPAD_LEFT,
    'd': KEYCODE_DPAD_RIGHT,
    'o': KEYCODE_DPAD_CENTER,
    'u': KEYCODE_VOLUME_UP,
    'j': KEYCODE_VOLUME_DOWN,
    '0': KEYCODE_0,
    '1': KEYCODE_1,
    '2': KEYCODE_2,
    '3': KEYCODE_3,
    '4': KEYCODE_4,
    '5': KEYCODE_5,
    '6': KEYCODE_6,
    '7': KEYCODE_7,
    '8': KEYCODE_8,
    '9': KEYCODE_9,
    'circle': KEYCODE_STB_POWER,
    'rewind': KEYCODE_MEDIA_REWIND,
    'forward': KEYCODE_MEDIA_FAST_FORWARD,
    'nextchn': KEYCODE_F8,
    'prechn': KEYCODE_F9,
    'del': KEYCODE_DEL,
    'pow': KEYCODE_POWER,
}

app = Flask(__name__,
            static_url_path='', 
            static_folder='static',
            template_folder='templates')

# Fix issues behind reverse proxy
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

def sendSignal(key):
    global sendingKeySocket, keyCodeDct
    boxIp = configHelper.read("server")["boxIp"]
    remoteName = configHelper.read("server")["remoteName"]
    tryReconnect = False

    while True:
        try:
            if key in keyCodeDct:
                sendingKeySocket.send_key_command(keyCodeDct[key])
            else:
                sendingKeySocket.send_key_command(int(key))
            break
        except:
            if tryReconnect:
                break
            # Connection maybe down. Reconnecting 1 time only
            tryReconnect = True
            sendingKeySocket = SendingKeySocket(remoteName, boxIp)
            sendingKeySocket.connect()

@app.route("/signal", methods=['GET'])
def signal():
    key = request.args.get("key")
    sendSignal(key)
    return make_response()

@app.route("/startpairing", methods=["GET"])
def startPairing():
    global sslSock, messageStatus, messageType
    boxIp = configHelper.read("server")["boxIp"]
    remoteName = configHelper.read("server")["remoteName"]

    port = 6467

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sslSock = ssl.wrap_socket(sock,
                        keyfile="key.pem",
                        certfile="cert.pem",
                        do_handshake_on_connect=True)
    sslSock.connect((boxIp, port))

    # Create pairing msg
    message = {"protocol_version":1,"payload":{"service_name":"androidtvremote","client_name":remoteName},"type":10,"status":200}
    msg = json.dumps(message)

    # Send msg
    sslSock.send((len(msg)).to_bytes(4, byteorder='big'))
    sslSock.send(msg.encode())

    # Receive msg
    rawMsg = None

    while True:
        msg = ''
        rawMsg = sslSock.recv(1024)
        if len(rawMsg) > 4:
            json_object = json.loads(rawMsg)
            messageStatus = json_object["status"]
            messageType = 0
            if messageStatus == 200:
                messageType = json_object["type"]
                if messageType == 11:
                    # crating option message
                    message = {"protocol_version":1,"payload":{"output_encodings":[{"symbol_length":4,"type":3}],
                    "input_encodings":[{"symbol_length":4,"type":3}],"preferred_role":1},"type":20,"status":200}
                    msg = json.dumps(message)

                elif messageType == 20:
                    # creating configuration message
                    message = {"protocol_version":1,"payload":{"encoding":{"symbol_length":4,"type":3},"client_role":1},"type":30,"status":200}
                    msg = json.dumps(message)

                elif messageType == 31:
                    return make_response()

                elif messageType == 41:
                    sslSock.close()
                    break
            else:
                return make_response()

            sslSock.send((len(msg)).to_bytes(4, byteorder='big'))
            sslSock.send(msg.encode())

    return make_response()

@app.route("/pairing", methods=["GET"])
def pairing():
    global sslSock, sendingKeySocket, messageStatus, messageType
    boxIp = configHelper.read("server")["boxIp"]
    remoteName = configHelper.read("server")["remoteName"]

    secret = request.args.get("secret")

    if messageStatus == 200:
        if messageType == 31:
            # Creating secret message: a sha-256 hash of client certificate modulus + client certificate exponent +
            # server modulus + server exponent + two last digit of pairing key coded to base64
            with open("cert.pem", 'rb') as fp:
                cert = load_certificate(FILETYPE_PEM, fp.read())
            client_modulus = cert.get_pubkey().to_cryptography_key().public_numbers().n
            client_exponent = cert.get_pubkey().to_cryptography_key().public_numbers().e
            # all items in hex format
            client_mod = '{:X}'.format(client_modulus)
            client_exp = "010001"
            server_cert = Certificate.load(sslSock.getpeercert(True))
            server_mod = '{:X}'.format(server_cert.public_key.native["public_key"]["modulus"])
            server_exp = "010001"
            h = hashlib.sha256()
            h.update(bytes.fromhex(client_mod))
            h.update(bytes.fromhex(client_exp))
            h.update(bytes.fromhex(server_mod))
            h.update(bytes.fromhex(server_exp))
            h.update(bytes.fromhex(secret[-2:]))
            hash_result = h.digest()

            message = {"protocol_version":1,"payload":{"secret":base64.b64encode(hash_result).decode()},"type":40,"status":200}
            msg = json.dumps(message)

            # Send msg
            sslSock.send((len(msg)).to_bytes(4, byteorder='big'))
            sslSock.send(msg.encode())

            if sendingKeySocket is not None:
                sendingKeySocket.disconnect()
            sendingKeySocket = SendingKeySocket(remoteName, boxIp)
            sendingKeySocket.connect()

    sslSock.close()

    messageStatus = None
    messageType = None

    return make_response()

if __name__ == '__main__':
    isDeployed = configHelper.read("server")["isDeployed"]
    host = configHelper.read("server")["host"]
    port = configHelper.read("server")["port"]

    boxIp = configHelper.read("server")["boxIp"]
    remoteName = configHelper.read("server")["remoteName"]

    try:
        sendingKeySocket = SendingKeySocket(remoteName, boxIp)
        sendingKeySocket.connect()
    except:
        # Server may attempt to reconnect in sendSignal, so we can skip this if network is unreachable
        pass

    if isDeployed:
        serve(app, host=host, port=port, threads=1, ident=None)
    else:
        app.run(debug=True, host="127.0.0.1", port=port)
