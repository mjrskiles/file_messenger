"""
CSC376 Assignment 3 - Chat
Server
Michael Skiles
"""

import threading
import sys
import os
import socket
import getopt

def usage( script_name ):
    print( 'Argument(s) specified incorrectly.')
    print( 'Usage: python3 ' + script_name + ' -l <listen port> [-s] [connect server address]\
                -p <connect server port>' )

argv = sys.argv
argc = len( sys.argv )
if argc < 2 or argc > 7 :
    usage( sys.argv[0] )
    sys.exit(1)

def parse_opts( argv, argc ):
    run_as_server = True
    listen_port = ''
    host = 'localhost'
    port = ''

    #options is a list of tuples of the parsed -options and values, args is the leftover
    options, args = getopt.getopt(argv[1:], "l:s:p:")

    for (opt, val) in options:
        if opt == '-l':
            listen_port = val
            try:
                int(listen_port)
            except ValueError:
                print("The listening port was not specified correctly.")
                usage( argv[0] )

        if opt == '-s':
            host = val
            run_as_server = False
            if host == '':
                print("The host was specified incorrectly.")
                usage( argv[0] )

        if opt == '-p':
            port = val
            run_as_server = False
            try:
                int(port)
            except ValueError:
                print("The server port was not specified correctly.")
                usage( argv[0] )

    print(run_as_server)
    print(listen_port)
    print(host)
    print(port)

    if listen_port == '':
        usage( argv[0] )
    if not run_as_server:
        if host == '' or port == '':
            usage( argv[0] )

    return [run_as_server, listen_port, host, port]

class Messenger:

    #The client_socks dict is a dictionary with an client id int
    #as the key, followed by a list in form [socket, thread instance, client username]
    SOCKET_POS = 0
    INSTANCE_POS = 1
    CLIENT_NAME_POS = 2
    client_socks = {}
    listen_sock = None
    server_host = None
    server_port = None
    text_sock   = None

    def __init__( self, port ):
        self.port = port

    def open_listener( self, port ):
        """
        open a socket on the specified port and set it to listen.
        """
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_sock.bind( ('localhost', int(port)) )
        self.listen_sock.listen(5)

    def request_connection( self, host, port ):
        self.text_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.text_sock.connect( (host, int(port)) )
        if self.text_sock is None:
            print("Could not open socket.")
            sys.exit(1)

    def accept_connection( self ):
        #socket.accept() returns a (socket, ('host', port)) tuple
        self.text_sock, addr = self.listen_sock.accept()
        self.server_host = addr[0]
        print("Connection accepted, addr: " + str(addr))

    def run_messenger( self ):
        msg_receiver = threading.Thread( target=self.get_messages )
        msg_receiver.start()
        self.get_input()

    def get_messages( self ):
        message = self.text_sock.recv( 4096 )
        while message:
            print( message.decode(), end='' )
            message = self.text_sock.recv( 4096 )
        self.clean_up()

    def get_input( self ):
        for line in sys.stdin:
            self.text_sock.send( line.encode() )
        self.clean_up()

    def clean_up( self ):
        pass

class Server( Messenger ):
    def __init__( self, listen_port ):
        super().__init__( listen_port )
        self.open_listener( self.port )
        self.accept_connection()
        file_req_port = self.text_sock.recv( 4 ).decode()
        print("Client sent back listen port " + file_req_port + ".")
        try:
            int(file_req_port)
        except ValueError:
            print("The client did not send back a valid port number.")
            os.exit(1)
        self.server_port = file_req_port


class Client( Messenger ):
    def __init__( self, listen_port, host, port ):
        super().__init__( listen_port )
        self.server_host = host
        self.server_port = port
        self.request_connection( self.server_host, self.server_port )
        print("Connection accepted.  Sending listen port " + listen_port + ".")
        self.text_sock.send( listen_port.encode() )
        self.open_listener( listen_port )


def main():
    parsed_args = parse_opts( argv, len(argv) )
    if parsed_args[0]:
        m = Server( parsed_args[1] )
    else:
        m = Client( parsed_args[1], parsed_args[2], parsed_args[3] )

    m.run_messenger()

main()