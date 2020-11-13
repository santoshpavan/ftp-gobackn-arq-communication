# pylint: skip-file
import socket
import struct
import sys
import time
import threading

def acknowledgementHandler():
    # ack handling thread
    global is_file_sent
    global total_data
    is_file_confirmed = False
    while not is_file_confirmed:
        if is_file_sent and not total_data:
            is_file_confirmed = True
            continue
        ack_packet, server_address = client_socket.recvfrom(BUFFER_SIZE)
        header = struct.unpack('!IHH', ack_packet[0:8])
        # sanity check
        if header[1] == 0 or header[2] == 0b1010101010101010:
            sequence_number = header[0]
            data_lock.acquire()
            # finding index for this ack
            for i in range(len(total_data)):
                if total_data[i][1] == sequence_number:
                    # No Comulative ACK as Selective Repeat Request
                    del total_data[i]
                    break
            data_lock.release()

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

def transmissionHandler():
    # transmitting thread
    global is_file_sent
    global total_data
    global file
    sequence_number = 0
    while True:
        while len(total_data) == WINDOW_SIZE:
            time.sleep(0.05)
        if is_file_sent:
            # IHH -> 4 + 2 + 2 bytes
            header = struct.pack('!IHH', sequence_number, computeCheckSum(""), 0b0101010101010101)
            data_lock.acquire()
            # sending the packet
            total_data.append([header, sequence_number, time.time()])
            client_socket.sendto(header, (socket.gethostname(), SERVER_PORT))
            data_lock.release()
            break
        # reading data byte basis
        data = ""
        while MSS != len(data):
            byte = file.read(1)
            if byte == '':
                is_file_sent = True
                break
            data += byte
        if len(data) > 0:
            # IHH -> 4 + 2 + 2 bytes
            header = struct.pack('!IHH', sequence_number, computeCheckSum(data), 0b0101010101010101)
            total_packet = header + str(data).encode()
            data_lock.acquire()
            # sending the packet
            total_data.append([total_packet, sequence_number, time.time()])
            client_socket.sendto(total_packet, (socket.gethostname(), SERVER_PORT))
            data_lock.release()
            sequence_number += 1

def isStartTimedOut():
    global total_data
    if total_data:
        return (time.time() - total_data[0][2]) > TIMER
    return False

def retransmissionHandler():
    global total_data
    print("Timeout, sequence number = ", total_data[0][1])
    data_lock.acquire()
    for tx_id in range(len(total_data)):
        # sending packet
        total_data[tx_id][2] = time.time()
        client_socket.sendto(total_data[tx_id][0], (socket.gethostname(), SERVER_PORT))
    data_lock.release()

"""
Command:
Simple_ftp_server server-host-name server-port# file-name N MSS
"""
# checking validity of command
if len(sys.argv) != 7 or sys.argv[1] != "Simple_ftp_server":
    print("Please enter correct command")
    sys.exit()

# Global variables
SERVER_HOST = sys.argv[2]
SERVER_PORT = int(sys.argv[3])
FILENAME = str(sys.argv[4])
WINDOW_SIZE = int(sys.argv[5])
MSS = int(sys.argv[6])

total_data = []
TIMER = 1
CLIENT_PORT = 1234
data_lock = threading.RLock()
is_file_sent = False
# 8 bytes buffer size as header is 8 bytes
BUFFER_SIZE = 8192
file = open(FILENAME, "r")

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.bind((socket.gethostname(), CLIENT_PORT))

transmission_thread = threading.Thread(target=transmissionHandler)
acknowledgement_thread = threading.Thread(target=acknowledgementHandler)

start_time = time.time()

transmission_thread.start()
acknowledgement_thread.start()

# main thread to handler retransmits
main_terminate_flag = False
while not main_terminate_flag:
    if transmission_thread.is_alive():
        time.sleep(TIMER)
        if isStartTimedOut():
            retransmissionHandler()
    elif acknowledgement_thread.is_alive():
        time.sleep(TIMER)
        if isStartTimedOut():
            retransmissionHandler()
    elif not transmission_thread.is_alive() and not acknowledgement_thread.is_alive():
        main_terminate_flag = True

# joining the thread
transmission_thread.join()
acknowledgement_thread.join()

end_time = time.time()
time_difference = round(end_time - start_time, 5)
print("Total time taken to transfer data: ", time_difference)
client_socket.close()
