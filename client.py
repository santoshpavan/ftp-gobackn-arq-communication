# pylint: skip-file
import socket
import sys
import threading
import time
import struct

def ackHandler(client_socket):
    # listens for acknowledgments
    global timer
    global start_index
    global total_data
    global is_file_sent
    global is_file_read
    global timer_lock

    while not is_file_sent:
        if is_file_read and timer[len(timer) - 1] == 'a':
            # ACK'ed the entire file
            is_file_sent = True
            break
        ack_packet, address = client_socket.recvfrom(ACK_SIZE)
        header = struct.unpack('!IHH', ack_packet[:8])
        # basic validity check
        if header[1] == 0 and header[2] == 0b1010101010101010:
            sequence_number = header[0]
            # updating the status
            timer_lock.acquire()
            if total_data and start_index < len(timer) and timer[start_index] != 'n':
                # cumulative ACKs
                while start_index < len(timer) and start_index <= transmission_index:
                    timer[start_index] = 'a'
                    if total_data[start_index][1] == sequence_number:
                        start_index += 1
                        break
                    start_index += 1
            
            timer_lock.release()


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

def createPacket(transmission_index, total_data):
    # IHH -> 4 + 2 + 2 bytes
    header = struct.pack('!IHH', total_data[transmission_index][1], computeCheckSum(total_data[transmission_index][0]), 0b0101010101010101)
    total_packet = header + str(total_data[transmission_index][0]).encode()
    return total_packet

def isStartTimedOut(start_index, timer):
    time_now = round(time.time(), 2)
    difference = 0
    if timer[start_index] != 'n':
        difference = time_now - timer[start_index]
    return difference >= TIMER

def transmissionHandler(client_socket):
    # transmits data
    global total_data
    global start_index
    global transmission_index
    global timer
    global is_file_sent
    global timer_lock

    while not is_file_sent:
        timer_lock.acquire()
        if total_data and transmission_index < len(total_data) and transmission_index < start_index + WINDOW_SIZE :
            # check if timeout
            if start_index < len(timer) and timer[start_index] != 'n' and isStartTimedOut(start_index, timer):
                # retransmit
                print(f"Timeout, Sequence Number = {total_data[start_index][1]}")
                transmission_index = start_index
            # create packet
            packet = createPacket(transmission_index, total_data)
            # send the data
            client_socket.sendto(packet, (socket.gethostname(), 7735))
            # update timer of transmission_index
            timer[transmission_index] = round(time.time())
            transmission_index += 1
        elif start_index < len(total_data) and isStartTimedOut(start_index, timer):
            # check for timeout
            # print(f"2Timeout, Sequence Number = {total_data[start_index][1]}")
            transmission_index = start_index
        timer_lock.release()

def readFile(file_ptr=0):
    # reading the data from the file
    global total_data
    global is_file_read
    global timer
    seg_no = 0

    while not is_file_read:
        with open(FILE_NAME) as file:
            # setting to continue where we left off
            file.seek(file_ptr)
            data = file.read(MSS)
            if not data:
                # file has been read completely
                is_file_read = True
                break
            file_ptr = file.tell()
        total_data.append([data, seg_no])
        seg_no += 1
        timer.append('n')


"""
Command:
Simple_ftp_server server-host-name server-port# file-name N MSS
"""
# checking validity of command
if len(sys.argv) != 7 or sys.argv[1] != "Simple_ftp_server":
    print("Please enter correct command")
    sys.exit()

"""
Global variables
"""
# time in milliseconds
SERVER_HOST = sys.argv[2]
SERVER_PORT = int(sys.argv[3])
FILE_NAME = sys.argv[4]
WINDOW_SIZE = int(sys.argv[5])
MSS = int(sys.argv[6])

CLIENT_PORT  = 1234
BUFFER_SIZE = MSS * 100
ACK_SIZE = 8192
TIMER = 1

# to keep track of the file reading buffer
file_buffer_size = 0
# the data to be transmitted
total_data = []
# to keep track of the file reading and sending
is_file_read = False
is_file_sent = False

