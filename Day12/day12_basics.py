#!/usr/bin/env python3
"""
Day 12: Socket 网络编程 —— TCP/UDP 实战
每个模块均可独立运行，演示 socket 编程核心概念
面向 C++ 开发者：底层 API 几乎一样，开发效率天差地别
"""

import socket
import select
import struct
import time
import threading
import queue
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# 1. TCP 客户端 — 连接服务器并收发数据
# ============================================================
def demo_tcp_client():
    """演示：TCP 客户端连接 HTTP 服务器获取首页"""
    print("\n" + "=" * 60)
    print("1. TCP 客户端 — HTTP GET 请求")
    print("=" * 60)

    host = "example.com"
    port = 80

    print(f"[*] 正在连接 {host}:{port} ...")

    # C++ 对比：socket(AF_INET, SOCK_STREAM, 0) → connect() → send() → recv()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect((host, port))
        print(f"[+] 已连接到 {sock.getpeername()}")

        # 发送 HTTP GET 请求
        request = (
            f"GET / HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: Day12-PythonSocket\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        sock.sendall(request.encode())
        print("[→] 请求已发送")

        # 接收响应
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk

        # 解析 HTTP 响应
        header, _, body = response.partition(b"\r\n\r\n")
        status_line = header.split(b"\r\n")[0].decode()
        print(f"[←] 响应: {status_line}")
        print(f"[←] 收到 {len(response)} 字节")

        # 显示前几行
        lines = body.decode("utf-8", errors="replace").split("\n")[:5]
        for line in lines:
            if line.strip():
                print(f"    {line.strip()[:80]}")

    except socket.timeout:
        print("[!] 连接超时")
    except socket.gaierror as e:
        print(f"[!] DNS 解析失败: {e}")
    except ConnectionRefusedError:
        print("[!] 连接被拒绝")
    finally:
        sock.close()
        print("[*] 连接已关闭")


# ============================================================
# 2. TCP 服务器 — 回显服务（Echo Server）
# ============================================================
def demo_tcp_echo_server():
    """演示：TCP 回显服务器（在后台线程运行，用客户端测试）"""
    print("\n" + "=" * 60)
    print("2. TCP 回显服务器 + 客户端测试")
    print("=" * 60)

    results = queue.Queue()

    def echo_server():
        """后台运行的简易回显服务器"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # C++ 对比：SO_REUSEADDR 在 C++ 中也是 setsockopt
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))  # 0 = 自动分配端口
        server.listen(1)

        host, port = server.getsockname()
        results.put(("listening", port))
        print(f"[*] 服务端监听 127.0.0.1:{port}")

        try:
            server.settimeout(3.0)
            client, addr = server.accept()
            print(f"[+] 客户端连接: {addr}")

            # 接收数据
            data = client.recv(1024)
            print(f"[←] 收到: {data.decode()}")

            # 回显（加上前缀标识）
            reply = f"Echo: {data.decode()}"
            client.sendall(reply.encode())
            print(f"[→] 回显: {reply}")

            client.close()
        except socket.timeout:
            results.put(("timeout", None))
            print("[!] 没有客户端连接（超时）")
        finally:
            server.close()

    # 启动服务器线程
    server_thread = threading.Thread(target=echo_server, daemon=True)
    server_thread.start()

    # 等待服务器就绪
    status, port = results.get(timeout=2.0)
    time.sleep(0.2)

    # 客户端连接测试
    print(f"\n[*] 客户端连接 127.0.0.1:{port} ...")
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))

    message = "Hello from C++ developer!"
    client.sendall(message.encode())
    print(f"[→] 发送: {message}")

    reply = client.recv(1024).decode()
    print(f"[←] 回复: {reply}")

    client.close()
    server_thread.join(timeout=2.0)
    print("[*] 测试完成")


# ============================================================
# 3. UDP 通信 — 无需连接的报文传输
# ============================================================
def demo_udp():
    """演示：UDP 发送和接收"""
    print("\n" + "=" * 60)
    print("3. UDP 通信 — 发送端 → 接收端")
    print("=" * 60)

    # C++ 对比：socket(AF_INET, SOCK_DGRAM, 0) → sendto() / recvfrom()
    # Python 中 UDP 不需要 connect()

    # 创建接收端
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("127.0.0.1", 0))  # 自动分配端口
    receiver.settimeout(2.0)
    host, port = receiver.getsockname()
    print(f"[*] UDP 接收端: 127.0.0.1:{port}")

    # 创建发送端
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    messages = [
        "Hello UDP",
        "这条消息可能丢包",
        "UDP 不保证顺序",
        "但速度很快",
    ]

    for msg in messages:
        sender.sendto(msg.encode(), ("127.0.0.1", port))
        print(f"[→] 发送: {msg}")
        time.sleep(0.1)

    sender.close()

    # 接收消息
    print("\n[*] 接收 UDP 消息 ...")
    try:
        for _ in range(len(messages)):
            data, addr = receiver.recvfrom(1024)
            print(f"[←] 来自 {addr}: {data.decode()}")
    except socket.timeout:
        print("[!] 部分消息丢失（UDP 特性）")

    receiver.close()
    print("[*] UDP 测试完成")


# ============================================================
# 4. DNS 解析 — gethostbyname / getaddrinfo
# ============================================================
def demo_dns():
    """演示：DNS 解析的各种用法"""
    print("\n" + "=" * 60)
    print("4. DNS 解析 — 域名 ↔ IP")
    print("=" * 60)

    # C++ 对比：getaddrinfo() / gethostbyname() 在 C++ 中需要手动释放链表
    targets = ["github.com", "baidu.com", "google.com"]

    for host in targets:
        try:
            ip = socket.gethostbyname(host)
            print(f"  {host:20s} → {ip}")
        except socket.gaierror as e:
            print(f"  {host:20s} → 解析失败: {e}")

    print()

    # 反向解析
    try:
        host_info = socket.gethostbyaddr("8.8.8.8")
        print(f"  反向: 8.8.8.8 → {host_info[0]}")
    except socket.herror:
        print(f"  反向: 8.8.8.8 → 无 PTR 记录")

    # 本机信息
    print(f"\n  本机主机名: {socket.gethostname()}")

    # getaddrinfo 详细解析
    print("\n  详细解析 localhost:")
    for info in socket.getaddrinfo("localhost", None):
        family, socktype, proto, canonname, sockaddr = info
        family_name = {socket.AF_INET: "IPv4", socket.AF_INET6: "IPv6"}.get(family, str(family))
        print(f"    {family_name}: {sockaddr}")


# ============================================================
# 5. 端口扫描基础 — connect_ex 探测
# ============================================================
def demo_port_scan():
    """演示：基础端口扫描（仅扫描本地常用端口，安全起见）"""
    print("\n" + "=" * 60)
    print("5. 端口扫描基础 — connect_ex 探测")
    print("=" * 60)

    # 常见的知名端口及其服务名
    COMMON_PORTS = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
        53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
        443: "HTTPS", 993: "IMAPS", 995: "POP3S",
        3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
        6379: "Redis", 8080: "HTTP-Alt", 27017: "MongoDB",
    }

    target = "127.0.0.1"  # 只扫描本机，安全！

    def scan_single(port):
        """扫描单个端口，返回 (port, name, is_open)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            # C++ 对比：connect_ex 是 Python 独有的便捷方法
            # C++ 中需要 connect() + 检查 errno
            result = sock.connect_ex((target, port))
            return port, COMMON_PORTS.get(port, "?"), result == 0
        finally:
            sock.close()

    print(f"[*] 扫描目标: {target}")
    print(f"[*] 扫描端口: {min(COMMON_PORTS)}-{max(COMMON_PORTS)}")
    print(f"[*] 超时设置: 0.5s\n")

    # 单线程扫描（教学用）
    print("  端口   状态     服务")
    print("  " + "-" * 30)

    for port in COMMON_PORTS:
        p, name, is_open = scan_single(port)
        status = "\033[92mOPEN\033[0m" if is_open else "closed"
        if is_open:
            print(f"  {p:<6} {status:<22} {name}")
        else:
            print(f"  {p:<6} closed                {name}")

    print("\n[*] 扫描完成（仅本机，安全）")


# ============================================================
# 6. 多线程端口扫描 — 加速扫描
# ============================================================
def demo_threaded_scan():
    """演示：多线程端口扫描（大幅加速）"""
    print("\n" + "=" * 60)
    print("6. 多线程端口扫描 — ThreadPoolExecutor 加速")
    print("=" * 60)

    target = "127.0.0.1"
    ports = list(range(1000, 1011))  # 扫描少量端口做演示

    def scan_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        try:
            result = sock.connect_ex((target, port))
            return port, result == 0
        finally:
            sock.close()

    print(f"[*] 扫描目标: {target}")
    print(f"[*] 端口范围: {ports[0]}-{ports[-1]}")
    print(f"[*] 线程数: 5\n")

    start = time.time()
    open_ports = []

    # C++ 对比：C++ 中多线程扫描需要手动管理线程池/互斥锁
    # Python 的 ThreadPoolExecutor 一行搞定
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scan_port, p): p for p in ports}
        for future in as_completed(futures):
            port, is_open = future.result()
            if is_open:
                open_ports.append(port)
                print(f"  [OPEN] 端口 {port}")

    elapsed = time.time() - start
    print(f"\n  耗时: {elapsed:.2f}s")
    print(f"  开放端口: {open_ports if open_ports else '无'}")
    print(f"  对比单线程: 约快 {len(ports) / 5:.1f}x")


