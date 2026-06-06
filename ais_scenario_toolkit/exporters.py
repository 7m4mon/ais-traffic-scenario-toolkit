from __future__ import annotations

import base64
import hashlib
import os
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse


class Exporter:
    def send(self, message: str) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


@dataclass
class DryRunExporter(Exporter):
    prefix: str = ""

    def send(self, message: str) -> None:
        print(f"{self.prefix}{message}")


@dataclass
class UdpExporter(Exporter):
    host: str
    port: int
    sock: socket.socket = field(default_factory=lambda: socket.socket(socket.AF_INET, socket.SOCK_DGRAM))

    def send(self, message: str) -> None:
        self.sock.sendto((message + "\r\n").encode("ascii", errors="ignore"), (self.host, self.port))

    def close(self) -> None:
        self.sock.close()


class TcpServerExporter(Exporter):
    def __init__(self, host: str, port: int) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen()
        self.sock.setblocking(False)
        self.clients: list[socket.socket] = []

    def send(self, message: str) -> None:
        self._accept_waiting()
        data = (message + "\r\n").encode("ascii", errors="ignore")
        live: list[socket.socket] = []
        for client in self.clients:
            try:
                client.sendall(data)
                live.append(client)
            except OSError:
                client.close()
        self.clients = live

    def close(self) -> None:
        for client in self.clients:
            client.close()
        self.sock.close()

    def _accept_waiting(self) -> None:
        while True:
            try:
                client, _addr = self.sock.accept()
            except BlockingIOError:
                return
            client.setblocking(False)
            self.clients.append(client)


class SerialExporter(Exporter):
    def __init__(self, port: str, baud: int = 4800) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Serial output requires pyserial. Install with: pip install pyserial") from exc
        self.serial = serial.Serial(port=port, baudrate=baud, timeout=0)

    def send(self, message: str) -> None:
        self.serial.write((message + "\r\n").encode("ascii", errors="ignore"))

    def close(self) -> None:
        self.serial.close()


class WebSocketTextExporter(Exporter):
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "ws":
            raise ValueError("Only ws:// WebSocket URLs are supported without external dependencies")
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 80
        self.path = parsed.path or "/"
        if parsed.query:
            self.path += "?" + parsed.query
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self._handshake()

    def send(self, message: str) -> None:
        payload = message.encode("utf-8")
        header = bytearray([0x81])
        mask_bit = 0x80
        length = len(payload)
        if length < 126:
            header.append(mask_bit | length)
        elif length < 65536:
            header.extend([mask_bit | 126, (length >> 8) & 0xFF, length & 0xFF])
        else:
            header.append(mask_bit | 127)
            header.extend(length.to_bytes(8, "big"))
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def close(self) -> None:
        self.sock.close()

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self.sock.recv(4096)
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest())
        if b" 101 " not in response or expected not in response:
            raise RuntimeError("WebSocket handshake failed")


def parse_host_port(value: str) -> tuple[str, int]:
    host, port = value.rsplit(":", 1)
    return host, int(port)
