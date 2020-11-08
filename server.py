# pylint: skip-file
import socket
import threading
import os
import sys
import time
import struct
import random

def ackHandler(server_socket):
    global ack_ind
    global received_sequences
    global client_address

    while True:
        if ack_ind < len(received_sequences):
            ack_packet = struct.pack('!IHH', received_sequences[ack_ind], 0, 0b1010101010101010)
            server_socket.sendto(ack_packet, client_address)
            print(f"--ACK sent: {received_sequences[ack_ind]}")
            ack_ind += 1
        else:
            time.sleep(0.05)


def isChecksumValid(data, receivedCheckSum):
    checksum = 0
    val = len(data) % 2
    flag = 0
    if val != 0:
        flag = 1
    data = data + '0' if flag == 1 else data
    i = 0
    while i < len(data):
        blockSum = checksum + ord(data[i]) + (ord(data[i + 1]) << 8)
        checksum = (blockSum & 0xFFFF) + (blockSum >> 16)
        i += 2
    checksum = (~checksum) & 0xFFFF

    if checksum == receivedCheckSum:
        return True
    else:
        return False


def receivingHandler(server_socket):
    global received_sequences
    global client_address

    while True:
        client_packet, client_address = server_socket.recvfrom(PACKET_SIZE)
        # IHH -> 4 + 2 + 2 bytes
        header = struct.unpack('!IHH', client_packet[:8])
        data = client_packet[8:].decode()
        loss_thresh = random.random()
        print(header[0])
        if header[2] == 0b0101010101010101 and loss_thresh > LOSS_PROB and isChecksumValid(data, header[1]):
            received_sequences.append(header[0])
            with open(FILE_NAME, 'a') as file:
                file.write(data)
        time.sleep(0.05)

# taking inputs
if len(sys.argv) != 5 or sys.argv[1] != "Simple_ftp_server":
    print("Please enter correct command")
    sys.exit()

SERVER_PORT = int(sys.argv[2])
FILE_NAME = sys.argv[3]
LOSS_PROB = float(sys.argv[4])
PACKET_SIZE = 8192

# global variables
# received_data = []
# status = []
received_sequences = []
ack_ind = 0

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((socket.gethostname(), SERVER_PORT))
print(f"Server connected at port: {SERVER_PORT}")

# file_thread = threading.Thread(target=writeFile)
# ack_thread = threading.Thread(target=ackHandler, args=(server_socket,))
receiver_thread = threading.Thread(target=receivingHandler, args=(server_socket,))
receiver_thread.start()
# main thread for acks
ackHandler(server_socket)
