# pylint: skip-file
import socket
import threading
import os
import sys
import time
import struct
import random
import pathlib

# def ackHandler(server_socket):
def ackHandler(server_socket, ack_ind, seq_no, client_address):
    # global ack_ind
    # global received_sequences
    # global client_address

    # while True:
    if ack_ind < len(received_sequences):
        # print(f"ack_ind: {ack_ind}, len: {len(received_sequences)}")
        # print(f"acked seq: {seq_no}")
        ack_packet = struct.pack('!IHH', seq_no, 0, 0b1010101010101010)
        server_socket.sendto(ack_packet, client_address)
        # print(f"--ACK sent: {seq_no}")
        ack_ind += 1
    # else:
    #     time.sleep(0.05)


def isChecksumValid(data, receivedCheckSum):
    """
    CHANGE THIS NOT WORKING!
    """
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
    # print(f"checksum: {checksum == receivedCheckSum}")
    return checksum == receivedCheckSum


def receivingHandler(server_socket):
    global received_sequences
    global client_address
    global expected_seq
    while True:
        client_packet, client_address = server_socket.recvfrom(PACKET_SIZE)
        # IHH -> 4 + 2 + 2 bytes
        header = struct.unpack('!IHH', client_packet[:8])
        data = client_packet[8:].decode()
        if not data:
            break
        loss_val = random.random()
        # print("loss_thresh: ", loss_thresh, LOSS_PROB, isChecksumValid(data, header[1]))
        seq_no = header[0]
        if (    header[2] == 0b0101010101010101 and loss_val > LOSS_PROB and isChecksumValid(data, header[1])): 
                # and isChecksumValid(data, header[1])):
            # if seq_no not in received_sequences:
            if seq_no <= expected_seq:
                if seq_no not in received_sequences:
                    received_sequences.append(seq_no)
                    with open(FILE_NAME, 'a') as file:
                        file.write(data)
                expected_seq = seq_no + 1
                ackHandler(server_socket, ack_ind, seq_no, client_address)
            
            # elif seq_no < expected_seq:
            #     # signifies retransmission
            #     expected_seq = seq_no + 1
            #     ackHandler(server_socket, ack_ind, seq_no, client_address)
                     
            # else:
            #     # retransmitted packet need retransmitted ACK
            #     ind = 0
            #     for seq in received_sequences:
            #         if seq == seq_no:
            #             break
            #         ind += 1
        else:
            print(f"dropped: {seq_no}")
            expected_seq = seq_no
        # time.sleep(0.05)

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
expected_seq = 0

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((socket.gethostname(), SERVER_PORT))
print(f"Server connected at port: {SERVER_PORT}")

# deleting already existing file
old_file = pathlib.Path(FILE_NAME)
if old_file.is_file():  # or p.is_dir() to see if it is a directory
    os.remove(FILE_NAME)
# file_thread = threading.Thread(target=writeFile)
# ack_thread = threading.Thread(target=ackHandler, args=(server_socket,))
# ack_thread.start()
# receiver_thread = threading.Thread(target=receivingHandler, args=(server_socket,))
# receiver_thread.start()
# main thread for acks
receivingHandler(server_socket)
# ackHandler(server_socket)
print("Receiving completed")
