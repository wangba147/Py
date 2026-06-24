#!/usr/bin/env python3
"""
Day 11: Python 一行命令与内置服务 —— python -m xxx
从今天开始，每天介绍一些日常实用的 Python 技巧
面向 C++ 开发者，让 Python 成为你随手可用的瑞士军刀
"""

import os
import sys
import json
import re
import subprocess
import pathlib
import textwrap
import base64
import hashlib
import calendar
import argparse
import time
import socket
import struct
import csv
import io
import zipfile
import tempfile
from datetime import datetime


# ============================================================
# 1. python -m http.server —— 临时 HTTP 服务器
# ============================================================
# C++ 对比：C++ 搭建 HTTP 服务需要 Boost.Beast / cpp-httplib 等库
# Python 一行命令即可，适合临时文件传输、本地调试

def demo_http_server():
    """演示：http.server 的用法"""
    print("\n=== 1. python -m http.server ===")

    # 最简用法 —— 一行命令启动
    print("基本用法（命令行直接执行）：")
    print("  python -m http.server              # 默认端口 8000，共享当前目录")
    print("  python -m http.server 8080          # 指定端口 8080")
    print("  python -m http.server 3000 -d /tmp  # 指定目录和端口")
    print("  python -m http.server --bind 127.0.0.1  # 只允许本机访问")

    # Python 3.7+ 支持 -d 指定目录
    # Python 3.8+ 支持 --bind 指定绑定地址
    # Python 3.9+ 支持 --directory 和 --cgi

    print("\n实战场景：")
    print("  1. 同局域网传文件：手机/同事浏览器访问 http://你的IP:8000")
    print("  2. 本地调试 HTML：打开 http://localhost:8000/index.html")
    print("  3. 分享 C++ 头文件：同事远程下载 include/ 目录")
    print("  4. CI 环境中临时提供制品下载")

    # 用 Python 代码演示（非命令行模式）
    print("\nPython 代码中使用：")
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    print("  from http.server import HTTPServer, SimpleHTTPRequestHandler")
    print("  server = HTTPServer(('localhost', 8000), SimpleHTTPRequestHandler)")
    print("  server.serve_forever()  # 或者 server.handle_request() 处理一个请求")

    # 获取本机 IP —— 方便告知同事
    # C++ 方式：getaddrinfo 系统调用；Python：socket.gethostbyname
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"\n本机 IP：{local_ip}")
        print(f"同事可访问：http://{local_ip}:8000")
    except Exception:
        print("  (无法获取本机 IP)")


# ============================================================
# 2. python -m json.tool —— JSON 格式化与校验
# ============================================================
# C++ 对比：C++ 处理 JSON 需要 nlohmann/json 等第三方库
# Python 一行命令格式化+校验，开发调试必备

def demo_json_tool():
    """演示：json.tool 的用法"""
    print("\n=== 2. python -m json.tool ===")

    # 基本用法
    print("基本用法（命令行）：")
    print("  python -m json.tool file.json          # 格式化输出")
    print("  python -m json.tool file.json out.json # 格式化并保存")
    print("  echo '{\"a\":1}' | python -m json.tool   # 管道输入")
    print("  python -m json.tool --compact file.json # 紧凑输出(Python 3.9+)")

    # 实战演示：格式化 JSON
    ugly_json = '{"name":"test","version":"1.0","deps":["numpy","requests"],"config":{"debug":true,"port":8080}}'

    print("\n原始 JSON：")
    print(f"  {ugly_json}")

    # python -m json.tool 的本质就是 json.dumps(data, indent=4)
    data = json.loads(ugly_json)
    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    print("\n格式化后：")
    for line in pretty.split('\n'):
        print(f"  {line}")

    # JSON 校验 —— 无效 JSON 会报错
    print("\nJSON 校验（检测无效 JSON）：")
    try:
        json.loads("{bad json}")  # 会抛异常
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 无效：{e}")

    print("  python -m json.tool 本质：校验+格式化，一行搞定")
    print("  C++ 开发场景：检查 CMake 的 JSON 配置、REST API 返回值")


