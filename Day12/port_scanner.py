#!/usr/bin/env python3
"""
port_scanner.py —— 多线程端口扫描器

和 C++ 写的扫描器相比，Python 版代码量减少 80%，功能却更丰富。

特性:
  - 多线程并发扫描（可配置线程数）
  - 自动识别常见服务（80→HTTP, 22→SSH, 3306→MySQL...）
  - 支持多种输出格式（text / json / csv）
  - 支持扫描单端口、端口范围、端口列表
  - 连接超时可配置
  - IPv4 / 域名自动解析
  - --demo 模式：无需参数，演示所有功能

用法:
  python port_scanner.py 192.168.1.1                          # 扫描常见端口
  python port_scanner.py 192.168.1.1 1-1024                   # 扫描 1-1024
  python port_scanner.py 192.168.1.1 22,80,443,3306           # 扫描指定端口
  python port_scanner.py scanme.nmap.org 1-100 -t 50          # 50 线程扫描
  python port_scanner.py 192.168.1.1 1-1000 -f json           # JSON 输出
  python port_scanner.py --demo                               # 演示模式
"""

import socket
import sys
import time
import argparse
import json
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict


# ============================================================
# 知名端口 → 服务名映射
# ============================================================
PORT_SERVICES = {
    7:    "Echo",
    20:   "FTP-Data",
    21:   "FTP",
    22:   "SSH",
    23:   "Telnet",
    25:   "SMTP",
    53:   "DNS",
    67:   "DHCP-Server",
    68:   "DHCP-Client",
    69:   "TFTP",
    80:   "HTTP",
    88:   "Kerberos",
    110:  "POP3",
    111:  "RPC",
    119:  "NNTP",
    123:  "NTP",
    135:  "RPC-Endpoint",
    137:  "NetBIOS-NS",
    138:  "NetBIOS-DGM",
    139:  "NetBIOS-SSN",
    143:  "IMAP",
    161:  "SNMP",
    162:  "SNMP-Trap",
    194:  "IRC",
    389:  "LDAP",
    443:  "HTTPS",
    445:  "SMB",
    465:  "SMTPS",
    514:  "Syslog",
    515:  "LPD",
    543:  "KLogin",
    544:  "KShell",
    587:  "SMTP-Submit",
    631:  "IPP",
    636:  "LDAPS",
    873:  "rsync",
    993:  "IMAPS",
    995:  "POP3S",
    1080: "SOCKS",
    1433: "MSSQL",
    1521: "Oracle",
    1723: "PPTP",
    1883: "MQTT",
    2049: "NFS",
    2082: "cPanel",
    2083: "cPanel-SSL",
    2181: "ZooKeeper",
    2375: "Docker",
    2376: "Docker-TLS",
    3128: "Squid",
    3306: "MySQL",
    3389: "RDP",
    3690: "SVN",
    4369: "Erlang-EPMD",
    4444: "Metasploit",
    4567: "Verdaccio",
    4848: "GlassFish",
    5000: "Flask-Dev",
    5222: "XMPP",
    5353: "mDNS",
    5432: "PostgreSQL",
    5555: "ADB",
    5672: "RabbitMQ",
    5683: "CoAP",
    5900: "VNC",
    5938: "TeamViewer",
    5984: "CouchDB",
    5985: "WinRM-HTTP",
    5986: "WinRM-HTTPS",
    6379: "Redis",
    6443: "K8s-API",
    6667: "IRC-SSL",
    7474: "Neo4j",
    8000: "HTTP-Dev",
    8001: "HTTP-Dev",
    8006: "Proxmox-VE",
    8009: "AJP",
    8080: "HTTP-Alt",
    8081: "HTTP-Alt",
    8088: "HTTP-Alt",
    8443: "HTTPS-Alt",
    8880: "HTTP-Alt",
    8888: "HTTP-Alt / Jupyter",
    9000: "PHP-FPM / SonarQube",
    9001: "Supervisor",
    9042: "Cassandra",
    9090: "Prometheus",
    9092: "Kafka",
    9100: "Node-Exporter",
    9200: "Elasticsearch",
    9300: "Elasticsearch-TCP",
    9443: "K8s-API-Alt",
    9999: "HTTP-Alt",
    10000: "Webmin",
    11211: "Memcached",
    15672: "RabbitMQ-Mgmt",
    27017: "MongoDB",
    27018: "MongoDB-Shard",
    27019: "MongoDB-Config",
    28015: "RethinkDB",
    49152: "WinRM-Alt",
    50000: "SAP",
    50070: "HDFS-NN",
    50075: "HDFS-DN",
    61616: "ActiveMQ",
}


