import os
import socket
import sys
import threading

exit_event = threading.Event()
users = []


def getOnlineusers():
    global users
    online_users = []
    for user_id, user in enumerate(users):
        if user[0]:
            online_users.append(user_id)
    return online_users


def checkValiduser(user_id):
    global users
    try:
        if users[user_id][0]:
            return True
        else:
            return False
    except IndexError:
        return False


def handleSend(user_id, content, id_from=-1, status=0):
    global users
    connection = users[user_id][1]
    if status:
        format_info = 'FILE|' + str(users[user_id][2]) + '|' + str(id_from)
        connection.send(format_info.encode('utf-8'))
        check = connection.recv(1024).decode('utf-8')
        if check == 'OK':
            with open(str(user_id) + 'FileCache', 'rb') as file:
                while True:
                    data = file.read(1024)
                    if not data:
                        break
                    connection.send(data)
            connection.send('EOF'.encode('utf-8'))
            print('文件发送完成')
        else:
            print('文件接收异常终止:客户端未响应')
    elif id_from != -1:
        send_message = f'用户{id_from}给你发了消息: ' + content
        connection.send(send_message.encode('utf-8'))
        print('已发给目标用户')
    else:
        users[user_id][1].send(content.encode('utf-8'))


def receiveFile(user_id):
    global users
    connection = users[user_id][1]
    print('接收文件名')
    users[user_id][2] = connection.recv(1024).decode('utf-8')
    print(f'发送的文件名为{users[user_id][2]}')
    with open(str(user_id) + 'FileCache', 'wb') as file:
        while True:
            data = connection.recv(1024)
            if data.decode('utf-8', errors='ignore') == 'EOF':
                break
            elif not data:
                raise ConnectionResetError
            file.write(data)
        print('文件接收完成')


def handleRequset(connection, user_id):
    global  users
    try:
        while not exit_event.is_set():
            result = connection.recv(1024).decode('utf-8')
            if not result:
                print(f'用户{user_id}寿终正寝')
                users[user_id][0] = 0
                if os.path.exists(str(user_id) + 'FileCache'):
                    os.remove(str(user_id) + 'FileCache')
                break
            if result[0].isdigit():
                stat_code = int(result[0])
                result = result[1:]
                if stat_code == 1:
                    print(f'收到用户{user_id}发给服务器的消息', result)
                    handleSend(user_id, '服务器收到你发的消息')
                elif stat_code == 2:
                    print(f'收到{user_id}的消息转发请求')
                    result = result.split(' ', maxsplit=1)
                    to_id = int(result[0])
                    if checkValiduser(to_id):
                        print(f'用户{user_id}向{to_id}发送消息')
                        handleSend(to_id, result[1], user_id)
                        handleSend(user_id, '你的消息已发送')
                    else:
                        print(f'用户{user_id}请求无效用户')
                        handleSend(user_id, '目标用户无效')
                elif stat_code == 3:
                    print(f'收到用户{user_id}的文件转发请求')
                    if os.path.exists(str(user_id) + 'FileCache'):
                        to_id = int(result)
                        if checkValiduser(to_id):
                            handleSend(user_id, 'FILESEND', to_id, 1)
                            print(f'用户{user_id}的文件已转发给{to_id}')
                            handleSend(user_id, '你的文件已转发')
                        else:
                            print(f'用户{user_id}请求的用户不存在')
                    else:
                        print(f'用户{user_id}没有文件缓存')
                        handleSend(user_id, '没有文件缓存，先缓存你的文件')
                elif stat_code == 4:
                    print(f'用户{user_id}请求在线列表')
                    handleSend(user_id, str(getOnlineusers()))
                elif stat_code == 9:
                    print(f'用户{user_id}要更新文件缓存')
                    receiveFile(user_id)
                    print('文件缓存更新完成')
            else:
                print(f'收到来自用户{user_id}无法解码的消息', result)
    except ConnectionResetError:
        print(f'用户{user_id}强制关闭连接')
        users[user_id][0] = 0
        if os.path.exists(str(user_id) + 'FileCache'):
            os.remove(str(user_id) + 'FileCache')
    except ConnectionAbortedError:
        print('handleRequest退出')
        users[user_id][0] = 0
        if os.path.exists(str(user_id) + 'FileCache'):
            os.remove(str(user_id) + 'FileCache')


def handleConnect(connection):
    global users
    try:
        while not exit_event.is_set():
            new_user_id = -1
            client, addr = connection.accept()
            print(f'地址{addr}请求连接')
            for index, user in enumerate(users):
                if not user[0]:
                    print(user[0])
                    new_user_id = index
                    users[index] = [1, client, '']
            if new_user_id == -1:
                new_user_id = len(users)
                users.append([1, client, ''])
                print(len(users))
            threading.Thread(target=handleRequset, args=(client, new_user_id)).start()
            print(f'地址{addr}已连接，分配id{new_user_id}')
    except socket.error as e:
        print('你都自己开服务器了，我就不做错误处理了', e)


if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 12345))
    server.listen(100)
    threading.Thread(target=handleConnect, args=(server,)).start()
    print('服务器上线')
    try:
        while not exit_event.is_set():
            admin_input = input('等待指令\n')
            if admin_input == 'exit':
                break
    finally:
        for inner_user in users:
            inner_user[1].close()
        server.close()
        exit_event.set()
        sys.exit(114514)
