#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import select
import socket
import struct

from typing import Union, Callable

__all__ = [
    'SimpleMessage', 'SimpleMessageServer', 'SimpleMessageClient',
    'PyUtilsNetworkException', 'InvalidMessage'
]

'''
SimpleMessage structure

    head(16 byte)
        magic(4 byte): \x22\x33\x41\x61
        body_size(4 byte)
        type(1 byte): MESSAGE_TYPE_COMMAND(\x01), MESSAGE_TYPE_DATA(\x02)
        padding(7 byte)
    body<MESSAGE_TYPE_COMMAND>(variable byte)
        command_name_size(4 byte)
        command_name(variable byte)

    body<MESSAGE_TYPE_DATA>(variable byte)
        data(variable byte)
'''

class SimpleMessage:
    
    MESSAGE_TYPE_INVALID = 0
    MESSAGE_TYPE_COMMAND = 1
    MESSAGE_TYPE_DATA = 2
    MESSAGE_TYPE_END = 3

    FIELD_MAGIC_OFFSET = 0
    FIELD_MAGIC_END = FIELD_MAGIC_OFFSET + 4
    FIELD_BODY_SIZE_OFFSET = FIELD_MAGIC_END
    FIELD_BODY_SIZE_END = FIELD_BODY_SIZE_OFFSET + 4
    FIELD_TYPE_OFFSET = FIELD_BODY_SIZE_END
    FIELD_TYPE_END = FIELD_TYPE_OFFSET + 1

    MAGIC_NUMBER = 0x22334161

    INVALID_MESSAGE_DISPLAY = "[INVALID MESSAGE]"

    def __init__(self):
        self.__header = b''
        self.__body = b''
        self.__valid = False
        self.__body_size = 0
        self.__type = SimpleMessage.MESSAGE_TYPE_INVALID
        self.__command_name:str = ''
        self.__message_data:bytes = b''

    def __repr__(self):
        if not self.to_bytes(): return SimpleMessage.INVALID_MESSAGE_DISPLAY
        infos = []
        if self.is_command():
            infos.append("type: COMMAND")
        elif self.is_data():
            infos.append("type: DATA")
        infos.append(f"body size: {self.__body_size}")
        if self.is_command():
            infos.append(f"command name: {self.__command_name}")
        elif self.is_data():
            infos.append(f"data: {self.__message_data}")
        return ' | '.join(infos)

    __str__ : __repr__

    @property
    def message_data(self):
        return self.__message_data
    
    @message_data.setter
    def message_data(self, data:Union[str, bytes]):
        if not isinstance(data, (str, bytes)): return
        if isinstance(data, str):
            self.__message_data = data.encode('utf-8')
        else:
            self.__message_data = data
        self.__type = SimpleMessage.MESSAGE_TYPE_DATA
        self.__body_size = len(data)

    @property
    def command_name(self):
        return self.__command_name

    @command_name.setter
    def command_name(self, command:str):
        if not isinstance(command, str): return
        self.__body_size = 4 + len(command)
        self.__command_name = command
        self.__type = SimpleMessage.MESSAGE_TYPE_COMMAND

    @property
    def valid(self):
        return self.__valid

    @property
    def body_size(self):
        return self.__body_size

    @property
    def header(self):
        return self.__header

    @property
    def body(self):
        return self.__body

    def set_header(self, header:bytes):
        if not isinstance(header, bytes):
            return False
        if len(header) != 0x10:
            return False
        magic = struct.unpack(
            '!I', 
            header[SimpleMessage.FIELD_MAGIC_OFFSET:SimpleMessage.FIELD_MAGIC_END]
        )[0]
        if magic != SimpleMessage.MAGIC_NUMBER:
            return False
        body_size = struct.unpack(
            '!I', 
            header[SimpleMessage.FIELD_BODY_SIZE_OFFSET:SimpleMessage.FIELD_BODY_SIZE_END]
        )[0]
        message_type = struct.unpack(
            'B', 
            header[SimpleMessage.FIELD_TYPE_OFFSET:SimpleMessage.FIELD_TYPE_END]
        )[0]
        if SimpleMessage.is_valid_type(self.__type):
            return False
        self.__body = b''
        self.__body_size = body_size
        self.__type = message_type
        self.__valid = True
        self.__header = header
        return True

    def set_body(self, body:bytes):
        if not self.__header: return False
        if not isinstance(body, bytes): return False
        if self.__body_size != len(body): return False
        if self.is_command():
            if len(body) < 4: return False
            command_name_size = struct.unpack('!I', body[0:4])[0]
            command_name = body[4:]
            if command_name_size != len(command_name): return False
            try:
                self.__command_name = command_name.decode('utf-8')
            except UnicodeDecodeError:
                return False
        elif self.is_data():
            self.__message_data = body
        self.__body = body
        return True

    def is_command(self):
        return self.__type == SimpleMessage.MESSAGE_TYPE_COMMAND

    def is_data(self):
        return self.__type == SimpleMessage.MESSAGE_TYPE_DATA

    def to_bytes(self):
        if not SimpleMessage.is_valid_type(self.__type): return None
        if not self.__header:
            header = struct.pack(
                '!IIB', SimpleMessage.MAGIC_NUMBER, self.__body_size, self.__type
            ).ljust(0x10, b'\x00')
        else:
            header = self.__header

        if not self.__body:
            body = b''
            if self.is_command():
                if 4 + len(self.__command_name) != self.__body_size: return None
                body += struct.pack('!I', len(self.__command_name))
                body += self.__command_name.encode('utf-8')
            elif self.is_data():
                if not isinstance(self.__message_data, (str, bytes)): return None
                if len(self.__message_data) != self.__body_size: return None
                data = self.__message_data
                if isinstance(data, str):
                    data = data.encode('utf-8')
                body += data
        else:
            body = self.__body

        return header + body

    @staticmethod
    def is_valid_type(message_type:int):
        if message_type <= SimpleMessage.MESSAGE_TYPE_INVALID:
            return False
        if message_type >= SimpleMessage.MESSAGE_TYPE_END:
            return False
        return True

