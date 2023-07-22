import json
import logging
import pathlib
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from mimetypes import guess_type
import urllib.parse
from datetime import datetime
from threading import Thread

from jinja2 import Environment, FileSystemLoader

BASE_DIR = pathlib.Path()
env = Environment(loader=FileSystemLoader('assets/templates'))
SERVER_IP = '127.0.0.1'
SERVER_PORT = 5000
BUFFER = 1024
DATA_STORAGE = 'storage/data.json'


class HttpHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        send_data_to_socket(body)
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file('index.html')
        elif pr_url.path == '/message':
            self.send_html_file('message.html')
        else:
            if BASE_DIR.joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file('error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'.{self.path}', 'rb') as file:
            self.wfile.write(file.read())


def run_socket_server(ip, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server = ip, port
    server_socket.bind(server)
    try:
        while True:
            data, address = server_socket.recvfrom(BUFFER)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped')
    finally:
        server_socket.close()


def save_data(data):
    body_parse = urllib.parse.unquote_plus(data.decode())
    try:
        body_dict = {key: value for key, value in [el.split('=') for el in body_parse.split('&')]}
        time = datetime.now()
        result_dict = {str(time): body_dict}
        file_data = {}
        if pathlib.Path(DATA_STORAGE).exists():
            with open(BASE_DIR.joinpath(DATA_STORAGE), 'r', encoding='utf-8') as fd:
                file_data = json.load(fd)
                file_data.update(result_dict)

        with open(BASE_DIR.joinpath(DATA_STORAGE), 'w', encoding='utf-8') as fd:
            json.dump(file_data, fd, indent=4, ensure_ascii=False)


    except ValueError as err:
        logging.error(f'Field parse {body_parse} with error {err}')
    except OSError as err:
        logging.error(f'Field write {body_parse} with error {err}')


def send_data_to_socket(body):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.sendto(body, (SERVER_IP, SERVER_PORT))
    client_socket.close()


def run(server=HTTPServer, handler=HttpHandler):
    address = ('', 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    thread_server = Thread(target=run)
    thread_server.start()

    thread_socket = Thread(target=run_socket_server(SERVER_IP, SERVER_PORT))
    thread_socket.start()
