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

    data = b""

    # Keep receiving until all bytes have arrived
    while len(data) < size:

        chunk = connection.recv(min(4096, size - len(data)))

        # Check if the connection has closed
        if not chunk:
            raise ConnectionError("Incomplete message")

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


# Receive a message from a TCP connection
def receive_message(connection):

    # Receive the binary header
    header = recv_exact(connection, HEADER_SIZE)

    # Extract the values from the header
    magic, message_type, length = struct.unpack(
        HEADER_FORMAT, header
    )

    # Check the magic identifier
    if magic != MAGIC:
        raise ValueError("Invalid header")

    # Check the message length
    if not 0 < length <= MAX_SIZE:
        raise ValueError("Invalid message length")

    # Receive the JSON payload
    payload = recv_exact(connection, length)

    # Decode the JSON information
    data = json.loads(payload.decode("utf-8"))

    return message_type, data


# Server function
def run_server(port):

    # Create a TCP socket