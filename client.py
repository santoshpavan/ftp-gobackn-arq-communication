# pylint: skip-file
import socket
import sys
import threading
import time
from collections import deque
import struct

"""
Command:
Simple_ftp_server server-host-name server-port# file-name N MSS
"""
# checking validity of command
if (len(sys.argv) != 7 or sys.argv[1] != "Simple_ftp_server"):
    print("Please enter correct command")
    sys.exit()

# time in milliseconds
# START_TIME = int(time.time_ns()/1000000)
START_TIME = int(time.time())
SERVER_HOST = sys.argv[2]
SERVER_PORT = int(sys.argv[3])
FILE_NAME = sys.argv[4]
WINDOW_SIZE = int(sys.argv[5])
MSS = int(sys.argv[6])

"""
print(START_TIME)
print(SERVER_HOST)
print(SERVER_PORT)
print(FILE_NAME)
print(WINDOW_SIZE)
print(MSS)
"""

BUFFER_SIZE = MSS * 100
ACK_SIZE = 8192
# timer in milli seconds
TIMER = 1

def ackHandler(client_socket):
    # listens for acknowledgments
    # print("Listening for ACKs...")
    global timer
    global start_index
    global total_data
    global is_file_sent
    global is_file_read
    global timer_lock
    # global data_lock
    #global file_buffer_size
    while not is_file_sent:
    # while True:
        # print(threading.currentThread().getName())

        if is_file_read and timer[len(timer) - 1] == 'a':
            # ACK'ed the entire file
            is_file_sent = True
            print("FILE SEND DONE!")
            break

        ack_packet, address = client_socket.recvfrom(ACK_SIZE)
        header = struct.unpack('!IHH', ack_packet[:8])
        # basic validity check
        # if len(ack_packet) == 64 and ack_packet[32:48] == "0"*16 and ack_packet[48:] == "10"*8:
        if header[1] == 0 and header[2] == 0b1010101010101010:
            # sequence_number = int(ack_packet[:32], 2)
            sequence_number = header[0]
            # print(f"acked: {sequence_number} and startind: {start_index} and len: {len(timer)}")
            # start_index += 1
            # updating the status

            timer_lock.acquire()
            # print('***ack-acquired')

            if (
                    # total_data and timer[start_index] != 'a' and
                    total_data and timer[start_index] != 'n'
                    # sequence_number >= timer[start_index][1] and sequence_number <= timer[transmission_index][1] 
                ):
                # need to ACK from start to ind of sequence
                end_ind = start_index + WINDOW_SIZE
                while start_index <= transmission_index:
                    print(f"-----ACKed no: {total_data[start_index][1]}")
                    # timer_lock.acquire()
                    # print('***ack-acquired')
                    timer[start_index] = 'a'
                    timer_lock.release()
                    # print('**ack-released')
                    if total_data[start_index][1] == sequence_number:
                        # if is_file_read and sequence_number == total_data[len(total_data) - 1][1]:
                        #     # ACK'ed the entire file
                        #     is_file_sent = True
                        #     print("FILE SEND DONE!", sequence_number)
                        start_index += 1
                        break
                    start_index += 1
            
            # timer_lock.release()

                # receive more in buffer
                # file_buffer_size -= MSS
                # data_lock.acquire()
                # total_data.popleft()
                # data_lock.release()
            
        # else:
        #     time.sleep( 0.0001 )

def timerHandler():
    # handles timers for each MSS unit
    # print("Timer...")
    global timer
    global start_index
    global transmission_index
    global TIMER
    global timer_lock
    global is_file_sent
    # timer[transmission_index] = [TIMER, time.time_ns()*1000000]
    while not is_file_sent:
    # while True:
        # print(threading.currentThread().getName())
        end_ind = start_index + WINDOW_SIZE
        for index in range(start_index, end_ind):
            
            timer_lock.acquire()
            # print("^^^^timer acquired")
            if index < len(timer) and timer[index] != 'n' and timer[index] != 'a':
                # timer_lock.acquire()
                #time_now = int(time.time_ns() / 1000000)
                # print(threading.currentThread().getName(), timer[index])
                # time_now = int(time.time())
                time_now = round(time.time(), 2)
                # time_now = round(time.time())
                # try: 
                # difference = timer[index][1] - time_now
                difference = time_now - timer[index][1]
                # except:
                # print(f"-------{index}-----{timer[index]}--------------")
                new_counter = timer[index][0] - difference
                # print(f"diff: {difference} and new_counter: {new_counter}")
                
                if new_counter <= 0:
                    # time out!
                    print(f"Timeout, Sequence Number = {total_data[index][1]}")
                    # double the timer in the event of the timeout
                    TIMER *= 2
                    start_index = index
                    transmission_index = start_index
                    # resetting timer for these to transmit
                    for i in range(start_index, start_index + WINDOW_SIZE):
                        if i < len(timer):
                            timer[i] = 'n'
                    # break from for-loop
                    break
                
                # timer_lock.acquire()
                timer[index] = [difference, time_now]
            timer_lock.release()
            # print("^^^^timer released")
        # print("timer yield")
        time.sleep( 0.05 )

