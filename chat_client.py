import os.path
import socket
import sys
from multiprocessing import Queue
import threading
import tkinter
from tkinter import filedialog
import time
import re


class HandleServerReturn(threading.Thread):
    def __init__(self, inner_connection):
        self.connection = inner_connection
        super().__init__()

    def run(self):
        try:
            while not exit_event.is_set():
                server_return = self.connection.recv(1024).decode('utf-8')
                if server_return[:4] == 'FILE':
                    file_name = server_return.split('|')[1]
                    id_from = server_return.split('|')[2]
                    print(f'收到来自{id_from}的文件{file_name}')
                    with open(file_name, 'wb') as file:
                        self.connection.send('OK'.encode('utf-8'))
                        while True:
                            data = self.connection.recv(1024)
                            if data.decode('utf-8', errors='ignore') == 'EOF':
                                break
                            elif not data:
                                raise ConnectionResetError
                            file.write(data)
                        print('文件接收完成')
                        continue
                print(server_return)
        except ConnectionAbortedError:
            print('退出')
        except socket.error as e:
            print('有点问题', e)
        except AttributeError:
            print('服务器未创建')
        finally:
            exit_event.set()


class SendingModel(threading.Thread):
    def __init__(self, inner_host, inner_port):
        self.host = inner_host
        self.port = inner_port
        self.queue = None
        self.connection = None
        super().__init__()

    def sendFile(self, file_path):
        print('开始发送流程')
        time.sleep(1)
        print('发送文件名')
        file_name = os.path.basename(file_path)
        self.connection.send(file_name.encode('utf-8'))
        time.sleep(1)
        print('发送文件体')
        with open(file_path, 'rb') as file:
            while True:
                data = file.read(1024)
                if not data:
                    break
                self.connection.send(data)
        print('发送完成')
        time.sleep(1)
        print('发送结束标志')
        self.connection.send('EOF'.encode('utf-8'))

    def run(self):
        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # noinspection PyBroadException
        try:
            self.connection.connect((self.host, self.port))
        except Exception:
            print('你和服务器有一个有问题')
        self.queue = Queue()
        while not exit_event.is_set():
            try:
                message = self.queue.get()
                if message[0] == -1:
                    break
                if message[0] <= 4:
                    send_message = str(message[0]) + message[1]
                    self.connection.send(send_message.encode('utf-8'))
                    print('消息已发送')
                elif message[0] == 9:
                    self.connection.send('9'.encode('utf-8'))
                    print('已通知服务器准备接收文件')
                    self.sendFile(message[1])
            except socket.error as e:
                print('貌似服务器挂了哦', e)
                exit_event.set()


class Operations:
    def __init__(self):
        self.file_path = None

    def choose_file(self):
        print('调用文件选择函数')
        tkinter.Tk().withdraw()
        return filedialog.askopenfilename(title="选择文件")

    def handleUserinput(self, raw_input):
        if raw_input[0] == '$':
            raw_input = raw_input[1:]
            if raw_input == 'file':
                self.file_path = self.choose_file()
                if self.file_path:
                    print('路径已保存')
                else:
                    print('未选择文件')
        elif raw_input[:6] == 'server':
            send_message = raw_input[7:]
            User_send.queue.put((1, send_message))
            print('消息已传给发送函数')
        elif raw_input[:2] == 'to':
            send_message = raw_input[3:]
            valid_check = send_message.split(' ', maxsplit=1)
            if valid_check[0].isdigit():
                User_send.queue.put((2, send_message))
            else:
                print('无效输入')
        elif raw_input[:4] == 'file':
            if raw_input[4:6] == 'to':
                send_message = raw_input[7:]
                if send_message.isdigit():
                    User_send.queue.put((3, send_message))
                    print('文件发送请求已传给发送函数')
                else:
                    print('无效输入')
            else:
                if self.file_path:
                    User_send.queue.put((9, self.file_path))
                    print('文件缓存更新请求已传给发送函数')
                else:
                    print('未指定文件！')
        elif raw_input[:5] == 'query':
            User_send.queue.put((4, 'place'))


host = '127.0.0.1'
port = 12345
exit_event = threading.Event()

if __name__ == '__main__':
    host = input('输入服务器IP:\n')
    ip_check = re.compile(r'^((25[0-5]|2[0-4]\d|[0-1]?\d?\d)\.){3}(25[0-5]|2[0-4]\d|[0-1]?\d?\d)$')
    valid = ip_check.match(host)
    if valid is None:
        print('输入的ip无效')
        sys.exit(1919810)
    User_send = SendingModel(host, port)
    User_send.start()
    User_operation = Operations()
    time.sleep(1)
    Receive_server = HandleServerReturn(User_send.connection)
    Receive_server.start()
    try:
        while not exit_event.is_set():
            if exit_event.is_set():
                break
            user_input = input('键入指令\n')
            if user_input == 'exit':
                exit_event.set()
                User_send.queue.put((-1,))
                User_send.connection.close()
                continue
            else:
                User_operation.handleUserinput(user_input)
    except KeyboardInterrupt:
        exit_event.set()
        User_send.queue.put((-1,))
        User_send.connection.close()
    finally:
        sys.exit(114514)
