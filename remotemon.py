import argparse
import socket
import json
import struct
import subprocess
import ipaddress

# Import functions from Part 1
from localNetwork import collect_network, display_network, save_json


# Application protocol settings
MAGIC = b"NET1"
HEADER_FORMAT = "!4sBI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_SIZE = 1024 * 1024

# Message types
REQUEST = 1
RESPONSE = 2
ERROR = 3


# Receive an exact number of bytes
def recv_exact(connection, size):

    # Create an empty byte string
    data = b""

    # Keep receiving until all bytes have arrived
    while len(data) < size:

        chunk = connection.recv(min(4096, size - len(data)))

        # Check if the connection has closed
        if not chunk:
            raise ConnectionError("Incomplete message")

        # Add received bytes to data
        data += chunk

    return data


# Send a message over the TCP connection
def send_message(connection, message_type, data):

    # Convert dictionary to JSON and encode as UTF-8
    payload = json.dumps(data).encode("utf-8")

    # Check that the payload size is valid
    if not 0 < len(payload) <= MAX_SIZE:
        raise ValueError("Invalid payload length")

    # Create the binary header
    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        message_type,
        len(payload)
    )

    # Send the header followed by the JSON payload
    connection.sendall(header + payload)


# Main program
def main():

    # Create the command-line argument parser
    parser = argparse.ArgumentParser(
        description="Remote Network Monitor"
    )

    # Only allow one mode to be selected
    mode = parser.add_mutually_exclusive_group(required=True)

    # Server mode
    mode.add_argument("-r", action="store_true")

    # Client mode
    mode.add_argument("-t", action="store_true")

    # Port number with a default of 7777
    parser.add_argument("-p", type=int, default=7777)

    # Server IP address
    parser.add_argument("-ip")

    # Read the command-line arguments
    args = parser.parse_args()

    # Validate the port number
    if not 1 <= args.p <= 65535:
        parser.error("Invalid port number")

    # IP address can only be used in client mode
    if args.r and args.ip is not None:
        parser.error("-ip can only be used in client mode")

    # Set the default server IP address
    if args.ip is None:
        args.ip = "127.0.0.1"

    # Validate the IP address
    try:
        ipaddress.IPv4Address(args.ip)

    except ValueError:
        parser.error("Invalid IP address")

    # Select server mode
    if args.r:
        print("Running in server mode")
        print("Port:", args.p)

    # Select client mode
    elif args.t:
        print("Running in client mode")
        print("Server IP:", args.ip)
        print("Port:", args.p)


# Start the main program
if __name__ == "__main__":
    main()