def computeCheckSum(data):
    """
    CHANGE THIS LATER!!!!!!!!!! - NOT SURE
    """
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
    return checksum

def createPacket():
    global transmission_index
    global total_data
    # IHH -> 4 + 2 + 2 bytes
    # print(f"crp-trind: {transmission_index} and contents: {total_data[transmission_index]}")
    # print(len(total_data))
    header = struct.pack('!IHH', total_data[transmission_index][1], computeCheckSum(total_data[transmission_index][0]), 0b0101010101010101)
    total_packet = header + str(total_data[transmission_index][0]).encode()
    return total_packet

def transmissionHandler(client_socket):
    # transmits data
    # print("Transmitting...")
    global total_data
    global start_index
    global transmission_index
    global timer
    global is_file_sent
    while not is_file_sent:
    # while True:
        # print(threading.currentThread().getName())
        if (    total_data and transmission_index < len(total_data) and
                transmission_index < start_index + WINDOW_SIZE ):
            print(f"tx: {total_data[transmission_index][1]}")
            # create packet
            packet = createPacket()
            ###packet_inbyte = bytes(packet,'utf-8')
            # send the data
            #client_socket.send(packet.encode())
            #client_socket.sendto(packet.encode('utf-8'), ('', 7734))
            client_socket.sendto(packet, (socket.gethostname(), 7735))
            ###client_socket.sendto(packet_inbyte, ('', 7735))
            # update timer of transmission_index
            # timer[transmission_index] = [TIMER, int(time.time())]
            timer[transmission_index] = [TIMER, round(time.time())]
            transmission_index += 1
        else:
        #     #print("tranmitter yield")
            time.sleep( 0.05 )

def readFile(file_ptr=0):
    # reading the data from the file
    # print("Reading...")
    global total_data
    global is_file_read
    global timer
    # global file_buffer_size
    # file_buffer_size = 0
    seg_no = 0
    while True:
        # if file_buffer_size < BUFFER_SIZE:
        if len(total_data) < BUFFER_SIZE:
        # if len(total_data) < BUFFER_SIZE and not is_file_read:
            with open(FILE_NAME) as file:
                # setting to continue where we left off
                file.seek(file_ptr)
                data = file.read(MSS)
                if not data:
                    # file has been read
                    is_file_read = True
                    print("FILE READ DONE!", seg_no * MSS, seg_no)
                    break
                file_ptr = file.tell()
                # file_buffer_size += MSS
            total_data.append([data, seg_no * MSS])
            seg_no += 1
            timer.append('n')
        # else:
        #     #print("tranmitter yield")
        #     time.sleep( 0.0001 )


"""
Global variables
"""
# to keep track of the file reading buffer
file_buffer_size = 0
# the data to be transmitted
# total_data = deque()
data_lock = threading.RLock()
# to keep track of the file reading and sending
is_file_read = False
is_file_sent = False
total_data = []

"""
timer - track the timers of each transmission
Following states:   n - not assigned
                    a - acknowledged
                    [counter(ms), sent_time(ms)] - sent but not acknowledged
"""
# timer = ['n'] * BUFFER_SIZE
timer = []
timer_lock = threading.RLock()
# indices required for transmission
start_index = 0
start_ind_lock = threading.RLock()
transmission_index = 0
tx_ind_lock = threading.RLock()

# UDP
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.bind((socket.gethostname(), 1234))
#client_socket.connect(SERVER_HOST, SERVER_PORT)
#client_socket.connect(('', 7734))
print("Connected to the server...")

file_thread = threading.Thread(target=readFile)
ack_thread = threading.Thread(target=ackHandler, args=(client_socket,))
timer_thread = threading.Thread(target=timerHandler)

"""
def readFile(file, size=MSS):
    while True:
        data = file.read(size)
        if not data:
            break
        yield data


# file_thread.start()
print("Reading...")
seg_no = 0
with open(FILE_NAME) as f:
    for data_seg in readFile(f):
        #MSS is in bytes
        total_data.append([data_seg, seg_no * MSS])
        seg_no += 1
"""
# timer = ['n'] * len(total_data)

file_thread.start()
timer_thread.start()
ack_thread.start()

# main thread is transmitting
transmissionHandler(client_socket)

# terminate
client_socket.close()