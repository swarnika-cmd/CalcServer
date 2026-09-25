import socket


def send_request(sock: socket.socket, path: str, method: str = "GET", include_host: bool = True) -> tuple[int, str]:
    """Send one request on an existing socket, return (status_code, body)."""
    headers = "Host: localhost:8080\r\n" if include_host else ""
    request = f"{method} {path} HTTP/1.1\r\n{headers}\r\n"
    sock.sendall(request.encode())

    # Read the response.
    raw = sock.recv(4096).decode()

    head, _, body = raw.partition("\r\n\r\n")
    status_line = head.split("\r\n")[0]        # "HTTP/1.1 200 OK"
    status_code = int(status_line.split(" ")[1])

    return status_code, body


def check(sock, path, expected_status, expected_body=None, label="", method="GET", include_host=True):
    status, body = send_request(sock, path, method=method, include_host=include_host)
    ok = (status == expected_status) and (expected_body is None or body == expected_body)
    result = "PASS" if ok else "FAIL"
    print(f"[{result}] {label or path}  ->  got ({status}, {body!r})  expected ({expected_status}, {expected_body!r})")
    return ok


def main():
    sock = socket.create_connection(("localhost", 8080))

    results = []
    # F-01 to F-04: Arithmetic operations
    results.append(check(sock, "/add?a=3&b=4",   200, "7",    label="F-01: /add?a=3&b=4"))
    results.append(check(sock, "/sub?a=10&b=4",  200, "6",    label="F-02: /sub?a=10&b=4"))
    results.append(check(sock, "/mul?a=3&b=4",   200, "12",   label="F-03: /mul?a=3&b=4"))
    results.append(check(sock, "/div?a=8&b=4",   200, "2",    label="F-04: /div?a=8&b=4 (integer output)"))
    # F-05: Division by zero
    results.append(check(sock, "/div?a=8&b=0",   400, label="F-05: division by zero"))
    # F-06: Missing or empty parameter
    results.append(check(sock, "/add?a=3",       400, label="F-06: missing param b"))
    results.append(check(sock, "/add?a=5&b=",    400, label="F-06: empty param b"))
    # F-07: Unknown operation
    results.append(check(sock, "/pow?a=2&b=8",   404, label="F-07: unknown route /pow"))
    # F-08: Method not allowed (only GET)
    results.append(check(sock, "/add?a=2&b=3",   405, method="POST", label="F-08: POST method not allowed"))
    # F-09: Missing Host header
    results.append(check(sock, "/add?a=2&b=3",   400, include_host=False, label="F-09: missing Host header"))
    # Non-integer parameters
    results.append(check(sock, "/add?a=x&b=4",   400, label="non-integer param"))

    still_open = sock.fileno() != -1
    print(f"\nsocket still open after {len(results)} requests: {still_open}")

    passed = sum(results)
    print(f"\n{passed}/{len(results)} checks passed")

    sock.close()


if __name__ == "__main__":
    main()