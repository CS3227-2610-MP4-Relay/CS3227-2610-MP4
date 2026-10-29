"""A local HTTPS server with a throwaway certificate, for gateway transport tests."""

import socket
import ssl
import subprocess
import threading
import time


def make_certificate(directory, name="IP:127.0.0.1"):
    """Write a one-day self-signed certificate for `name`; return its paths."""
    cert, key = directory / "cert.pem", directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=synthetic",
            "-addext",
            f"subjectAltName={name}",
        ],
        check=True,
        capture_output=True,
    )
    return cert, key


def respond(raw):
    """A script that sends `raw` at once, then closes."""

    def script(conn):
        conn.sendall(raw)

    return script


def hold(raw, duration):
    """A script that sends `raw` at once, then keeps the connection open."""

    def script(conn):
        conn.sendall(raw)
        time.sleep(duration)

    return script


class Server:
    """Serve one scripted response per connection on 127.0.0.1 over TLS."""

    def __init__(self, cert, key, script):
        self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        self.context.load_cert_chain(cert, key)
        self.script = script
        self.requests = []
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    @property
    def url(self):
        """The HTTPS endpoint the gateway should call."""
        return f"https://127.0.0.1:{self.port}/llm"

    def _serve(self):
        while True:
            try:
                plain, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(plain,), daemon=True).start()

    def _handle(self, plain):
        try:
            with self.context.wrap_socket(plain, server_side=True) as conn:
                conn.settimeout(5)
                self.requests.append(self._read_request(conn))
                self.script(conn)
        except OSError:
            return

    @staticmethod
    def _read_request(conn):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(65536)
            if not chunk:
                return data
            data += chunk
        head, _, body = data.partition(b"\r\n\r\n")
        length = 0
        for line in head.split(b"\r\n")[1:]:
            name, _, value = line.partition(b":")
            if name.strip().lower() == b"content-length":
                length = int(value.strip())
        while len(body) < length:
            chunk = conn.recv(65536)
            if not chunk:
                break
            body += chunk
        return head + b"\r\n\r\n" + body

    def close(self):
        """Stop accepting connections."""
        self.listener.close()