# ============================================================
# ANSI 颜色
# ============================================================
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    RED     = "\033[91m"
    MAGENTA = "\033[95m"
    MUTED   = "\033[90m"
    WHITE   = "\033[97m"


def colored(text, *codes):
    return "".join(codes) + text + C.RESET


# ============================================================
# 核心功能
# ============================================================
def parse_ports(port_spec):
    """解析端口规格，返回端口列表

    支持格式:
      "80"          → [80]
      "1-1024"      → [1, 2, ..., 1024]
      "22,80,443"   → [22, 80, 443]
      "1-10,80,443" → [1,2,...,10, 80, 443]
    """
    ports = []
    for part in port_spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            ports.extend(range(int(start), int(end) + 1))
        else:
            ports.append(int(part))
    return sorted(set(ports))


def resolve_host(host):
    """解析主机名或 IP，返回 IP 地址"""
    try:
        # 尝试直接解析为 IP（如果是 IP 则直接返回）
        socket.inet_pton(socket.AF_INET, host)
        return host
    except OSError:
        pass

    try:
        ip = socket.gethostbyname(host)
        return ip
    except socket.gaierror as e:
        raise ValueError(f"无法解析主机名 '{host}': {e}")


def get_service_name(port):
    """根据端口号获取服务名"""
    return PORT_SERVICES.get(port, "")