class PyUtilsNetworkException(Exception):
    '''PyUtilsNetworkException'''

class InvalidMessage(PyUtilsNetworkException):
    '''InvalidMessage'''

class ConnectionClosed(PyUtilsNetworkException):
    '''ConnectionClosed'''

class SimpleMessageNode:

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @staticmethod
    def recv_bytes(s:socket.socket, size:int):
        recv = b''
        while size:
            data = s.recv(size)
            if not data: raise ConnectionClosed
            size -= len(data)
            recv += data
        return recv

    @staticmethod
    def recv_message(s:socket.socket):
        header = SimpleMessageNode.recv_bytes(s, 0x10)
        message = SimpleMessage()
        assert message.set_header(header)
        body = SimpleMessageNode.recv_bytes(s, message.body_size)
        assert message.set_body(body)
        return message

class SimpleMessageServer(SimpleMessageNode):

    def __init__(self, host:str='0.0.0.0', port:int=0):
        SimpleMessageNode.__init__(self)
        self._socket.setblocking(False)
        self._socket.bind((host, port))
        self._socket.listen()
        self.__running = False
        self.__readable_sockets = [self._socket]
        self.__listener:Callable[[SimpleMessage], SimpleMessage] = None

    @property
    def sockets(self):
        return self.__readable_sockets

    def address(self):
        try:
            return self._socket.getsockname()
        except OSError:
            return (None, None)

    def host(self):
        return self.address()[0]
    
    def port(self):
        return self.address()[1]

    def close(self):
        self.__running = False
        self._socket.close()

    def set_listener(self, listener:Callable[[SimpleMessage], SimpleMessage]):
        self.__listener = listener

    def handle_client(self, client:socket.socket):
        try:
            message = self.recv_message(client)
        except:
            self.__readable_sockets.remove(client)
            return
        if not self.__listener: return
        try:
            response = self.__listener(message)
            if isinstance(response, SimpleMessage):
                client.sendall(response.to_bytes())
        except Exception:
            pass

    def run_forever(self):
        self.__running = True
        while self.__running:
            try:
                readable, _, _ = select.select(
                    self.__readable_sockets, [], [], 0.01
                )
                for s in readable:
                    if s is self._socket:
                        try:
                            client, _ = self._socket.accept()
                        except OSError:
                            continue
                        self.__readable_sockets.append(client)
                    else:
                        self.handle_client(client)
            except KeyboardInterrupt:
                self.__running = False

class SimpleMessageClient(SimpleMessageNode):

    def __init__(self, server_host:str, server_port:int):
        SimpleMessageNode.__init__(self)
        self._socket.connect((server_host, server_port))

    def send(self, message:SimpleMessage):
        if not isinstance(message, SimpleMessage): return
        self._socket.sendall(message.to_bytes())

    def recv(self):
        return SimpleMessageNode.recv_message(self._socket)

    def close(self):
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
        