# ============================================================
# 7. select 多路复用 — 同时处理多个连接
# ============================================================
def demo_select():
    """演示：select 监听多个 socket"""
    print("\n" + "=" * 60)
    print("7. select — 同时监控多个连接")
    print("=" * 60)

    results = queue.Queue()

    def select_server():
        """select 驱动的回显服务器"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(5)
        server.setblocking(False)

        host, port = server.getsockname()
        results.put(port)

        # C++ 对比：select() 函数签名几乎相同
        # Python 不需要手动管理 fd_set + FD_ZERO/FD_SET/FD_ISSET
        sockets_list = [server]
        start_time = time.time()

        while time.time() - start_time < 5.0:
            readable, _, _ = select.select(sockets_list, [], [], 0.5)
            for s in readable:
                if s is server:
                    try:
                        client, addr = s.accept()
                        print(f"  [select] 新连接: {addr}")
                        client.setblocking(False)
                        sockets_list.append(client)
                    except BlockingIOError:
                        pass
                else:
                    try:
                        data = s.recv(1024)
                        if data:
                            s.sendall(b"select-echo: " + data)
                        else:
                            sockets_list.remove(s)
                            s.close()
                    except (BlockingIOError, ConnectionResetError):
                        sockets_list.remove(s)
                        s.close()

        # 清理
        for s in sockets_list:
            s.close()

    # 启动 select 服务器
    server_thread = threading.Thread(target=select_server, daemon=True)
    server_thread.start()
    port = results.get(timeout=2.0)
    print(f"[*] select 服务器: 127.0.0.1:{port}")
    time.sleep(0.2)

    # 多个客户端同时连接
    def make_request(client_id, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(("127.0.0.1", port))
        sock.sendall(msg.encode())
        reply = sock.recv(1024).decode()
        print(f"  [客户端{client_id}] 发送: {msg} → 回复: {reply}")
        sock.close()

    print("[*] 并发请求测试:")
    threads = []
    for i in range(3):
        t = threading.Thread(
            target=make_request,
            args=(i + 1, f"Hello from client {i + 1}")
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=2.0)

    server_thread.join(timeout=1.0)
    print("[*] select 演示完成")


# ============================================================
# 8. socket 选项与地址信息
# ============================================================
def demo_socket_options():
    """演示：常用 socket 选项和地址信息"""
    print("\n" + "=" * 60)
    print("8. Socket 选项 — setsockopt / getsockname")
    print("=" * 60)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 获取默认选项值
    print("  默认 socket 选项:")
    print(f"    SO_REUSEADDR: {sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)}")
    print(f"    SO_KEEPALIVE: {sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)}")
    print(f"    SO_RCVBUF:    {sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)}")
    print(f"    SO_SNDBUF:    {sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)}")
    print(f"    TCP_NODELAY:  {sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY)}")
    print()

    # 设置并验证
    print("  设置 SO_REUSEADDR = 1")
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f"    SO_REUSEADDR: {sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)}")

    # 绑定自动分配的端口，查看地址信息
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    print(f"\n  绑定后地址: {host}:{port}")
    print(f"  socket 家族: {sock.family} (AF_INET = {socket.AF_INET})")
    print(f"  socket 类型: {sock.type} (SOCK_STREAM = {socket.SOCK_STREAM})")
    print(f"  socket 协议: {sock.proto}")

    sock.close()


# ============================================================
# 9. 超时与错误处理
# ============================================================
def demo_error_handling():
    """演示：socket 错误处理的各种场景"""
    print("\n" + "=" * 60)
    print("9. 错误处理 — 超时、拒绝、DNS 失败")
    print("=" * 60)

    test_cases = [
        ("连接不存在的主机", ("192.0.2.1", 80), "timeout"),
        ("连接拒绝（无服务）", ("127.0.0.1", 19999), "refused"),
        ("DNS 解析失败", ("this-domain-does-not-exist-xyz.com", 80), "dns"),
    ]

    for desc, target, expected in test_cases:
        print(f"\n  测试: {desc}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)

        try:
            sock.connect(target)
            print(f"    ✓ 意外成功")
        except socket.timeout:
            print(f"    ⏱ 超时 — 这很正常（主机不存在或不可达）")
        except ConnectionRefusedError:
            print(f"    ✗ 连接被拒绝 — 端口无服务监听")
        except socket.gaierror as e:
            print(f"    ✗ DNS 错误: {e}")
        except OSError as e:
            print(f"    ✗ 系统错误: {e}")
        finally:
            sock.close()

    # 演示 connect_ex 不抛异常的特性
    print(f"\n  connect_ex 测试（不存在的主机）:")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    result = sock.connect_ex(("192.0.2.1", 80))
    print(f"    connect_ex 返回码: {result} (0=成功, 非0=失败)")
    sock.close()


# ============================================================
# 命令行入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Day 12: Socket 网络编程实战",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python day12_basics.py              # 运行所有演示
  python day12_basics.py --tcp        # 仅运行 TCP 演示
  python day12_basics.py --scan       # 仅运行端口扫描演示
        """
    )
    parser.add_argument("--tcp", action="store_true", help="运行 TCP 客户端/服务器演示")
    parser.add_argument("--udp", action="store_true", help="运行 UDP 演示")
    parser.add_argument("--dns", action="store_true", help="运行 DNS 解析演示")
    parser.add_argument("--scan", action="store_true", help="运行端口扫描演示")
    parser.add_argument("--select", action="store_true", help="运行 select 多路复用演示")
    parser.add_argument("--options", action="store_true", help="运行 socket 选项演示")
    parser.add_argument("--errors", action="store_true", help="运行错误处理演示")

    args = parser.parse_args()

    # 如果没有任何参数，运行全部
    run_all = not any([args.tcp, args.udp, args.dns, args.scan,
                       args.select, args.options, args.errors])

    print("=" * 60)
    print("  Day 12: Socket 网络编程 — Python 实战")
    print("  C++ 开发者视角：底层 API 相同，开发效率×10")
    print("=" * 60)

    if run_all or args.tcp:
        demo_tcp_client()
        demo_tcp_echo_server()

    if run_all or args.udp:
        demo_udp()

    if run_all or args.dns:
        demo_dns()

    if run_all or args.scan:
        demo_port_scan()
        demo_threaded_scan()

    if run_all or args.select:
        demo_select()

    if run_all or args.options:
        demo_socket_options()

    if run_all or args.errors:
        demo_error_handling()

    print("\n" + "=" * 60)
    print("  Day 12 完成！下次见 👋")
    print("  实用工具: python port_scanner.py --demo")
    print("=" * 60)


if __name__ == "__main__":
    main()