"""
timer - track the timers of each transmission
Following states:   n - not assigned
                    a - acknowledged
                    [counter(ms), sent_time(ms)] - sent but not acknowledged
"""
timer = []
timer_lock = threading.RLock()
# indices required for transmission
start_index = 0
transmission_index = 0

# UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.bind((socket.gethostname(), CLIENT_PORT))
print(f"Connected to the server at port: {SERVER_PORT}")

file_thread = threading.Thread(target=readFile)
ack_thread = threading.Thread(target=ackHandler, args=(client_socket,))
START_TIME = time.time()
file_thread.start()
ack_thread.start()

# main thread is transmitting
transmissionHandler(client_socket)
# sending termination packet
header = struct.pack('!IHH', total_data[-1][1], computeCheckSum(total_data[-1][0]), 0b0101010101010101)
client_socket.sendto(header, (socket.gethostname(), 7735))

# terminate
client_socket.close()

END_TIME = time.time()
print("Transfer completed. Time taken: ", round(END_TIME - START_TIME, 5))

# ----
# # pylint: skip-file
# import socket
# import sys
# import threading
# import time
# import struct

# def ackHandler(client_socket):
#     # listens for acknowledgments
#     # global timer
#     # global start_index
#     global total_data
#     global is_file_sent
#     global is_file_read
#     global timer_lock

#     while not is_file_sent:
#         # print("len::",len(total_data), is_file_read)
#         if is_file_read and not total_data:
#             print('----- SENT DONE')
#             is_file_sent = True
#             break
#         ack_packet, address = client_socket.recvfrom(ACK_SIZE)
#         header = struct.unpack('!IHH', ack_packet[:8])
#         # basic validity check
#         if header[1] == 0 and header[2] == 0b1010101010101010:
#             sequence_number = header[0]
#             # print("ACK: ", sequence_number)
#             # find the sequence number
#             timer_lock.acquire()
#             for i in range(len(total_data)):
#                 if total_data[i][1] == sequence_number:
#                     total_data = total_data[i+1:]
#                     break
#             timer_lock.release()
        
#     """
#     while not is_file_sent:
#         if is_file_read and timer[len(timer) - 1] == 'a':
#             # ACK'ed the entire file
#             is_file_sent = True
#             break
#         ack_packet, address = client_socket.recvfrom(ACK_SIZE)
#         header = struct.unpack('!IHH', ack_packet[:8])
#         # basic validity check
#         if header[1] == 0 and header[2] == 0b1010101010101010:
#             sequence_number = header[0]
#             # updating the status
#             timer_lock.acquire()
#             if total_data and start_index < len(timer) and timer[start_index] != 'n':
#                 # cumulative ACKs
#                 while start_index < len(timer) and start_index <= transmission_index:
#                     timer[start_index] = 'a'
#                     if total_data[start_index][1] == sequence_number:
#                         start_index += 1
#                         break
#                     start_index += 1
            
#             timer_lock.release()
#     """

# def computeCheckSum(data):
#     checksum = 0
#     # checking if this is even
#     if len(data)%2 != 0:
#         data += '0'
#     for i in range(0, len(data), 2):
#         element = ord(data[i]) + (ord(data[i+1]) << 8)
#         sum = element + checksum
#         carry = sum >> 16
#         sum = sum & 0xFFFF
#         # adding the carry to the LSB
#         checksum = sum + carry
#     # 1's compliment
#     checksum = (~checksum) & 0xFFFF
#     return checksum
# """
# def createPacket(transmission_index, total_data):
#     # IHH -> 4 + 2 + 2 bytes
#     header = struct.pack('!IHH', total_data[transmission_index][1], computeCheckSum(total_data[transmission_index][0]), 0b0101010101010101)
#     total_packet = header + str(total_data[transmission_index][0]).encode()
#     return total_packet
# """
# def createPacket(data, sequence_number):
#     header = struct.pack('!IHH', sequence_number, computeCheckSum(data), 0b0101010101010101)
#     total_packet = header + str(data).encode()
#     return total_packet

