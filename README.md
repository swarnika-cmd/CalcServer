# CalcServer — HTTP/1.1 Persistent Calculator Server

For this project, I built a raw-socket HTTP/1.1 calculator server from scratch in Python. I didn't use any web frameworks like Flask, FastAPI, or Python's built-in `http.server`—just basic TCP sockets (`import socket`).

---

## What I Built and Why

In older HTTP/1.0 servers, the flow is simple: the client connects, sends a request, the server responds, and the server immediately closes the socket. The client knows the response is finished simply because the connection closed.

In HTTP/1.1, connections are **persistent by default** (`keep-alive`). That means one single TCP connection stays open to handle multiple requests back-to-back. This introduces the hardest part of raw socket programming: **message framing**. Since the socket never closes between requests, the server has to know exactly where one request ends and where the next one begins, and the client needs an accurate `Content-Length` header to know when the response body is done reading.

---

## How I Implemented It

### 1. Persistent Connection & Buffer Management
Inside `handle_connection()`, I set up a loop around the client socket:
- I maintain an in-memory byte buffer (`buffer`).
- When `conn.recv()` reads incoming bytes, I append them to `buffer` and search for the HTTP delimiter `\r\n\r\n`.
- Once I find `\r\n\r\n`, I slice out that exact request `buffer[:end + 4]` and save any remaining bytes (`buffer[end + 4:]`) for the next request.
- This ensures that if multiple requests arrive in a single `recv()` call (or across multiple chunked reads), no data is lost or misaligned.

### 2. Request Parsing & Query Handling
- I split the request line into `method`, `target` (URL), and `HTTP/1.1`.
- I parsed headers into a dictionary and made the keys lowercase for easy lookup.
- I extracted query parameters from paths like `/add?a=10&b=5` using simple string partitioning.

### 3. Arithmetic Operations & Output Formatting
I mapped routes (`/add`, `/sub`, `/mul`, `/div`) to standard arithmetic lambdas:
- For division, if the result is a whole number (like `8 / 4 = 2.0`), I cast it to an integer (`2`) so the response body is `2` rather than `2.0`.
- If the divisor `b == 0`, I catch it and return a `400 Bad Request` with `division by zero`.

### 4. HTTP/1.1 Compliance & Error Handling
I made sure the server handles edge cases according to the HTTP/1.1 spec:
- **Mandatory Host Header:** If the request does not include a `Host:` header, the server returns `400 Bad Request`.
- **Method Restrictions:** Only `GET` is supported for calculations. Any other method (like `POST`) returns `405 Method Not Allowed`.
- **Missing or Bad Parameters:** If `a` or `b` is missing, blank (like `b=`), or cannot be parsed into an integer, the server returns `400 Bad Request`.
- **Unknown Routes:** Any unsupported path (like `/pow`) returns `404 Not Found`.
- **Always Send Content-Length:** Every response sends an accurate `Content-Length` based on the UTF-8 byte length of the body, which is required for persistent connections.

### 5. Socket Optimizations
- Enabled `socket.TCP_NODELAY` to disable Nagle's algorithm. Without this, sending small response headers and bodies back-to-back can hit the 40ms delayed-ACK penalty.
- Used `conn.sendall()` instead of `conn.send()` so Python guarantees all bytes are sent out before the next loop iteration.
- Handled `Connection: close` so if the client explicitly requests to close, the server includes `Connection: close` in the response and cleanly breaks the loop.

---

## File Structure

```text
Project1/
├── 02-http11/
│   ├── server.py        # Raw socket HTTP/1.1 server implementation
│   └── test_client.py   # Multi-assertion test suite over a single socket
├── .gitignore           # Ignores local PRD notes and Python cache files
└── README.md            # What you're reading right now
```

---

## How to Run

### Step 1: Start the Server
In your first terminal, run:
```bash
python 02-http11/server.py
```
You should see:
```text
Listening on 8080
```

### Step 2: Run the Tests
In a second terminal, run:
```bash
python 02-http11/test_client.py
```

### What the Test Suite Checks
The test client opens **a single TCP socket** (`socket.create_connection`) and fires 11 requests in sequence without reconnecting:
1. `GET /add?a=3&b=4` &rarr; `200 7`
2. `GET /sub?a=10&b=4` &rarr; `200 6`
3. `GET /mul?a=3&b=4` &rarr; `200 12`
4. `GET /div?a=8&b=4` &rarr; `200 2`
5. `GET /div?a=8&b=0` &rarr; `400 division by zero`
6. `GET /add?a=3` (missing parameter) &rarr; `400`
7. `GET /add?a=5&b=` (empty parameter) &rarr; `400`
8. `GET /pow?a=2&b=8` (unknown route) &rarr; `404`
9. `POST /add?a=2&b=3` (unsupported method) &rarr; `405`
10. `GET /add?a=2&b=3` (missing Host header) &rarr; `400`
11. `GET /add?a=x&b=4` (non-integer parameter) &rarr; `400`

At the end, it verifies `sock.fileno() != -1` to confirm that all 11 requests succeeded over the same underlying connection.
