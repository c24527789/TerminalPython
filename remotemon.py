import argparse
import socket
import json
import struct
import subprocess
import ipaddress

from localNetwork import collect_network, display_network, save_json

# Protocol: 4-byte magic, 1-byte type, 4-byte JSON length (big-endian).
# Maximum JSON payload: 1 MiB. One request and response per connection.
MAGIC = b"NET1"
HEADER_FORMAT = "!4sBI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_SIZE = 1024 * 1024
REQUEST, RESPONSE, ERROR = 1, 2, 3


# Receive exactly the requested number of bytes.
def recv_exact(connection, size):
    data = b""
    while len(data) < size:
        chunk = connection.recv(min(4096, size - len(data)))
        if not chunk:
            raise ConnectionError("Incomplete message")
        data += chunk
    return data


# Convert a dictionary to JSON and send it with a binary header.
def send_message(connection, message_type, data):
    if message_type not in (REQUEST, RESPONSE, ERROR):
        raise ValueError("Unsupported message type")
    
    payload = json.dumps(data, allow_nan=False).encode("utf-8")
    if not 0 < len(payload) <= MAX_SIZE:
        raise ValueError("Invalid payload length")
    header = struct.pack(HEADER_FORMAT, MAGIC, message_type, len(payload))
    connection.sendall(header + payload)
    return len(payload)


# Reject non-standard JSON constants such as NaN and Infinity.
def invalid_json_number(value):
    raise ValueError("Invalid JSON number: " + value)


# Receive the header, validate it, then read and decode the JSON body.
def receive_message(connection, allowed_types):
    header = recv_exact(connection, HEADER_SIZE)
    magic, message_type, length = struct.unpack(HEADER_FORMAT, header)
    if magic != MAGIC:
        raise ValueError("Invalid header")
    if message_type not in allowed_types:
        raise ValueError("Unsupported message type")
    if not 0 < length <= MAX_SIZE:
        raise ValueError("Invalid payload length")
    payload = recv_exact(connection, length)
    data = json.loads(payload.decode("utf-8"), parse_constant=invalid_json_number)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return message_type, data, length


# Check the fields and data types expected by localNetwork.py.
def validate_network(network):
    if not isinstance(network, dict):
        raise ValueError("Invalid network data")
    if not isinstance(network.get("hostname"), str) or not network["hostname"]:
        raise ValueError("Invalid hostname")
    if not isinstance(network.get("interfaces"), list) or not isinstance(network.get("routes"), list):
        raise ValueError("Invalid interfaces or routes")

    for interface in network["interfaces"]:
        fields = ("name", "mtu", "mac", "state", "flags", "ip_addresses")
        if not isinstance(interface, dict) or not all(k in interface for k in fields):
            raise ValueError("Missing interface fields")
        if not isinstance(interface["name"], str) or not interface["name"]:
            raise ValueError("Invalid interface name")
        if type(interface["mtu"]) is not int or interface["mtu"] <= 0:
            raise ValueError("Invalid MTU")
        for key in ("mac", "state"):
            if interface[key] is not None and not isinstance(interface[key], str):
                raise ValueError("Invalid " + key)
        for key in ("flags", "ip_addresses"):
            if not isinstance(interface[key], list) or not all(isinstance(v, str) for v in interface[key]):
                raise ValueError("Invalid " + key)
        for address in interface["ip_addresses"]:
            ipaddress.ip_address(address)

    for route in network["routes"]:
        if not isinstance(route, dict) or not all(k in route for k in ("destination", "gateway", "interface")):
            raise ValueError("Missing route fields")
        if not isinstance(route["destination"], str):
            raise ValueError("Invalid destination")
        for key in ("gateway", "interface"):
            if route[key] is not None and not isinstance(route[key], str):
                raise ValueError("Invalid " + key)


# Server: accept one client, collect network data and send a response.
def run_server(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", port))
        server.listen(1)
        print("Server listening on port:", port)
        connection, address = server.accept()
        with connection:
            connection.settimeout(10)
            print("Client connected:", address)
            try:
                _, request, _ = receive_message(connection, (REQUEST,))
                if request != {"command": "GET_NETWORK"}:
                    raise ValueError("Invalid request")
                network = collect_network()
                validate_network(network)
                print("JSON bytes sent:", send_message(connection, RESPONSE, network))
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                # Try to report errors to the client before closing.
                try:
                    send_message(connection, ERROR, {"error": str(error)})
                except (OSError, ValueError):
                    pass
                raise
    # TODO: Accept multiple clients without restarting.


# Client: request network information and validate the response.
def run_client(server_ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect((server_ip, port))
        print("Connected to server:", server_ip)
        send_message(client, REQUEST, {"command": "GET_NETWORK"})
        message_type, network, size = receive_message(client, (RESPONSE, ERROR))
        print("JSON bytes received:", size)
        if message_type == ERROR:
            raise ValueError("Server error: " + str(network.get("error")))
        validate_network(network)
        print("Reception and validation successful")
        # TODO: Display network information using display_network().
        # TODO: Save network information using save_json().


# Read and validate arguments, then select server or client mode.
def main():
    parser = argparse.ArgumentParser(description="Remote Network Monitor")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-r", action="store_true", help="Server mode")
    mode.add_argument("-t", action="store_true", help="Client mode")
    parser.add_argument("-p", type=int, default=7777, help="TCP port")
    parser.add_argument("-ip", help="Server IPv4 address")
    args = parser.parse_args()
    if not 1 <= args.p <= 65535:
        parser.error("Invalid port number")
    if args.r and args.ip is not None:
        parser.error("-ip can only be used in client mode")
    server_ip = args.ip if args.ip is not None else "127.0.0.1"
    try:
        ipaddress.IPv4Address(server_ip)
    except ValueError:
        parser.error("Invalid IPv4 address")
    try:
        if args.r:
            run_server(args.p)
        else:
            run_client(server_ip, args.p)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print("Error:", error)
        if args.t:
            print("Reception or validation failed")
        return 1
    except KeyboardInterrupt:
        print("\nApplication stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())