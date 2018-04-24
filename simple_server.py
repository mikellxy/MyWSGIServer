import socket
from io import StringIO
import sys


class TCPServer(object):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5

    def __init__(self, server_address):
        self._socket = _socket = socket.socket(
            self.address_family,
            self.socket_type
        )

        _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # bind to server_addresss
        _socket.bind(server_address)
        # activate to listen
        _socket.listen(self.request_queue_size)
        # achieve host and port of the server
        host, self.port = _socket.getsockname()[:2]
        # get server name
        self.server_name = socket.getfqdn(host)
        #
        self.client_conn = None


class HttpServer(TCPServer):
    def __init__(self, server_address):
        super(HttpServer, self).__init__(server_address)
        self.request_data = None
        self.request_method = None
        self.path = None
        self.request_version = None


    def parse_request(self, text):
        # 请求第一行部分（method，path，http版本)
        request_line = text.splitlines()[0]
        # 请求第一部分有两次换行
        request_line = request_line.rstrip('\r\n')
        # 以空格分隔
        self.request_method, self.path, self.request_version = request_line.split()

    def get_environ(self):
        env = {}

        env['wsgi.version'] = (1, 0)
        env['wsgi.url_scheme'] = 'http'
        env['wsgi.input'] = StringIO(self.request_data)
        env['wsgi.errors'] = sys.stderr
        env['wsgi.multithread'] = False
        env['wsgi.multiprocess'] = False
        env['wsgi.run_once'] = False

        env['REQUEST_METHOD'] = self.request_method
        env['PATH_INFO'] = self.path
        env['SERVER_NAME'] = self.server_name  # localhost
        env['SERVER_PORT'] = str(self.port)  # 8888
        return env



class WSGIServer(HttpServer, TCPServer):
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM
    request_queue_size = 5

    def __init__(self, server_address):
        super(WSGIServer, self).__init__(server_address)
        self.application = None
        self.headers_set = []


    def set_app(self, application):
        self.application = application

    def serve_forever(self):
        while True:
            self.client_conn, client_addr = self._socket.accept()
            self.handle_one_request()

    def handle_one_request(self):
        self.request_data = request_data = self.client_conn.recv(1024).decode("UTF8")
        self.parse_request(request_data)
        env = self.get_environ()
        result = self.application(env, self.start_response)
        self.finish_response(result)

    def start_response(self, status, headers, exc_info=None):
        self.headers_set = [status, headers]
        # return self.finish_response

    def finish_response(self, result):
        try:
            # response headers part BEGIN
            status, response_headers = self.headers_set
            # 响应数据第一行：http版本 状态码
            response = 'HTTP/1.1 {status}\r\n'.format(status=status)
            # 每个响应头换行，最后一个响应头换两行
            for header in response_headers:
                response += '{0}: {1}\r\n'.format(*header)
            response += '\r\n'
            # response headers part END

            response = response.encode("UTF8")

            # 追加请求体数据
            for data in result:
                response += data

            self.client_conn.sendall(response)
        # 暂时不捕获异常，finally要释放链接
        finally:
            self.client_conn.close()


SERVER_ADDRESS = '127.0.0.1', 8090

def make_server(server_address, application):
    host, port = server_address
    if host == '127.0.0.1':
        server_address = ('', port)
    server = WSGIServer(server_address)
    server.set_app(application)
    return server

from flask import Flask, redirect
app = Flask(__name__)


@app.route('/index/<username>')
def index(username):
    # return redirect('https://www.baidu.com')
    return "Hellow: " + username.upper()


if __name__ == '__main__':
    httpd = make_server(SERVER_ADDRESS, app)
    httpd.serve_forever()