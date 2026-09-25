import socket


def send_request(sock: socket.socket, path: str) -> tuple[int, str]:
    """Send one GET request on an existing socket, return (status_code, body)."""
    request = f"GET {path} HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
    sock.send(request.encode())

    # Read the response. A single recv() is good enough here because our
    # bodies are tiny and fit in one packet -- but note this is the same
    # "assume it all arrives in one recv()" shortcut the server used in M1,
    # and it's exactly what you should NOT rely on for anything larger.
    raw = sock.recv(4096).decode()

    head, _, body = raw.partition("\r\n\r\n")
    status_line = head.split("\r\n")[0]        # "HTTP/1.1 200 OK"
    status_code = int(status_line.split(" ")[1])

    return status_code, body


def check(sock, path, expected_status, expected_body=None, label=""):
    status, body = send_request(sock, path)
    ok = (status == expected_status) and (expected_body is None or body == expected_body)
    result = "PASS" if ok else "FAIL"
    print(f"[{result}] {label or path}  ->  got ({status}, {body!r})  expected ({expected_status}, {expected_body!r})")
    return ok


def main():
    sock = socket.create_connection(("localhost", 8080))

    results = []
    results.append(check(sock, "/add?a=3&b=4",   200, "7"))
    results.append(check(sock, "/sub?a=10&b=4",  200, "6"))
    results.append(check(sock, "/mul?a=3&b=4",   200, "12"))
    results.append(check(sock, "/div?a=8&b=4",   200, "2.0"))
    results.append(check(sock, "/div?a=8&b=0",   400))
    results.append(check(sock, "/add?a=3",       400, label="missing param b"))
    results.append(check(sock, "/mod?a=3&b=4",   404, label="unknown route"))
    results.append(check(sock, "/add?a=x&b=4",   400, label="non-integer param"))

    still_open = sock.fileno() != -1
    print(f"\nsocket still open after {len(results)} requests: {still_open}")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")

    sock.close()


if __name__ == "__main__":
    main()