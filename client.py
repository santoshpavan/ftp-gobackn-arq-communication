# pylint: skip-file
import socket
import sys
import threading
import time

"""
Command:
Simple_ftp_server server-host-name server-port# file-name N MSS
"""
# checking validity of command
if (sys.argv[0] != "Simple_ftp_server"):
    print("Please enter correct command")
    sys.exit()

# time in milliseconds
START_TIME = time.time_ns()*1000000
SERVER_HOST = sys.argv[1]
SERVER_PORT = int(sys.argv[2])
FILE_NAME = sys.argv[3]
WINDOW_SIZE = int(sys.argv[4])
MSS = int(sys.argv[5])

BUFFER_SIZE = MSS * 100
# timer in milli seconds
TIMER = 1000

def ackHandler(client_socket):
    # listens for acknowledgments
    global timer
    global start_index
    global file_buffer_size
    while True:
        ack_packet = client_socket.recv(64)
        # basic validity check
        if len(ack_packet) == 64 and ack_packet[32:48] == "0"*16 and ack_packet[48:] == "10"*8:
            sequence_number = int(ack_packet[:32], 2)
            # checking if it is the expected ACK
            if total_data[start_index] != 'a' and total_data[start_index] != 'n' and sequence_number == timer[start_index][1]:
                # update the global values
                timer[start_index] = 'a'
                start_index += 1
                # receive more in buffer
                file_buffer_size -= MSS

def timerHandler():
    # handles timers for each MSS unit
    global timer
    global start_index
    global transmission_index
    while True:
        for index in range(start_index, start_index + WINDOW_SIZE):
            if timer[index] != 'n' and timer[index] != 'a':
                time_now = time.time_ns() * 1000000
                difference = timer[index][1] - time_now
                new_counter = timer[index][0] - difference
                if new_counter <= 0:
                    # time out!
                    start_index = index
                    transmission_index = start_index
                    # resetting timer for these to tranmit
                    for i in range(start_index, start_index + WINDOW_SIZE):
                        timer[i] = 'n'
                    # break from for-loop
                    break
                timer[index] = [difference, time_now]

def computeCheckSum(binary_data_list):
    result = "".join(['0']*16)
    # Traverse the string
    for x in binary_data_list:
        temp_byte = '' 
        carry = 0
        for i in range(len(binary_data_list) - 1, -1, -1): 
            r = carry 
            r += 1 if x[i] == '1' else 0
            r += 1 if result[i] == '1' else 0
            temp_byte = ('1' if r % 2 == 1 else '0') + temp_byte 
            carry = 0 if r < 2 else 1
        
        # adding carry to the LSB
        for i in range(len(binary_data_list) - 1, -1, -1):
            if carry != 0:
                r = carry 
                r += 1 if x[i] == '1' else 0
                r += 1 if result[i] == '1' else 0
                temp_byte = ('1' if r % 2 == 1 else '0') + temp_byte 
                carry = 0 if r < 2 else 1
            else:
                break
        result = temp_byte
    # 1's compliment
    result = ''.join(['1' if (i == '0') else '0' for i in result])
    return result

def createPacket():
    global transmission_index
    global total_data
    # create header except checksum
    # sequence no
    h_field_1 = "{:032b}".format(total_data[transmission_index][1])
    # signifies this is a data datagram
    h_field_3 = "01"*8
    # calculate checksum
    data_packet = total_data[transmission_index][0]
    binary_data_array = ["{:016b}".format(i) for i in bytearray(data_packet, "utf-8")]
    h_field_2 = computeCheckSum(binary_data_array)
    # add it to the data
    total_packet = h_field_1 + h_field_2 + h_field_3 + data_packet
    return total_packet

def transmissionHandler():
    # transmits data
    global total_data
    global start_index
    global transmission_index
    global timer
    while True:
        if total_data and transmission_index < start_index + WINDOW_SIZE:
            # create packet
            packet = createPacket()
            # send the data
            client_socket.send(packet)
            # update timer of transmission_index
            timer[transmission_index] = [TIMER, time.time_ns()*1000000]
            transmission_index += 1

def readFile(file_ptr=0):
    # reading the data from the file
    global total_data
    global file_buffer_size
    file_buffer_size = 0
    while True:
        if file_buffer_size < BUFFER_SIZE:
            with open(FILE_NAME) as file:
                # setting to continue where we left off
                file.seek(file_ptr)
                data = file.read(MSS)
                if not data:
                    # file has been read
                    break
                file_ptr = file.tell()
                file_buffer_size += MSS
            # total_data = [data[i:i+MSS] for i in range(0, len(data), MSS)]
            total_data.append([data, ((file_buffer_size/MSS) - 1) % WINDOW_SIZE])


"""
Global variables
"""
# to keep track of the file reading buffer
file_buffer_size = 0
# the data to be transmitted
total_data = []
"""
timer - track the timers of each transmission
Following states:   n - not assigned
                    a - acknowledged
                    [counter(ms), sent_time(ms)] - sent but not acknowledged
"""
timer =  timer = ['n'] * BUFFER_SIZE
# indices required for transmission
start_index = 0
transmission_index = 0

# UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.connect(SERVER_HOST, SERVER_PORT)
print("Connected to the server...")

file_thread = threading.Thread(target=readFile)
ack_thread = threading.Thread(target=ackHandler, args=(client_socket,))
timer_thread = threading.Thread(target=timerHandler)
file_thread.start()
ack_thread.start()
timer_thread.start()

# main thread is transmitting
transmissionHandler()

# terminate
client_socket.close()