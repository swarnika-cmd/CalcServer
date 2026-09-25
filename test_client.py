import socket

def send_request(sock: socket.socket, path: str) -> str:
    request = f"GET {path} HTTP/1.1\r\nHost: localhost:8080\r\n\r\n"
    sock.send(request.encode())
    response = sock.recv(4096)
    return response.decode()


def main():
    sock = socket.create_connection(("localhost", 8080))

    print("--- request 1 ---")
    print(send_request(sock, "/add?a=3&b=4"))

    print("--- request 2 (same connection) ---")
    print(send_request(sock, "/mul?a=5&b=6"))

    print("--- request 3 (same connection) ---")
    print(send_request(sock, "/div?a=8&b=0"))

    print("socket still open?", sock.fileno() != -1)
    sock.close()


if __name__ == "__main__":
    main()