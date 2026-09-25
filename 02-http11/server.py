import socket

HOST, PORT = "0.0.0.0", 8080

OPERATIONS = {
    "/add": lambda a, b: a + b,
    "/sub": lambda a, b: a - b,
    "/mul": lambda a, b: a * b,
    "/div": lambda a, b: a / b,
}


def parse_request(raw: bytes):
    head = raw.decode("iso-8859-1")
    lines = head.split("\r\n")

    request_line = lines[0]
    method, target, version = request_line.split(" ")

    headers = {}
    for line in lines[1:]:
        if not line:
            continue
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()

    path, _, query = target.partition("?")
    return method, path, query, headers


def parse_query(query: str) -> dict:
    params = {}
    if not query:
        return params
    for pair in query.split("&"):
        key, _, value = pair.partition("=")
        params[key] = value
    return params


def build_response(status_code: int, status_text: str, body: str, close: bool = False) -> bytes:
    body_bytes = body.encode("utf-8")
    conn_header = "Connection: close\r\n" if close else ""
    head = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: text/plain\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"{conn_header}\r\n"
    )
    return head.encode("utf-8") + body_bytes


def handle_request(method: str, path: str, query: str, headers: dict, close: bool = False) -> bytes:
    if method != "GET":
        return build_response(405, "Method Not Allowed", "only GET is supported", close=close)
    if "host" not in headers:
        return build_response(400, "Bad Request", "missing Host header", close=close)
    if path not in OPERATIONS:
        return build_response(404, "Not Found", f"no such operation: {path}", close=close)

    params = parse_query(query)
    if "a" not in params or "b" not in params or params["a"] == "" or params["b"] == "":
        return build_response(400, "Bad Request", "missing parameter a or b", close=close)

    try:
        a = int(params["a"])
        b = int(params["b"])
    except ValueError:
        return build_response(400, "Bad Request", "a and b must be integers", close=close)

    if path == "/div" and b == 0:
        return build_response(400, "Bad Request", "division by zero", close=close)

    result = OPERATIONS[path](a, b)
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    return build_response(200, "OK", str(result), close=close)


def handle_connection(conn: socket.socket):
    """
    Serve MULTIPLE requests off the same connection, in a loop.
    buffer holds bytes we've read but not yet turned into a full request.
    """
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    buffer = b""

    while True:
        # 1. Do we already have a full request sitting in buffer from last read?
        end = buffer.find(b"\r\n\r\n")

        if end == -1:
            # No complete request yet -> read more bytes and append
            chunk = conn.recv(4096)
            if chunk == b"":
                # Client closed the connection. Nothing more to do.
                break
            buffer += chunk
            continue  # go re-check buffer for a complete request

        # 2. We have one full request: buffer[0:end+4] (request line+headers+\r\n\r\n)
        request_bytes = buffer[:end + 4]
        buffer = buffer[end + 4:]   # keep leftover bytes for the NEXT request

        try:
            method, path, query, headers = parse_request(request_bytes)
            should_close = headers.get("connection", "").lower() == "close"
            response = handle_request(method, path, query, headers, close=should_close)
        except Exception:
            should_close = True
            response = build_response(400, "Bad Request", "malformed request", close=True)

        conn.sendall(response)
        if should_close:
            break

    conn.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Listening on {PORT}")

    while True:
        conn, addr = server.accept()
        handle_connection(conn)


if __name__ == "__main__":
    main()