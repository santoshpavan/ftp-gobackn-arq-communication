# pylint: skip-file
import sys
import socket
import struct
import random
import os
import pathlib

def computeCheckSum(data):
    checksum = 0
    # checking if this is even
    if len(data)%2 != 0:
        data += '0'
    for i in range(0, len(data), 2):
        element = ord(data[i]) + (ord(data[i+1]) << 8)
        sum = element + checksum
        carry = sum >> 16
        sum = sum & 0xFFFF
        # adding the carry to the LSB
        checksum = sum + carry
    # 1's compliment
    checksum = (~checksum) & 0xFFFF
    return checksum

def receivingHandler(server_socket):
    file = open(FILE_NAME, "w")
    expected_seq = 0
    is_file_received = False
    while not is_file_received:
        packet, client_address = server_socket.recvfrom(BUFFER_SIZE)
        header = struct.unpack('!IHH', packet[0:8])
        sequence_number = header[0]
        # print("recv: ", sequence_number)
        data = packet[8:].decode()
        loss_value = random.random()
        # sanity check
        if header[2] == 0b0101010101010101 and computeCheckSum(data) == header[1] and sequence_number <= expected_seq:
            if loss_value > LOSS_PROB:
                server_socket.sendto(struct.pack('!IHH', sequence_number, 0, 0xAAAA), client_address)
                if len(data) > 0 and sequence_number == expected_seq:
                    file.write(data)
                    expected_seq = expected_seq + 1
                else:
                    file.close()
                    server_socket.close()
                    is_file_received = True
                    continue
            else:
                print("Packet loss, sequence number = ", sequence_number)

"""
Command:
Simple_ftp_server port# file-name p
python3 testserver.py Simple_ftp_server 7735 output.txt 0.07
"""

# taking inputs
if len(sys.argv) != 5 or sys.argv[1] != "Simple_ftp_server":
    print("Please enter correct command")
    sys.exit()

SERVER_PORT = int(sys.argv[2])
FILE_NAME = str(sys.argv[3])
LOSS_PROB = float(sys.argv[4])

# 8 bytes as header size
BUFFER_SIZE = 8192

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((socket.gethostname(), SERVER_PORT))

# deleting already existing file
old_file = pathlib.Path(FILE_NAME)
if old_file.is_file():
    os.remove(FILE_NAME)

receivingHandler(server_socket)

print("File tranfered successfully.")
