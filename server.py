import http.server
import socketserver
import os

PORT = 8000
DIRECTORY = "logs"

class HttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

if __name__ == "__main__":
    os.makedirs(DIRECTORY, exist_ok=True)
    with socketserver.TCPServer(("", PORT), HttpRequestHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
