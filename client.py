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

START_TIME = time.time()
SERVER_HOST = sys.argv[1]
SERVER_PORT = int(sys.argv[2])
FILE_NAME = sys.argv[3]
WINDOW_SIZE = int(sys.argv[4])
MSS = int(sys.argv[5])

BUFFER_SIZE = MSS * 100
TIMER = 1 #seconds

def ackHandler(client_socket):
    # listens for acknowledgments
    while True:
        client_socket.recv(MSS + 8)

def timerHandler():
    # handles timers for each MSS unit
    global timer
    timer = ['n'] * BUFFER_SIZE

def computeCheckSum(binary_data):
    

def createPacket():
    global transmission_index
    global total_data
    # create header except checksum
    # sequence no
    h_field_1 = "{:032b}".format(total_data[transmission_index][1])
    # signifies this is a data datagram
    h_field_3 = "0101010101010101"
    # calculate checksum
    data_packet = total_data[transmission_index][0]
    binary_data_array = ["{:08b}".format(i) for i in bytearray(data_packet, "utf-8")]
    computeCheckSum(binary_data_array)
    # add it to the data

    return 

def transmissionHandler():
    # transmits data
    global total_data
    global start_index
    global transmission_index
    while True:
        if total_data:
            # create packet
            createPacket()
            # update timer of startInd
            timerHandler()
            # send the data


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
# track the timers of each transmission
timer = []
# indices required for transmission
start_index = 0
transmission_index = 0

# UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.connect(SERVER_HOST, SERVER_PORT)

file_thread = threading.Thread(target=readFile)
ack_thread = theading.Thread(target=ackHandler, args=(client_socket,))
# timer_thread = threading.Thread(target=timerHandler)
file_thead.start()
ack_thread.start()
timer_thread.start()

# main thread is transmitting
transmissionHandler()

# terminate
client_socket.close()