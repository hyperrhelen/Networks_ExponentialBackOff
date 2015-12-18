# Multiple Queues
# Helen Chac & Nathan Truong
# Written in Python3.x
#
# Written in Python3.x to calculate the throughput with various arrival
# rates and compare them to linear backoff and the exponential back off
# to understsand why exponential back off is more liked.

import random
import simpy
import math

RANDOM_SEED = 29
SIM_TIME = 100000
MU = 1

# The throughput should equal to the number of successful slots over the total
# number of slots that it tries.
def Throughput(successful_slots , total):
    if total == 0:
        return 0
    return successful_slots / total

# Implements the Exponential Back off Randomly.
# Find the min(n, 10)
# Return a random number in the range min(2**n, 2**10)
def ExpBackOff(x):
    # Find a new slot number for the class.
    # Minimum of the (n, 10) becuase it can't be greater than 2^10
    # Then we need to round it, which helps us choose the random number.
    if x.N() > 10:
        return random.randrange(2**10)
    return random.randrange(2**x.N())

# Implementated the Linear Back off Randomly.
# Find the min(n, 1024)
# Return a random number in the range min(n,1024).
def LinBackOff(x):
    if x.N() > 1024:
        return random.randrange(1024)
    if x.N() == 0:
        return 0
    return random.randrange(x.N())

""" Packet class """
class Packet:
    def __init__(self, identifier, arrival_time):
        self.identifier = identifier
        self.arrival_time = arrival_time

"""
    Queue class
    Each host maintains these three variables:
        L = number of packets in the queue.
        N = number of packets at the head of queue that has been
            retransmitted. When a new packet comes to the head of
            the queue, then n is reset to 0.
        S = slot number when the next transmission attempt will be
            made for the packet at the head of the queue.
"""
class Queue:
    def __init__(self, num_of_packets, slot_num, retransmissions):
        self.l = num_of_packets
        self.s = slot_num
        self.n = retransmissions  #Initially

    def L(self):
        return self.l

    def S(self):
        return self.s

    def N(self):
        return self.n

    # When we have a successfully transmitted packet, we want to decrement
    # the number of packets and increment the slot number, and set the
    # retransmissions = 0.
    def SuccessfulTxPkt(self):
        self.l -= 1
        self.s += 1
        self.n = 0

    # We have 2 different cases:
    #   1. Unsuccessfully transmitted linear back off.
    #   2. Unsuccessfully transmitted exponential back off.
    def UnSuccessfulTxPktLin(self):
        self.s += (LinBackOff(self) + 1)
        self.n += 1
        return
    def UnSuccessfulTxPktExp(self):
        # This will give us our new slot number.
        self.s += (ExpBackOff(self) + 1)
        # Since the retransmission failed, we need to increment our number
        # of transmissions by 1.
        self.n += 1
        return

"""
    Ethernet class, acts as the server. Can hold n hosts.
    Processes that will be running in parallel is:
    1. n number of packet arrivals for the hosts
    2. Check Collision which continues to check the collision for
       each slot.
"""
class Ethernet:
    def __init__(self, env, arrival_rate, hosts, slot_num):
        self.server = simpy.Resource(env, capacity=1)
        self.env = env
        self.hosts = hosts
        self.packet_number = 0
        self.slot_num = slot_num
        self.arrival_rate = arrival_rate
        self.success = 0
        self.total = 0

    # flag_exp = true if it's for Exponential Backoff.
    # false for linear backoff
    # Checks for collision and runs as a process in the background.
    # If there is a collision, then we want to find a new slot number
    # for that host.
    # If there isn't a collision, then we want to successfully process the
    # packet.
    def CheckCollision(self, env, list_of_queue, flag_exp):
        # Iteratively check to see if there is a collision.
        while True:
            l = []
            for q in self.hosts:
                if q.s == self.slot_num and q.l > 0:
                    l.append(q)
            # Point of collision.
            if len(l) > 1:
                for q in l:
                    if flag_exp == True:
                        q.UnSuccessfulTxPktExp()
                    else:
                        q.UnSuccessfulTxPktLin()
            else:
                if len(l) == 1:
                    self.success += 1
                    # Point of success. There are no collisions.
                    # We want to process the packet.
                    for q in l:
                        q.SuccessfulTxPkt()
                        self.packet_number += 1
                        arrival_time = env.now
                        new_packet = Packet(self.packet_number,arrival_time)
                        self.process_packet(env, new_packet)

            # We don't do yield env.timeout(random.expovariate(MU)) since
            # this is slotted, then the times for each one has to be the same.
            # There shouldn't be a variance between the slots.
            yield env.timeout(MU)
            self.total += 1
            self.slot_num += 1

    # As a host receives the packets, for that specific host, the number
    # of packets that are in their queue increases.
    # L += 1
    def packets_arrival(self, env, s_host):
        while True:
            # Waiting for the packet to arrive.
            yield env.timeout(random.expovariate(self.arrival_rate))
            s_host.l += 1
            if s_host.l == 1:
                s_host.s = self.slot_num + 1

    # To show that the server is processing the packets.
    def process_packet(self, env, packet):
        return

def main():

    # The list of arrival rates.
    arrival_rates = [.01, .02, .03, .04, .05, .06, .07, .08, .09]

    num_of_hosts = 10
    start_slot_num = 0
    print("{0:<9} {1:<16} {2:<16}".format("Lambda", "ExpBackOff", "Linear"))
    # Loop through the arrival rates and calculate the exponential back off
    # and the linear back off.
    for arrival_rate in arrival_rates:
        exp = 0
        lin = 0
        for index in range(0,2):
            env = simpy.Environment()
            hosts = []
            # Initialize all the values of the host based on the number
            # of hosts there are.
            for i in range(0, num_of_hosts):
                hosts.append(Queue(0,0,0))

            ethernet = Ethernet(env, arrival_rate, hosts, start_slot_num)
            # Initialize the processes. Since there are n number of hosts,
            # we want to have n number of PacketArrival processes running
            # at the same time.
            for i in range(len(ethernet.hosts)):
                env.process(ethernet.packets_arrival(env, ethernet.hosts[i]))
            # Check Collision checks at every MU, and continously checks
            # whether or not there is currently a collision.
            env.process(ethernet.CheckCollision(env, hosts, index))
            env.run(until=SIM_TIME)
            print("Success: {0:<5}, Total: {0:<5}".format(ethernet.success,
                ethernet.total))
            # Calculate the throughput for linear and exponential backoff.
            if index == 0:
                lin = Throughput(ethernet.success, ethernet.total)
            else:
                exp = Throughput(ethernet.success, ethernet.total)

        # Formatted printing
        print("{0:<9} {1:<16} {2:<16}".format(arrival_rate,
            round(exp,10), round(lin,10)))
    return

main()
