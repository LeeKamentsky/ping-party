"""Ping Party!

This application uses UDP packets to check network connectivity between
machines on a network. The protocol is this:

Messages are encoded as JSON dictionary. The message is in the "message"
key of the dictionary.

"Are you there?" - a message asking a specific sender if they are still around.
         The message should be sent from the sender's listening port. The
         recipient should send "I am here" to the given port.
"I am here" - a message sent to tell a requester
         that the sender is running and has connectivity. It is sent on the
         sender's listening port to either a requesting recipient or
         periodically to the broadcast port. There is a single parameter which
         is the frequency.
"""
import argparse
import io
import json
import logging
import logging.config
import random
import socket
import threading
import time

MSG_ARE_YOU_THERE = "Are you there?"
MSG_I_AM_HERE = "I am here."
MSG_WAKE_UP = "WAKE UP!"
MSG_STOP = "STOP!"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ip-address",
        help="The IP address of the interface to bind to",
        required=True
    )
    parser.add_argument(
        "--broadcast-address",
        help="The IP address of the broadcast address for the subnet",
        required=True
    )
    parser.add_argument(
        "--broadcast-port",
        help="The port used for broadcasting",
        required=True,
        type=int
    )
    parser.add_argument(
        "--frequency",
        help="Minimum frequency of broadcasts in seconds",
        default=60,
        type=float
    )
    parser.add_argument(
        "--jitter-min",
        help="Minimum number of seconds to subtract from the frequency",
        type=float,
        default=5
    )
    parser.add_argument(
        "--jitter-max",
        help="Maximum number of seconds to subtract from the frequency",
        type=float,
        default=10
    )
    parser.add_argument(
        "--logging-config",
        help='Logging config file (see "https://docs.python.org/3/library/logging.config.html#logging-config-fileformat")'
    )
    return parser.parse_args()


"""This is the listening socket"""
SOCKET = None


def make_socket(interface, port):
    global SOCKET
    SOCKET = socket.socket(family=socket.AF_INET,
                           type=socket.SOCK_DGRAM,
                           proto=socket.IPPROTO_UDP)
    SOCKET.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    SOCKET.bind((interface, port))
    logging.debug("Listening socket has bound")


def listening_thread(d:dict, e:threading.Event, frequency):
    while True:
        data, address = SOCKET.recvfrom(1024)
        t = time.time()
        logging.debug("Received msg from %s" % str(address))
        try:
            fd = io.BytesIO(data)
            msg = json.load(fd)
        except:
            logging.exception("Caught exception while decoding message")
            continue
        if "name" in msg:
            name = msg["name"]
            logging.debug("Message type: %s" % name)
            if name == MSG_STOP:
                break
            if name == MSG_I_AM_HERE:
                logging.info("Received heartbeat from %s" % str(address))
                d[address] = (t, t + msg["frequency"])
                e.set()
            if name == MSG_ARE_YOU_THERE:
                send_i_am_here(address, frequency)


def make_message(name, params={}):
    msg = dict(name=name)
    msg.update(params)
    return msg


def send_i_am_here(address, frequency):
    msg = make_message(MSG_I_AM_HERE,
                       dict(frequency=frequency))
    fd = io.StringIO()
    json.dump(msg, fd)
    logging.debug("Sending I am Here to %s" % str(address))
    SOCKET.sendto(fd.getvalue().encode("utf-8"), address)


def sending_thread(broadcast_address, frequency, min_jitter, max_jitter):
    while True:
        send_i_am_here(broadcast_address, frequency)
        next_frequency = frequency - random.uniform(min_jitter, max_jitter)
        time.sleep(next_frequency)


def main():
    args = parse_args()
    if args.logging_config is None:
        logging.basicConfig()
    else:
        logging.config.fileConfig(args.logging_config)
    make_socket(args.ip_address, args.broadcast_port)
    d = {}
    e = threading.Event()

    def lf():
        listening_thread(d, e, args.frequency)

    lt = threading.Thread(target=lf)
    lt.setDaemon(True)
    lt.start()

    broadcast_address = (args.broadcast_address, args.broadcast_port)
    def sf():
        sending_thread(broadcast_address, args.frequency,
                       args.jitter_min, args.jitter_max)
    st = threading.Thread(target=sf)
    st.setDaemon(True)
    st.start()

    while True:
        if len(d) == 0:
            e.wait()
            e.clear()
        else:
            t0 = time.time()
            min_t = t0 + 1000
            for k in d:
                min_t = min(d[k][1], min_t)
                min_addr = k
            if not e.wait(min_t - t0):
                # Somebody updated the dictionary in time, so proceed
                e.clear()
                continue
            logging.warning("%s heartbeat timed out" % str(min_addr))
            logging.info("Timeout after %f sec, orig delta = %f sec" %
                         (min_t -t0, d[min_addr][1] - d[min_addr][0]))
            #
            # There's a race here where the worst guy sends a message
            # while we are failing. Well, at worst we miss the next heartbeat
            # and enter him/her at the subsequent heartbeat
            #
            del d[min_addr]


if __name__=="__main__":
    main()