# ============================================================
# 3. python -m zipfile —— 无需安装的压缩工具
# ============================================================
# C++ 对比：C++ 压缩需要 zlib + 手写代码；Python 标准库一步到位

def demo_zipfile():
    """演示：zipfile 模块"""
    print("\n=== 3. python -m zipfile ===")

    # 命令行用法
    print("命令行用法：")
    print("  python -m zipfile -l archive.zip       # 列出内容")
    print("  python -m zipfile -e archive.zip dir/   # 解压到目录")
    print("  python -m zipfile -c archive.zip file1 file2  # 创建压缩包")

    # Python 代码演示
    tmp_dir = pathlib.Path(tempfile.mkdtemp())
    zip_path = tmp_dir / "demo.zip"

    # 创建压缩包
    print("\n创建压缩包：")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 写入字符串内容（无需先创建文件）
        zf.writestr("header.h", "// Auto-generated header\n#pragma once\n")
        zf.writestr("config.json", json.dumps({"port": 8080, "debug": True}, indent=2))
        zf.writestr("readme.txt", "Demo project\n")
        print(f"  已创建 {zip_path}")

    # 列出内容
    print("\n列出压缩包内容：")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            print(f"  {info.filename} ({info.compress_size}/{info.file_size} bytes, compressed {100*(1-info.compress_size/info.file_size):.0f}%)")

    # 解压
    extract_dir = tmp_dir / "extracted"
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
        print(f"\n  解压到 {extract_dir}")
        for f in extract_dir.rglob("*"):
            if f.is_file():
                print(f"    {f.name}: {f.read_text(encoding='utf-8')[:50]}")

    shutil_clean = False  # 不用 shutil，直接用 zipfile 自身

    # 清理
    import shutil
    shutil.rmtree(tmp_dir)


# ============================================================
# 4. python -m base64 —— 编码解码
# ============================================================
# C++ 对比：C++ 需要 base64 库或手写编解码；Python 标准库一行

def demo_base64():
    """演示：base64 模块"""
    print("\n=== 4. python -m base64 ===")

    # 命令行用法
    print("命令行用法：")
    print("  echo 'Hello World' | python -m base64         # 编码")
    print("  echo 'SGVsbG8gV29ybGQ=' | python -m base64 -d  # 解码")
    print("  python -m base64 -e file.bin                   # 编码文件")

    # Python 代码演示
    original = "C++ 开发者用 Python 辅助"
    encoded = base64.b64encode(original.encode('utf-8')).decode('ascii')
    decoded = base64.b64decode(encoded).decode('utf-8')

    print(f"\n编码演示：")
    print(f"  原文：{original}")
    print(f"  Base64：{encoded}")
    print(f"  解码：{decoded}")

    # URL-safe Base64（不含 +/ 字符）
    url_encoded = base64.urlsafe_b64encode(original.encode('utf-8')).decode('ascii')
    print(f"  URL-safe：{url_encoded}")

    # 实战场景
    print("\n实战场景：")
    print("  1. REST API 认证头：Authorization: Basic <base64(user:pass)>")
    print("  2. 内嵌小图片到 HTML/CSS：data:image/png;base64,...")
    print("  3. 配置文件中存二进制密钥")
    print("  4. C++ 项目中快速验证 base64 编解码逻辑")


# ============================================================
# 5. python -m hashlib —— 文件哈希校验
# ============================================================
# C++ 对比：C++ 需要引入 OpenSSL 或手写 SHA256；Python 标准库一步

def demo_hashlib():
    """演示：hashlib 模块"""
    print("\n=== 5. python -m hashlib ===")

    # 注意：python -m hashlib 是 Python 3.9+ 才有的 CLI
    # 早期版本只能用 Python 代码

    print("Python 3.9+ 命令行：")
    print("  python -m hashlib file.bin           # 默认 SHA256")
    print("  python -m hashlib -a md5 file.bin    # 指定算法")
    print("  python -m hashlib -a sha1 file.bin   # SHA1")

    # Python 代码演示（所有版本可用）
    text = "Hello, C++ developers!"

    print("\nPython 代码计算哈希：")
    for algo in ['md5', 'sha1', 'sha256', 'sha512']:
        h = hashlib.new(algo, text.encode('utf-8'))
        print(f"  {algo:8s}: {h.hexdigest()}")

    # 文件哈希 —— 校验下载文件完整性
    tmp_dir = pathlib.Path(tempfile.mkdtemp())
    test_file = tmp_dir / "demo.bin"
    test_file.write_bytes(b"C++ binary file content for integrity check")

    file_hash = hashlib.sha256(test_file.read_bytes()).hexdigest()
    print(f"\n文件哈希校验：")
    print(f"  文件：{test_file.name}")
    print(f"  SHA256：{file_hash}")
    print("  用途：校验 C++ SDK/lib 下载完整性，对比官网公布的 hash")

    import shutil
    shutil.rmtree(tmp_dir)


