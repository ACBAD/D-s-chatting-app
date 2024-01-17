import socket
import sys
from multiprocessing import Queue
import threading
import tkinter as tk
from tkinter import filedialog
import time


def choose_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="选择文件")
    return file_path


class HandleServerReturn(threading.Thread):
    def __init__(self, inner_connection):
        self.connection = inner_connection
        super().__init__()

    def run(self):
        try:
            while not exit_event.is_set():
                server_return = self.connection.recv(1024).decode('utf-8')
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
        print('正式开始发送')
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
            self.connection.send('0客户端初始化'.encode('utf-8'))
        except Exception:
            print('你和服务器有一个有问题')
        self.queue = Queue()
        while not exit_event.is_set():
            try:
                message = self.queue.get()
                if message[0] == -1:
                    break
                if message[0] <= 4:
                    send_message = str(message[1]) + message[1]
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
    def __init__(self, queue):
        self.send_queue = queue
        self.file_path = None

    def handleUserinput(self, raw_input):
        if raw_input[0] == '$':
            raw_input = raw_input[1:]
            if raw_input == 'file':
                self.file_path = choose_file()
                if self.file_path:
                    print('路径已保存')
                else:
                    print('未选择文件')
        elif raw_input[:6] == 'server':
            send_message = raw_input[7:]
            self.send_queue.put((1, send_message))
            print('消息已传给发送函数')
        elif raw_input[:2] == 'to':
            send_message = raw_input[3:]
            self.send_queue.put((2, send_message))
        elif raw_input[:4] == 'file':
            if raw_input[4:6] == 'to':
                send_message = raw_input[7:]
                self.send_queue.put((3, send_message))
                print('文件发送请求已传给发送函数')
            else:
                if self.file_path:
                    self.send_queue.put((9, self.file_path))
                    print('文件缓存更新请求已传给发送函数')
                else:
                    print('未指定文件！')
        elif raw_input[:5] == 'query':
            self.send_queue.put((4, 'place'))


host = '127.0.0.1'
port = 12345
exit_event = threading.Event()

if __name__ == '__main__':
    User_send = SendingModel(host, port)
    User_send.start()
    User_operation = Operations(User_send.queue)
    time.sleep(1)
    Receive_server = HandleServerReturn(User_send.connection)
    Receive_server.start()
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
    sys.exit(114514)