def scan_single(host, port, timeout):
    """扫描单个端口，返回 (port, is_open, service_name)"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        is_open = (result == 0)
        service = get_service_name(port) if is_open else ""
        return port, is_open, service
    except (socket.timeout, OSError):
        return port, False, ""
    finally:
        sock.close()


def scan_ports(host, ports, threads=50, timeout=1.0, verbose=False):
    """多线程扫描端口列表

    Args:
        host: 目标 IP 或域名
        ports: 端口列表
        threads: 并发线程数
        timeout: 连接超时（秒）
        verbose: 是否实时显示结果

    Returns:
        list of (port, service_name) 元组，只包含开放端口
    """
    ip = resolve_host(host)
    open_ports = []
    total = len(ports)

    if verbose:
        print(f"\n{colored('[※]', C.CYAN)} 目标: {colored(host, C.WHITE)} ({ip})")
        print(f"{colored('[※]', C.CYAN)} 端口: {ports[0]}-{ports[-1]} (共 {total} 个)")
        print(f"{colored('[※]', C.CYAN)} 线程: {threads}  超时: {timeout}s")
        print(f"{colored('[※]', C.CYAN)} 开始扫描...\n")

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(scan_single, ip, p, timeout): p for p in ports}
        done = 0

        for future in as_completed(futures):
            port, is_open, service = future.result()
            done += 1

            if is_open:
                open_ports.append((port, service))
                if verbose:
                    svc_str = f" ({service})" if service else ""
                    print(f"  {colored('[OPEN]', C.GREEN)} "
                          f"{colored(str(port), C.YELLOW):<8} {svc_str}")

            elif verbose and done % max(1, total // 20) == 0:
                pct = done * 100 // total
                print(f"\r  {colored('[*]', C.MUTED)} 进度: {pct}% ({done}/{total})",
                      end="", flush=True)

    elapsed = time.time() - start_time
    open_ports.sort(key=lambda x: x[0])

    if verbose:
        print(f"\n{colored('[※]', C.CYAN)} 扫描完成!")
        print(f"{colored('[※]', C.CYAN)} 耗时: {elapsed:.2f}s  "
              f"速率: {total / elapsed:.0f} ports/s")

    return open_ports, elapsed, total


# ============================================================
# 输出格式
# ============================================================
def output_text(host, results, elapsed, total):
    """纯文本输出"""
    open_ports, _ = results if isinstance(results, tuple) else (results, 0)
    if not open_ports:
        print(f"\n{colored('[!]', C.RED)} 未发现开放端口")
        return

    print(f"\n{colored('═' * 50, C.MUTED)}")
    print(f"{colored(' 扫描结果', C.BOLD)}")

    for port, service in open_ports:
        svc_str = f"{colored(service, C.CYAN)}" if service else ""
        print(f"  {colored(str(port), C.YELLOW):<8} {colored('OPEN', C.GREEN):<8} {svc_str}")

    print(f"{colored('═' * 50, C.MUTED)}")
    print(f"  共 {colored(str(len(open_ports)), C.GREEN)} 个开放端口 "
          f"/ {total} 个已扫描 ({elapsed:.1f}s)")


def output_json(host, results, elapsed, total):
    """JSON 输出"""
    open_ports = results if isinstance(results, list) else results
    output = {
        "host": host,
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scanned": total,
        "open_count": len(open_ports),
        "elapsed_s": round(elapsed, 2),
        "open_ports": [
            {"port": p, "service": s if s else None} for p, s in open_ports
        ]
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def output_csv(host, results, elapsed, total):
    """CSV 输出"""
    open_ports = results if isinstance(results, list) else results
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["port", "status", "service"])
    for port, service in open_ports:
        writer.writerow([port, "OPEN", service])
    print(output.getvalue(), end="")


# ============================================================
# 演示模式
# ============================================================
def demo_mode():
    """演示所有功能"""
    print(colored("=" * 60, C.BOLD))
    print(colored("  🔍 Port Scanner — 演示模式", C.CYAN))
    print(colored("=" * 60, C.BOLD))

    # 1. 基本用法演示
    print(f"\n{colored('━━━ 演示 1: 扫描本地常见端口 ━━━', C.YELLOW)}")
    common = [22, 80, 135, 443, 445, 3306, 3389, 5432, 6379, 8080, 27017]
    results, elapsed, total = scan_ports("127.0.0.1", common, threads=5, timeout=0.3, verbose=True)
    output_text("127.0.0.1", results, elapsed, total)

    # 2. JSON 输出演示
    print(f"\n{colored('━━━ 演示 2: JSON 格式输出 ━━━', C.YELLOW)}")
    open_ports, elapsed, total = scan_ports("127.0.0.1", common[:5], threads=5, timeout=0.3)
    output_json("127.0.0.1", open_ports, elapsed, total)

    # 3. CSV 输出演示
    print(f"\n{colored('━━━ 演示 3: CSV 格式输出 ━━━', C.YELLOW)}")
    output_csv("127.0.0.1", open_ports, elapsed, total)

    # 4. 端口解析演示
    print(f"\n{colored('━━━ 演示 4: 端口规格解析 ━━━', C.YELLOW)}")
    specs = ["80", "1-10", "22,80,443", "80,22,1-5,443"]
    for spec in specs:
        ports = parse_ports(spec)
        print(f"  '{spec}' → {ports}")

    # 5. 服务识别演示
    print(f"\n{colored('━━━ 演示 5: 知名端口服务识别 ━━━', C.YELLOW)}")
    test_ports = [22, 25, 53, 80, 443, 3306, 5432, 6379, 8080, 27017]
    print(f"  {'端口':<8} {'服务':<20} {'说明'}")
    print(f"  {'-'*45}")
    for p in test_ports:
        svc = get_service_name(p)
        desc = {
            22: "安全 Shell",
            25: "邮件发送",
            53: "域名解析",
            80: "网页服务",
            443: "加密网页",
            3306: "数据库",
            5432: "数据库",
            6379: "缓存",
            8080: "开发/代理",
            27017: "文档数据库",
        }.get(p, "")
        print(f"  {str(p):<8} {svc:<20} {desc}")

    print(f"\n{colored('━' * 60, C.MUTED)}")
    print(colored("  演示完成！查看代码了解实现细节 🔍", C.GREEN))
    print(f"  python port_scanner.py -h           # 查看帮助")
    print(f"  python port_scanner.py localhost    # 扫描本机常见端口")
    print(f"  python port_scanner.py 192.168.1.1 1-100 -t 100  # 快速扫描")
    print(colored('━' * 60, C.MUTED))


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="🔍 多线程端口扫描器 (Python Socket 实战)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python port_scanner.py 192.168.1.1                    # 扫描常见端口
  python port_scanner.py 192.168.1.1 1-1024             # 扫描 1-1024
  python port_scanner.py scanme.nmap.org 1-100 -t 50    # 50线程扫描
  python port_scanner.py 192.168.1.1 22,80,443 -f json  # JSON输出
  python port_scanner.py --demo                         # 演示模式
        """
    )
    parser.add_argument("host", nargs="?", default=None,
                        help="目标主机 (IP 或域名)")
    parser.add_argument("ports", nargs="?", default=None,
                        help="端口规格 (e.g. 80, 1-1024, 22,80,443)")
    parser.add_argument("-t", "--threads", type=int, default=50,
                        help="并发线程数 (默认 50)")
    parser.add_argument("-T", "--timeout", type=float, default=1.0,
                        help="连接超时/秒 (默认 1.0)")
    parser.add_argument("-f", "--format", choices=["text", "json", "csv"],
                        default="text", help="输出格式 (默认 text)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="静默模式（只输出开放端口）")
    parser.add_argument("--demo", action="store_true",
                        help="演示模式：展示所有功能")

    args = parser.parse_args()

    # 演示模式
    if args.demo:
        demo_mode()
        return

    # 参数校验
    if not args.host:
        parser.print_help()
        print(f"\n{colored('[!]', C.RED)} 请指定目标主机，或使用 --demo 查看演示")
        sys.exit(1)

    # 端口默认值：常见端口
    ports_spec = args.ports if args.ports else (
        "21,22,23,25,53,80,110,135,139,143,443,445,993,995,"
        "1433,1521,1723,3306,3389,5432,5900,6379,8080,8443,"
        "27017,27018"
    )

    try:
        ports = parse_ports(ports_spec)
        if not ports:
            print(f"{colored('[!]', C.RED)} 无效的端口规格: {ports_spec}")
            sys.exit(1)
    except ValueError as e:
        print(f"{colored('[!]', C.RED)} 端口解析错误: {e}")
        sys.exit(1)

    # 执行扫描
    try:
        open_ports, elapsed, total = scan_ports(
            args.host, ports,
            threads=args.threads,
            timeout=args.timeout,
            verbose=not args.quiet
        )
    except ValueError as e:
        print(f"{colored('[!]', C.RED)} {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{colored('[!]', C.YELLOW)} 扫描已取消")
        sys.exit(0)

    # 输出结果
    if args.format == "json":
        output_json(args.host, open_ports, elapsed, total)
    elif args.format == "csv":
        output_csv(args.host, open_ports, elapsed, total)
    else:
        output_text(args.host, open_ports, elapsed, total)

    # 返回码：有开放端口返回 0，否则返回 1（方便脚本判断）
    return 0 if open_ports else 1


if __name__ == "__main__":
    sys.exit(main() or 0)