# ============================================================
# 6. python -m calendar —— 日历查看
# ============================================================
# C++ 对比：C++ 没有日历标准库；Python calendar 模块一步输出

def demo_calendar():
    """演示：calendar 模块"""
    print("\n=== 6. python -m calendar ===")

    # 命令行用法
    print("命令行用法：")
    print("  python -m calendar                    # 打印当年日历")
    print("  python -m calendar 2026               # 指定年份")
    print("  python -m calendar 6 2026             # 指定月份")

    # Python 代码演示
    year = 2026
    month = 7  # 七月

    print(f"\n{year}年{month}月日历：")
    cal = calendar.month(year, month)
    print(cal)

    # 判断工作日 —— C++ 没有这个功能
    # calendar.weekday(year, month, day) → 0=Mon, 6=Sun
    weekday = calendar.weekday(year, month, 1)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print(f"  2026年7月1日 是 {day_names[weekday]}")

    # 实用：判断某月有多少天
    days = calendar.monthrange(year, month)[1]
    print(f"  2026年7月有 {days} 天")

    # 判断闰年
    print(f"  2026 是闰年？{calendar.isleap(year)}")
    print(f"  2024 是闰年？{calendar.isleap(2024)}")


# ============================================================
# 7. python -c 一行代码技巧
# ============================================================
# C++ 对比：C++ 无法一行执行代码；Python -c 是瑞士军刀

def demo_one_liners():
    """演示：python -c 一行代码技巧"""
    print("\n=== 7. python -c 一行代码技巧 ===")

    one_liners = [
        ("快速计算", "python -c \"print(2**10)\"", "1024"),
        ("排序文件行", "python -c \"import sys; print(*sorted(sys.stdin), sep='')\"", "管道输入排序"),
        ("时间戳", "python -c \"import time; print(time.time())\"", "当前 Unix 时间戳"),
        ("十六进制转换", "python -c \"print(hex(255))\"", "0xff"),
        ("反转字符串", "python -c \"print('hello'[::-1])\"", "olleh"),
        ("斐波那契", "python -c \"a,b=0,1; [print(b) for _ in range(10) if not (a,b:=b,a+b)]\"", "前10项"),
        ("文件大小", "python -c \"import os; print(os.path.getsize('file.txt'))\"", "文件字节大小"),
        ("当前目录", "python -c \"import os; print(os.getcwd())\"", "工作目录路径"),
        ("环境变量", "python -c \"import os; print(os.environ['PATH'])\"", "PATH 变量"),
        ("PING端口", "python -c \"import socket; s=socket.socket(); result=s.connect_ex(('localhost',8080)); print('open' if result==0 else 'closed')\"", "端口检测"),
    ]

    print("实用一行代码：")
    for desc, cmd, output in one_liners:
        print(f"\n  {desc}：")
        print(f"    {cmd}")
        print(f"    → {output}")

    # 端口检测演示
    print("\n端口检测实战：")
    for port in [80, 443, 8080, 3306, 8000]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            result = s.connect_ex(('localhost', port))
            status = "开放" if result == 0 else "关闭/不可达"
            print(f"  localhost:{port} → {status}")
            s.close()
        except Exception as e:
            print(f"  localhost:{port} → 检测失败: {e}")


# ============================================================
# 8. python -m csv —— CSV 查看与处理
# ============================================================
# C++ 对比：C++ CSV 处理需要 RapidCSV 等库；Python 标准库内置

