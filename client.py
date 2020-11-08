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
        # print('a', end='')
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
            # print(f"ack seqno: {sequence_number}, start seqno:{total_data[start_index][1]}")
            """
            if total_data and total_data[start_index] != 'n': 
                if sequence_number == total_data[start_index][1]:
                    # update the global values
                    # print(f"ack seqno: {sequence_number}")
                    timer[start_index] = 'a'
                    start_index += 1
            """
            if total_data and timer[start_index] != 'n':
                # cumulative ACKs
                while start_index <= transmission_index:
                    timer[start_index] = 'a'
                    # timer_lock.release()
                    if total_data[start_index][1] == sequence_number:
                        start_index += 1
                        break
                    start_index += 1
            
            timer_lock.release()

"""
def timerHandler():
    # handles timers for each MSS unit
    global timer
    global start_index
    global transmission_index
    global TIMER
    global timer_lock
    global is_file_sent

    while not is_file_sent:
        end_ind = start_index + WINDOW_SIZE
        for index in range(start_index, end_ind):
            # timer_lock.acquire()
            if index < len(timer) and timer[index] != 'n' and timer[index] != 'a':
                time_now = round(time.time(), 2)
                difference = time_now - timer[index]
                # new_counter = timer[index][0] - difference
                if difference <= TIMER:
                    # time out!
                    # print(f"Timeout, Sequence Number = {total_data[index][1]}")
                    # double the timer in the event of the timeout
                    # TIMER *= 2
                    start_index = index
                    transmission_index = start_index
                    # resetting timer for these to transmit
                    ## for i in range(start_index, start_index + WINDOW_SIZE):
                    ##     if i < len(timer):
                    ##         timer[i] = 'n'
                    # break from for-loop
                    # timer_lock.release()
                    break
                timer_lock.acquire()
                timer[index] = [difference, time_now]
                timer_lock.release()
        # forcing thread yield
        # time.sleep( 0.05 )
"""

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
    # print(checksum)
    # checksum = 0
    # val = len(data) % 2
    # flag = 0
    # if val != 0:
    #     flag = 1
    #     data = data + '0' if flag == 1 else data
    #     i = 0
    #     while i < len(data):
    #         blockSum = checksum + ord(data[i]) + (ord(data[i + 1]) << 8)
    #         checksum = (blockSum & 0xFFFF) + (blockSum >> 16)
    #         i += 2
    # checksum = (~checksum) & 0xFFFF
    # print(checksum)
    # print("-------")
    return checksum

def createPacket(transmission_index, total_data):
    # global transmission_index
    # global total_data
    # IHH -> 4 + 2 + 2 bytes
    header = struct.pack('!IHH', total_data[transmission_index][1], computeCheckSum(total_data[transmission_index][0]), 0b0101010101010101)
    total_packet = header + str(total_data[transmission_index][0]).encode()
    return total_packet

def isStartTimedOut(start_index, timer):
    time_now = round(time.time(), 2)
    difference = 0
    if timer[start_index] != 'n':
        difference = time_now - timer[start_index]
    # except:
    # print(start_index, len(timer), timer[start_index])
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
        # print(transmission_index, start_index, len(total_data))
        timer_lock.acquire()
        if total_data and transmission_index < len(total_data) and transmission_index < start_index + WINDOW_SIZE :
            # check if timeout
            if timer[start_index] != 'n' and isStartTimedOut(start_index, timer):
                # retransmit
                print(f"Timeout, Sequence Number = {total_data[start_index][1]}")
                transmission_index = start_index
            # create packet
            packet = createPacket(transmission_index, total_data)
            # send the data
            # print("tx", total_data[transmission_index][1])
            client_socket.sendto(packet, (socket.gethostname(), 7735))
            # update timer of transmission_index
            # timer[transmission_index] = [TIMER, round(time.time())]
            timer[transmission_index] = round(time.time())
            transmission_index += 1
        elif start_index < len(total_data) and isStartTimedOut(start_index, timer):
            # check for timeout
            print(f"Timeout, Sequence Number = {total_data[start_index][1]}")
            transmission_index = start_index
        timer_lock.release()
        # else:
        #     print("----", transmission_index, len(total_data))
        #     # forcing thread yield
        #     time.sleep( 0.05 )

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
                # print('-------------FILE READ DONE!')
                is_file_read = True
                break
            file_ptr = file.tell()
        # total_data.append([data, seg_no * MSS])
        # print("read: ", seg_no)
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
# timer_thread = threading.Thread(target=timerHandler)

START_TIME = round(time.time())

file_thread.start()
# timer_thread.start()
ack_thread.start()

# main thread is transmitting
transmissionHandler(client_socket)

# terminate
client_socket.close()

END_TIME = round(time.time())
print("Transfer completed. Time taken: ", END_TIME - START_TIME)
