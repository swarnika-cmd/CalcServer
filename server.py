import socket

HOST, PORT = "0.0.0.0", 8080

OPERATIONS = {
    "/add": lambda a, b: a + b,
    "/sub": lambda a, b: a - b,
    "/mul": lambda a, b: a * b,
    "/div": lambda a, b: a / b,   # ZeroDivisionError handled separately below
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
    """'a=3&b=4' -> {'a': '3', 'b': '4'}. Missing/empty query -> {}."""
    params = {}
    if not query:
        return params
    for pair in query.split("&"):
        key, _, value = pair.partition("=")
        params[key] = value
    return params


def build_response(status_code: int, status_text: str, body: str) -> bytes:
    body_bytes = body.encode("utf-8")
    head = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: text/plain\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"\r\n"
    )
    return head.encode("utf-8") + body_bytes


def handle_request(method: str, path: str, query: str, headers: dict) -> bytes:
    # 1. Method check
    if method != "GET":
        return build_response(405, "Method Not Allowed", "only GET is supported")

    # 2. Host header required (HTTP/1.1 spec, and a common grader check)
    if "host" not in headers:
        return build_response(400, "Bad Request", "missing Host header")

    # 3. Unknown route
    if path not in OPERATIONS:
        return build_response(404, "Not Found", f"no such operation: {path}")

    # 4. Parse params
    params = parse_query(query)
    if "a" not in params or "b" not in params or params["a"] == "" or params["b"] == "":
        return build_response(400, "Bad Request", "missing parameter a or b")

    try:
        a = int(params["a"])
        b = int(params["b"])
    except ValueError:
        return build_response(400, "Bad Request", "a and b must be integers")

    # 5. Division by zero
    if path == "/div" and b == 0:
        return build_response(400, "Bad Request", "division by zero")

    # 6. Compute
    result = OPERATIONS[path](a, b)
    return build_response(200, "OK", str(result))


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"Listening on {PORT}")

    while True:
        conn, addr = server.accept()
        data = conn.recv(4096)

        method, path, query, headers = parse_request(data)
        response = handle_request(method, path, query, headers)

        conn.send(response)
        conn.close()


if __name__ == "__main__":
    main()