def demo_csv_tool():
    """演示：csv 模块"""
    print("\n=== 8. python -m csv / csv 模块 ===")

    # 命令行无直接 -m csv，但 Python 代码极为简洁
    print("Python 代码处理 CSV（比命令行更实用）：")

    # 创建示例 CSV
    csv_data = [
        ["module", "source", "version"],
        ["core", "github.com/user/core", "1.2.0"],
        ["utils", "github.com/user/utils", "0.8.3"],
        ["network", "github.com/user/network", "2.1.0"],
    ]

    # 写入 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    for row in csv_data:
        writer.writerow(row)
    csv_text = output.getvalue()

    print("CSV 内容：")
    print(csv_text)

    # 读取 CSV
    reader = csv.DictReader(io.StringIO(csv_text))
    print("\nDictReader 逐行读取：")
    for row in reader:
        print(f"  {row['module']} v{row['version']} from {row['source']}")

    # 实战：从 C++ 项目依赖清单中提取信息
    print("\n实战场景：")
    print("  1. 解析 C++ 第三方依赖版本清单")
    print("  2. 从 CI 日志 CSV 中统计构建时长")
    print("  3. 批量处理 Excel 导出的 CSV 数据")


# ============================================================
# 9. python -m struct —— 二进制数据解析
# ============================================================
# C++ 对比：C++ 直接 cast 指针；Python 用 struct.unpack 安全解析

def demo_struct():
    """演示：struct 模块（解析二进制数据）"""
    print("\n=== 9. struct 模块 —— 二进制数据解析 ===")

    # C++ 开发中经常需要解析二进制文件头、网络协议包
    print("C++ 开发场景：解析二进制协议/文件头")

    # 示例：模拟一个简单的二进制文件头
    # 格式：magic(4B) + version(2B) + flags(1B) + size(4B)
    header_format = '>4sHBI'  # big-endian: 4str, uint16, uint8, uint32
    header_data = struct.pack(header_format, b'CPPM', 1, 0, 1024)

    print(f"  二进制头部：{header_data}")
    print(f"  十六进制：{header_data.hex()}")

    # 解析 —— C++ 用 reinterpret_cast<char*>(&header)；Python 用 struct.unpack
    unpacked = struct.unpack(header_format, header_data)
    print(f"  解析结果：magic={unpacked[0]}, version={unpacked[1]}, flags={unpacked[2]}, size={unpacked[3]}")

    # 常用格式字符
    print("\nstruct 格式字符速查：")
    for char, desc, size in [
        ('b', 'int8 (signed)', 1), ('B', 'uint8', 1),
        ('h', 'int16 (signed)', 2), ('H', 'uint16', 2),
        ('i', 'int32 (signed)', 4), ('I', 'uint32', 4),
        ('q', 'int64 (signed)', 8), ('Q', 'uint64', 8),
        ('f', 'float32', 4), ('d', 'float64', 8),
        ('s', 'char[] (bytes)', '?'), ('x', 'pad byte', 1),
    ]:
        print(f"  {char:2s} → {desc:20s} ({size} bytes)")

    # 字节序前缀
    print("\n字节序前缀：")
    print("  > → big-endian (网络协议标准)")
    print("  < → little-endian (x86/ARM)")
    print("  @ → native (本机默认)")
    print("  ! → network (= big-endian)")


# ============================================================
# 10. python -m pip / python -m sys —— 环境信息速查
# ============================================================

def demo_env_info():
    """演示：快速查看 Python 环境信息"""
    print("\n=== 10. 环境信息速查 ===")

    # python -m pip
    print("pip 用法：")
    print("  python -m pip install package       # 安装包")
    print("  python -m pip list                   # 已安装列表")
    print("  python -m pip show package           # 包详情")
    print("  python -m pip freeze > requirements.txt  # 导出依赖")

    # sys / platform 信息
    print("\nPython 环境信息（python -c 方式）：")
    info_items = [
        ("Python版本", sys.version),
        ("平台", sys.platform),
        ("字节序", sys.byteorder),
        ("最大整数", str(sys.maxsize)),
        ("路径分隔符", os.sep),
        ("默认编码", sys.getdefaultencoding()),
        ("文件系统编码", sys.getfilesystemencoding()),
    ]
    for label, value in info_items:
        print(f"  {label:15s}: {value}")

    # C++ 开发者关心的大小端
    print(f"\n当前系统是 {sys.byteorder}-endian")
    print("  → C++ 网络编程中字节序转换 ntohs/htonl 对应 Python struct > 格式")


