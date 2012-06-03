"""
Simple single threaded peer for a peer2peer network

Made for fun and to gain some experince with p2p networks

"""

import sys 
import socket
import errno
import uuid
import json
from pprint import pprint

BOOT_LIST = [('0.0.0.0', i) for i in range(9000, 9100)] # Fake boot list

class Peer(object):
    def __init__(self, port):
        self.port = port
        self.routing_table = {}
        self.guid = None
        self.host = None

    def _send(self, ip, port, request):
        """
        Send command to a peer
        
        """
        print ip, port
        # Create socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, int(port)))
        
        # Send command
        request.update({'origin': {'ip': '0.0.0.0', 'port': self.port}})
        s.send(json.dumps(request))
                
        # Handle response
        chunks = []
               
        while True:
            chunk = s.recv(1024)
            if not chunk: break
            chunks.append(chunk)
        s.close()
        
        return ''.join(chunks)  
    
    def join_network(self):
        """
        Join the network
        
        """
        # The boot list contains previous seen nodes.
        #   Each previous seen node is been checked (hardcode in this case)
        host_socket = None
        for ip, port in BOOT_LIST:
            print "Trying connect to %s:%s" % (ip, port)
            
            # Try connect to host
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((ip, port))
                   
                self.host = (ip, port) 
                host_socket = s
                
                # Connected to host!
                print "Host found on %s:%s" % (ip, port)
                
                # Send guid request
                request = {'action': 'request_guid'}
                request.update({'origin': {'ip': '0.0.0.0', 'port': self.port}})
                s.send(json.dumps(request))
                
                # Handle response
                chunks = []
               
                while True:
                    chunk = s.recv(1024)
                    if not chunk: break
                    chunks.append(chunk)
                s.close()
                
                response = json.loads(''.join(chunks))
                self.guid = response['response']
                
                # Host found, no need to check other previous seen nodes
                break

            except socket.error, v:
                error_code = v
                print "Failed to connect (%s)" % error_code
        
        if not host_socket:
            # No host could be found, so we assume we are the first peer
            print "No host could be found, use a self assigned guid"

            #   Self assigned guid
            self.guid = str(uuid.uuid4())
            self.routing_table[self.guid] = ('0.0.0.0', self.port)
             
        print 'This peer now has guid %s' % self.guid

    def request_routing_table(self):
        """
        Request a routing table from the host we connected to

        """
        response = self._send(
            self.host[0], 
            self.host[1], 
            {'action': 'request_routing_table'}
        )
        self.routing_table = json.loads(response)['response']

    def introduce(self):
        """
        Introduce ourself to other peers

        """
        for guid, address in self.routing_table.iteritems():
            try:
                print guid, address, self.port
                self._send(
                    address[0], 
                    address[1], 
                    {
                        'action': 'introduce',
                        'guid': self.guid,
                    }
                )
            except Exception, e:
                print e

    def connect(self):
        """
        Connect to the network

        """
        # Find boot node and request to join network on that node
        self.join_network()
        
        # Once a boot node has been found, request routing table
        if self.host:
            self.request_routing_table()

        # Introduce ourself to existing peers
        self.introduce()

        print 'Connection procedure ready'

    def leave(self):
        """
        Leave network

        """
        pass

    def listen(self):
        """
        Listen for incomming connections

        """
        incomming_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        incomming_socket.bind((socket.gethostname(), int(self.port)))
        incomming_socket.listen(5)
        print 'Incomming socket initialized, waiting for incomming connections...'

        def request_guid(address, request):
            guid = str(uuid.uuid4())
            self.routing_table[guid] = (request['origin']['ip'], request['origin']['port'])

            return {
                'response': str(guid)
            }

        def request_routing_table(address, request):
            return {
                'response': self.routing_table
            }

        def introduce(address, request):
            guid = request.get('guid')
            address = request.get('address')
            if not guid in self.routing_table:
                self.routing_table[guid] = address
           
            print "%s introduced itself" % guid 
            return {
                'response': 'hi %s!' % guid
            }
        
        actions = {
            'request_guid': request_guid,
            'request_routing_table': request_routing_table,
            'introduce': introduce,
        }
        
        while True:
            # Wait for a incomming connection
            print  'Waiting...'
            chunks = []
            clientsocket, address = incomming_socket.accept()
            
            print 'Incomming connection: %s' % (address,)
            # Handle incomming request
            message = clientsocket.recv(1024)
            
            # Handle incomming request
            request = json.loads(message)
            action = actions.get(request['action'])

            # Response
            print 'Requested: %s' % action.__name__
            response = json.dumps(action(address, request=request))
            clientsocket.sendall(response)
            clientsocket.close()

    def run(self):
        """
        Run this peer

        """
        # Lets connect
        self.connect()

        # Listen
        self.listen()

if __name__ == "__main__":
    Peer(sys.argv[1]).run()

