import socket
import threading

def forward_data(src_socket, dst_socket):
    """将数据从源端口转发到目标端口"""
    try:
        while True:
            data = src_socket.recv(1024)
            if not data:
                break
            dst_socket.sendall(data)
    except Exception as e:
        print(f"Forwarding error: {e}")
    finally:
        src_socket.close()
        dst_socket.close()

def handle_client(client_socket, dst_ip, dst_port):
    """处理客户端连接并转发到目标地址"""
    try:
        # 连接到目标地址
        dst_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dst_socket.connect((dst_ip, dst_port))

        # 启动线程转发数据
        threading.Thread(target=forward_data, args=(client_socket, dst_socket)).start()
        threading.Thread(target=forward_data, args=(dst_socket, client_socket)).start()
    except Exception as e:
        print(f"Connection error: {e}")
        client_socket.close()

def main():
    # 配置源端口和目标地址
    src_port = 8123
    dst_ip = "192.6.6.33"
    dst_port = 8123

    # 创建 TCP 服务器
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", src_port))
    server.listen(5)
    print(f"Port forwarding started: {src_port} -> {dst_ip}:{dst_port}")

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        threading.Thread(target=handle_client, args=(client_socket, dst_ip, dst_port)).start()

if __name__ == "__main__":
    main()