# ============================================================
# 11. 综合速查表
# ============================================================

def demo_cheatsheet():
    """打印 python -m 命令速查表"""
    print("\n=== 11. python -m 命令速查表 ===")

    commands = [
        ("http.server", "8000", "临时 HTTP 服务器（文件传输/调试）", "⭐⭐⭐⭐⭐"),
        ("json.tool", "file.json", "JSON 格式化与校验", "⭐⭐⭐⭐⭐"),
        ("zipfile", "-c/l/e", "压缩/解压/查看 ZIP", "⭐⭐⭐⭐"),
        ("base64", "-e/-d", "Base64 编码/解码", "⭐⭐⭐⭐"),
        ("hashlib", "file", "文件哈希校验（MD5/SHA256）", "⭐⭐⭐⭐"),
        ("calendar", "year/month", "日历查看", "⭐⭐⭐"),
        ("csv", "(代码)", "CSV 读写处理", "⭐⭐⭐⭐"),
        ("struct", "(代码)", "二进制数据解析", "⭐⭐⭐⭐"),
        ("pip", "install/list", "包管理", "⭐⭐⭐⭐⭐"),
        ("sys", "(代码)", "系统/环境信息", "⭐⭐⭐"),
        ("textwrap", "(代码)", "文本格式化/缩进", "⭐⭐⭐"),
        ("argparse", "(代码)", "命令行参数解析", "⭐⭐⭐⭐⭐"),
        ("trace", "script.py", "代码执行追踪/覆盖率", "⭐⭐⭐"),
        ("pdb", "script.py", "交互式调试器", "⭐⭐⭐⭐"),
        ("profile", "script.py", "性能分析", "⭐⭐⭐⭐"),
        ("timeit", "-s 'setup' 'stmt'", "微基准计时", "⭐⭐⭐⭐"),
        ("random", "(代码)", "随机数生成", "⭐⭐⭐"),
        ("uuid", "(代码)", "UUID 生成", "⭐⭐⭐"),
        ("this", "", "Python 之禅 😄", "⭐"),
        ("antigravity", "", "🛸 反重力（彩蛋）", "⭐"),
    ]

    print(f"{'命令':20s} {'参数':15s} {'用途':30s} {'实用度':12s}")
    print("-" * 77)
    for cmd, args, desc, stars in commands:
        print(f"  python -m {cmd:17s} {args:15s} {desc:30s} {stars}")

    print("\n💡 提示：python -c 和 python -m 是日常最常用的两种快捷方式")
    print("   -m 运行模块入口，-c 执行一行代码")
    print("   不需要写 .py 文件，随手即用")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Day 11: Python 一行命令与内置服务")
    parser.add_argument("--demo", choices=["all", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
                        default="all", help="选择演示模块")
    args = parser.parse_args()

    demos = {
        "1":  demo_http_server,
        "2":  demo_json_tool,
        "3":  demo_zipfile,
        "4":  demo_base64,
        "5":  demo_hashlib,
        "6":  demo_calendar,
        "7":  demo_one_liners,
        "8":  demo_csv_tool,
        "9":  demo_struct,
        "10": demo_env_info,
        "11": demo_cheatsheet,
    }

    print("=" * 60)
    print("Day 11: Python 一行命令与内置服务")
    print("  python -m xxx —— 不写脚本也能干活")
    print("=" * 60)

    if args.demo == "all":
        for key in sorted(demos.keys()):
            demos[key]()
    else:
        demos[args.demo]()

    print("\n" + "=" * 60)
    print("完成！关键要点：")
    print("  • python -m http.server → 临时文件传输")
    print("  • python -m json.tool → JSON 格式化校验")
    print("  • python -c → 一行代码随手用")
    print("  • 更多 python -m 命令见速查表（demo 11）")
    print("=" * 60)


if __name__ == "__main__":
    main()
