"""
CSC376 Assignment 3 - Chat
Server
Michael Skiles
"""

import threading
import sys
import os
import struct
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

#    print(run_as_server)
#    print(listen_port)
#    print(host)
#    print(port)

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

    def __init__( self, port ):
        self.port = port
        self.open_socks = []
        self.threads = []
        self.listen_sock = None
        self.server_host = None
        self.server_port = None
        self.text_sock   = None

    def open_listener( self, port ):
        """
        open a socket on the specified port and set it to listen.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind( ('localhost', int(port)) )
        sock.listen(5)
        return sock

    def request_connection( self, host, port ):
        """
        opens a socket and binds it to 'sock'
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect( (host, int(port)) )
        return sock

    def accept_connection( self ):
        #socket.accept() returns a (socket, ('host', port)) tuple
        sock, addr = self.listen_sock.accept()
        print("Connection accepted, addr: " + str(addr))
        return (sock, addr)

    def run_messenger( self ):
        msg_receiver = threading.Thread( target=self.get_messages )
        msg_receiver.start()
        self.threads.append( msg_receiver )
        file_server = threading.Thread( target=self.serve_files )
        file_server.start()
        self.threads.append( file_server )
        self.get_input()

    def get_messages( self ):
        message = self.text_sock.recv( 4096 )
        while message:
            print( message.decode(), end='' )
            message = self.text_sock.recv( 4096 )
        self.clean_up()

    def get_input( self ):
        while True:
            print("Enter an option ('m', 'f', 'x'):")
            print("  (M)essage (send)")
            print("  (F)ile (request)")
            print(" e(X)it")
            choice = sys.stdin.readline().rstrip('\n')
            if choice == 'x':
                break
            elif choice == 'm':
                print("Enter your message:")
                line = sys.stdin.readline()
                self.send_text( line )
            elif choice == 'f':
                print("Which file do you want?")
                file_name = sys.stdin.readline().rstrip('\n')
                self.get_file( file_name )
        self.clean_up()

    def send_text( self, text ):
        self.text_sock.send( text.encode() )

    def get_file( self, file_name ):
        print(type(file_name))
        print(file_name)
        #There needs to be a comma after file_name because args expects a tuple!!!
        file_conn = threading.Thread( target=self.request_file, args=(file_name,) )
        self.threads.append(file_conn)
        file_conn.start()

    def request_file( self, file_name ):
        """Opens a connection to the file server and receives the file"""
        try:
            file_sock = self.request_connection( self.server_host, self.server_port )
            if file_sock:
                print("file_sock opened")
            file_sock.send( file_name.encode() )
            file_size_bytes = file_sock.recv( 4 )
            if file_size_bytes:
                file_size= struct.unpack( '!L', file_size_bytes[:4] )[0]
                if file_size:
                    Messenger.receive_file( file_sock, file_name )
                else:
                    print( 'File does not exist or is empty' )
            else:
                print( 'File does not exist or is empty' )
        except:
            print("Could not open connection to file server.")
        finally:
            if file_sock is not None:
                file_sock.close()

    def receive_file( sock, filename ):
        """receive the file lines returned from the server"""
        file= open( filename, 'wb' )
        while True:
            file_bytes= sock.recv( 1024 )
            if file_bytes:
                file.write( file_bytes )
            else:
                break
        file.close()

    def serve_files( self ):
        print("Opening file server...")
        while True:
            sock, addr = self.accept_connection()
            file_server = threading.Thread( target=Messenger.handle_request, args=(sock,) )
            file_server.start()
            self.threads.append(file_server)

    def handle_request( sock ):
        msg_bytes= sock.recv(1024)
        # convert the message into a string, which is the name of the desired file
        file_name= msg_bytes.decode()
        # check whether the file exists; if it does, send back the file size
        print("Received file name: {}".format(file_name))
        try:
            file_stat= os.stat( file_name )
            if file_stat.st_size:
                print("Found file {}".format(file_name))
                file= open( file_name, 'rb' )
                Messenger.send_file( sock, file_stat.st_size, file )
            else:
                print("File not found: {}".format(file_name))
                Messenger.no_file( sock )
        except OSError:
            Messenger.no_file( sock )
        finally:
            sock.close()

    def send_file( sock, file_size, file ):
        print( 'File size is ' + str(file_size) )
        file_size_bytes= struct.pack( '!L', file_size )
        # send the number of bytes in the file
        sock.send( file_size_bytes )
        # read the file and transmit its contents
        while True:
            file_bytes= file.read( 1024 )
            if file_bytes:
                sock.send( file_bytes )
            else:
                break
        file.close()

    def no_file( sock ):
        zero_bytes= struct.pack( '!L', 0 )
        sock.send( zero_bytes )

    def clean_up( self ):
        self.text_sock.close()
        self.listen_sock.close()
        for sock in self.open_socks:
            sock.close()
        os._exit(0)


class Server( Messenger ):
    """
    Initialize the server to a standard Messenger state.
    The purpose of having derived Server and Client classes
    is basically to initialize 2 Messenger objects to the same
    starting state.  Once initialized, both server and client
    are virtually identical in this program.
    """
    def __init__( self, listen_port ):
        super().__init__( listen_port )
        self.listen_sock = self.open_listener( self.port )
        self.text_sock, addr = self.accept_connection()
        self.server_host = addr[0]
        file_req_port = self.text_sock.recv( 4 ).decode()
        print("Client sent back listen port " + file_req_port + ".")
        try:
            int(file_req_port)
        except ValueError:
            print("The client did not send back a valid port number.")
            sys.exit(1)
        self.server_port = file_req_port


class Client( Messenger ):
    def __init__( self, listen_port, host, port ):
        super().__init__( listen_port )
        self.server_host = host
        self.server_port = port
        self.text_sock = self.request_connection( self.server_host, self.server_port )
        if self.text_sock is None:
            print("Could not open socket.")
            sys.exit(1)
        print("Connection accepted.  Sending listen port " + listen_port + ".")
        self.text_sock.send( listen_port.encode() )
        self.listen_sock = self.open_listener( listen_port )


def main():
    parsed_args = parse_opts( argv, len(argv) )
    if parsed_args[0]:
        m = Server( parsed_args[1] )
    else:
        m = Client( parsed_args[1], parsed_args[2], parsed_args[3] )

    m.run_messenger()

main()