import datetime
import http.server
import ssl
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fx"
CERT = HERE / "cert.pem"
KEY = HERE / "key.pem"
GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
       b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


def make_certificate():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=30))
            .sign(key, hashes.SHA256()))
    CERT.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    KEY.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass

    def end_headers(self):
        if self.path.startswith(("/p.gif", "/x.gif")):
            host = self.headers.get("Host", "").split(":")[0]
            self.send_header("Set-Cookie", f"trk=1; Domain={host}; Path=/; SameSite=None; Secure")
        super().end_headers()

    def do_GET(self):
        if self.path.startswith(("/p.gif", "/x.gif")):
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(GIF)))
            self.end_headers()
            self.wfile.write(GIF)
            return
        super().do_GET()


def serve(port, tls):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    if tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(CERT), str(KEY))
        server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if not KEY.exists():
    make_certificate()
threading.Thread(target=serve, args=(8766, True), daemon=True).start()
print("Serving http://localhost:8765 and https on 8766. Press Ctrl+C to stop.")
serve(8765, False)