# """
# def isStartTimedOut(start_index, timer):
#     time_now = round(time.time(), 2)
#     difference = 0
#     if timer[start_index] != 'n':
#         difference = time_now - timer[start_index]
#     return difference >= TIMER
# """
# def isStartTimedOut():
#     if total_data:
#         # MIGHT NEED A LOCK HERE. NOT SURE!
#         return time.time() - total_data[0][2] > TIMER
#     return False

# def transmissionHandler(client_socket):
#     # transmits data
#     global total_data
#     # global start_index
#     # global transmission_index
#     # global timer
#     global is_file_sent
#     global timer_lock
#     global is_file_read

#     file_ptr = 0
#     sequence_number = 0
#     file = open(FILE_NAME)
#     while not is_file_sent:
#         # print(len(total_data))
#         # check for retransmission requirements
#         # if total_data:
#         #     print(total_data[0][2] - round(time.time()) >= TIMER)
#         if len(total_data) == WINDOW_SIZE:
#             # print(len(total_data))
#             time.sleep(0.05)
#             # continue
#         # print(len(total_data))
#         # elif isStartTimedOut():
#         #     print(f"Timeout, Sequence Number = {total_data[0][1]}")
#         #     # retransmissions
#         #     timer_lock.acquire()
#         #     for i in range(len(total_data)):
#         #         packet_data = total_data[i]
#         #         packet = createPacket(packet_data[0], packet_data[1])
#         #         print("tx: ", packet_data[1])
#         #         client_socket.sendto(packet, (socket.gethostname(), SERVER_PORT))
#         #         # timer_lock.acquire()
#         #         total_data[i][2] = time.time()
#         #         # timer_lock.release()
#         #     timer_lock.release()
#         #     time.sleep(0.01)
#         #     # continue
#         elif not is_file_read and len(total_data) < WINDOW_SIZE:
#             # read the file of MSS size
#             # file_ptr, data = readFile(file_ptr)
#             data = file.read(MSS)
#             if not data:
#                 print("------READ DONE!")
#                 is_file_read = True
#                 file.close()
#                 continue
#             # send the data
#             packet = createPacket(data, sequence_number)
#             # print("tx: ", sequence_number)
#             client_socket.sendto(packet, (socket.gethostname(), SERVER_PORT))
#             timer_lock.acquire()
#             total_data.append([data, sequence_number, time.time()])
#             timer_lock.release()
#             sequence_number += 1
#         """
#         timer_lock.acquire()
#         if total_data and transmission_index < len(total_data) and transmission_index < start_index + WINDOW_SIZE :
#             # check if timeout
#             if start_index < len(timer) and timer[start_index] != 'n' and isStartTimedOut(start_index, timer):
#                 # retransmit
#                 print(f"Timeout, Sequence Number = {total_data[start_index][1]}")
#                 transmission_index = start_index
#             # create packet
#             packet = createPacket(transmission_index, total_data)
#             # send the data
#             client_socket.sendto(packet, (socket.gethostname(), 7735))
#             # update timer of transmission_index
#             timer[transmission_index] = round(time.time())
#             transmission_index += 1
#         elif start_index < len(total_data) and isStartTimedOut(start_index, timer):
#             # check for timeout
#             # print(f"2Timeout, Sequence Number = {total_data[start_index][1]}")
#             transmission_index = start_index
#         timer_lock.release()
#         """

# def readFile(file_ptr=0):
#     # reading the data from the file
#     with open(FILE_NAME) as file:
#         file.seek(file_ptr)
#         data = file.read(MSS)
#         file_ptr = file.tell()
#     return file_ptr, data

# """
# def readFile(file_ptr=0)::
#     # reading the data from the file
#     global total_data
#     global is_file_read
#     global timer
#     seg_no = 0
#     while not is_file_read:
#         with open(FILE_NAME) as file:
#             # setting to continue where we left off
#             file.seek(file_ptr)
#             data = file.read(MSS)
#             if not data:
#                 # file has been read completely
#                 is_file_read = True
#                 break
#             file_ptr = file.tell()
#         total_data.append([data, seg_no])
#         seg_no += 1
#         timer.append('n')
# """

