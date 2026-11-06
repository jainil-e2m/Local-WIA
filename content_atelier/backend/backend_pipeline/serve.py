"""The API's process, the image's default command (plan 0.B7): uvicorn on one socket that takes IPv6 and IPv4.

Railway's private network, which the Frontend uses to reach the API, is IPv6 only; a local stack, a health check on
127.0.0.1 and any IPv4 proxy are not. `uvicorn --host ::` does not serve both: asyncio sets IPV6_V6ONLY on every IPv6
socket it binds, so the API answered IPv6 only and refused the local Frontend, the compose health check and every IPv4
client (found by the N1 shakedown, 23 October). Here the socket is made dual stack before uvicorn receives it. A
host without IPv6 gets an IPv4 socket on every interface. The platform's port is `$PORT` (8000 by default).

The reads are Python work, so one process serves one core's worth however many cores the host has: on 3 November a few
people on Weekly Studio held the API at one of its eight cores and every screen timed out. `$WEB_CONCURRENCY` processes (3
by default) share the socket.
"""
from __future__ import annotations

import os
import socket

import uvicorn
from uvicorn.supervisors import Multiprocess

APP = "backend_pipeline.api:app"
DEFAULT_WORKERS = 3


def listening_socket(port: int) -> socket.socket:
    """A listening socket on every interface, IPv6 and IPv4 (an IPv4 client appears as ::ffff:a.b.c.d)."""
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    except OSError:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
    else:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(("::", port))
    sock.listen(2048)
    sock.set_inheritable(True)
    return sock


def main() -> None:
    port = int(os.environ.get("PORT") or 8000)
    workers = int(os.environ.get("WEB_CONCURRENCY") or DEFAULT_WORKERS)
    config = uvicorn.Config(APP, workers=workers)
    server = uvicorn.Server(config)
    sock = listening_socket(port)
    if workers > 1:
        Multiprocess(config, target=server.run, sockets=[sock]).run()
    else:
        server.run(sockets=[sock])


if __name__ == "__main__":
    main()