# """
# Command:
# Simple_ftp_server server-host-name server-port# file-name N MSS
# """
# # checking validity of command
# if len(sys.argv) != 7 or sys.argv[1] != "Simple_ftp_server":
#     print("Please enter correct command")
#     sys.exit()

# """
# Global variables
# """
# # time in milliseconds
# SERVER_HOST = sys.argv[2]
# SERVER_PORT = int(sys.argv[3])
# FILE_NAME = sys.argv[4]
# WINDOW_SIZE = int(sys.argv[5])
# MSS = int(sys.argv[6])

# CLIENT_PORT  = 1234
# BUFFER_SIZE = MSS * 100
# ACK_SIZE = 8192
# TIMER = 1

# # to keep track of the file reading buffer
# file_buffer_size = 0
# # the data to be transmitted
# total_data = []
# # to keep track of the file reading and sending
# is_file_read = False
# is_file_sent = False

# """
# timer - track the timers of each transmission
# Following states:   n - not assigned
#                     a - acknowledged
#                     [counter(ms), sent_time(ms)] - sent but not acknowledged
# """
# timer = []
# timer_lock = threading.RLock()
# # indices required for transmission
# start_index = 0
# transmission_index = 0

# # UDP
# client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# client_socket.bind((socket.gethostname(), CLIENT_PORT))
# # client_socket.settimeout(32)
# print(f"Connected to the server at port: {SERVER_PORT}")

# g = 0
# p = 0
# while True:
#     with open(FILE_NAME) as file:
#         file.seek(p)
#         data = file.read(MSS)
#         p = file.tell()
#     if not data:
#         break
#     g += 1
# print("--------FINAL NO:", g-1)

# # file_thread = threading.Thread(target=readFile)
# ack_thread = threading.Thread(target=ackHandler, args=(client_socket,))
# tx_thread = threading.Thread(target=transmissionHandler, args=(client_socket,))
# START_TIME = time.time()
# # file_thread.start()
# ack_thread.start()
# tx_thread.start()
# # main thread is transmitting
# # transmissionHandler(client_socket)
# # sending termination packet
# flag = 0
# RTO = 0.02
# def retransmit():
#     timer_lock.acquire()
#     if isStartTimedOut():
#         print(f"Timeout, Sequence Number = {total_data[0][1]}")
#         # retransmissions
#         for i in range(len(total_data)):
#             packet_data = total_data[i]
#             packet = createPacket(packet_data[0], packet_data[1])
#             print("retx: ", packet_data[1])
#             client_socket.sendto(packet, (socket.gethostname(), SERVER_PORT))
#             # timer_lock.acquire()
#             total_data[i][2] = time.time()
#             # timer_lock.release()
#         timer_lock.release()
#         # time.sleep(0.01)

# while flag == 0:
#     # if tx_thread.is_alive():
#         # time.sleep(RTO)
#     retransmit()
#     #     flag = 0
#     #     continue
#     # if ack_thread.is_alive():
#     #     time.sleep(RTO)
#     #     retransmit()
#     #     flag = 0
#     #     continue
#     if not tx_thread.is_alive() and not ack_thread.is_alive():
#         flag = 1
#     else:
#         time.sleep(0.05)

# tx_thread.join()
# ack_thread.join()

# # header = struct.pack('!IHH', total_data[-1][1], computeCheckSum(total_data[-1][0]), 0b0101010101010101)
# header = struct.pack('!IHH', 0, 0, 0b0101010101010101)
# client_socket.sendto(header, (socket.gethostname(), 7735))

# END_TIME = time.time()

# # terminate
# client_socket.close()
# print("Transfer completed. Time taken: ", round(END_TIME - START_TIME, 5), socket.gethostname())

# ----