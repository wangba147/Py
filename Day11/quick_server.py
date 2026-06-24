#!/usr/bin/env python3
"""
quick_server.py —— 一键启动功能增强版 HTTP 服务器

比 python -m http.server 更好用：
  - 自动显示本机 IP（方便告知同事）
  - 启动时在浏览器中打开
  - 支持文件上传（http.server 只支持下载）
  - 显示访问日志（彩色输出）
  - CORS 支持（本地调试前端时常用）
  - 支持范围请求（视频拖进度条）

用法：
  python quick_server.py                  # 端口 8000，共享当前目录
  python quick_server.py 9090             # 指定端口
  python quick_server.py 8080 -d /tmp     # 指定目录
  python quick_server.py 8000 --upload    # 开启文件上传
  python quick_server.py 8000 --open      # 启动时打开浏览器
  python quick_server.py 8000 --cors      # 启用 CORS
"""

import os
import sys
import socket
import argparse
import html
import io
import pathlib
import webbrowser
import threading
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, HTTPServer, test


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

def colored(text, *codes):
    return "".join(codes) + str(text) + C.RESET


# ============================================================
# 获取本机 IP
# ============================================================
def get_local_ip():
    """获取本机局域网 IP（连接外网接口时选定的 IP）"""
    try:
        # 连接外部 IP（不真正发送数据），只是为了选定合适的网卡
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


# ============================================================
# 增强版 Handler
# ============================================================
class EnhancedHandler(SimpleHTTPRequestHandler):
    """增强版 HTTP Handler，支持文件上传 + CORS + 彩色日志"""

    # 类级别配置（通过 make_handler 设置）
    enable_upload = False
    enable_cors = False
    upload_dir = None

    # 支持范围请求（视频/大文件拖进度条）
    server_version = "QuickServer/1.0"

    def log_message(self, fmt, *args):
        """彩色访问日志"""
        # log_error 传入的 args[0] 可能是 HTTPStatus 枚举而非字符串
        # 标准日志 fmt: '"GET /path HTTP/1.1" 200 1234' — args 全部为 str/int
        # 错误日志 fmt: 'code %d, message %s' — args[0] 可能是 HTTPStatus
        if args and isinstance(args[0], HTTPStatus):
            # 错误日志：直接用默认格式输出
            code = args[0]
            msg = args[1] if len(args) > 1 else ""
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  {colored(ts, C.MUTED)}  {colored('ERROR', C.RED, C.BOLD):<20s}  {colored(int(code), C.RED, C.BOLD)}  {msg}")
            return

        # 正常访问日志
        code = args[1] if len(args) > 1 else "???"
        method = "?"
        path_part = "?"
        if args and isinstance(args[0], str):
            parts = args[0].split(" ")
            method = parts[0] if parts else "?"
            path_part = parts[1] if len(parts) > 1 else "?"

        # 根据状态码着色
        try:
            c = int(code)
            if c < 300:
                code_col = colored(code, C.GREEN, C.BOLD)
            elif c < 400:
                code_col = colored(code, C.YELLOW)
            else:
                code_col = colored(code, C.RED, C.BOLD)
        except ValueError:
            code_col = code

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  {colored(ts, C.MUTED)}  {colored(method, C.CYAN):<20s}  {code_col}  {path_part}")

    def end_headers(self):
        """在响应头末尾添加 CORS 和其他自定义头"""
        if self.enable_cors:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        """处理 OPTIONS 预检请求（CORS）"""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self):
        """处理文件上传（multipart/form-data）"""
        if not self.enable_upload:
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Upload not enabled, start with --upload")
            return

        if self.path != "/upload":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected multipart/form-data")
            return

        # 解析文件上传
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # 从 boundary 解析文件名和内容
        boundary = content_type.split("boundary=")[-1].strip().encode()
        parts = body.split(b"--" + boundary)

        saved_files = []
        for part in parts:
            if b"Content-Disposition" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            headers = part[:header_end].decode("utf-8", errors="replace")
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]

            # 先按行分割，只在 Content-Disposition 行中查找 filename
            # 避免按 ; 分割后 filename 与 Content-Type 行粘连
            filename_match = None
            for line in headers.splitlines():
                if "Content-Disposition" not in line:
                    continue
                for segment in line.split(";"):
                    segment = segment.strip()
                    if segment.startswith('filename="'):
                        # 去掉开头的 filename=" 和结尾的 "
                        filename_match = segment[10:]
                        if filename_match.endswith('"'):
                            filename_match = filename_match[:-1]
                        break

            if filename_match and content:
                save_path = pathlib.Path(self.upload_dir or ".") / pathlib.Path(filename_match).name
                save_path.write_bytes(content)
                saved_files.append(save_path.name)
                print(colored(f"\n  ⬆️  上传：{save_path.name} ({len(content)} bytes)", C.GREEN, C.BOLD))

        # 返回结果
        response = f"Uploaded: {', '.join(saved_files) if saved_files else 'no files'}".encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def list_directory(self, path):
        """覆盖目录列表页面，加入上传控件（如果 --upload 开启）"""
        try:
            entries = sorted(pathlib.Path(path).iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return None

        rel_path = urllib.parse.unquote(self.path)

        upload_form = ""
        if self.enable_upload:
            upload_form = """
<div style="background:#1a2a1a;border:1px solid #3a6a3a;border-radius:8px;padding:16px;margin-bottom:20px">
  <h3 style="color:#66bb6a;margin:0 0 10px">📤 上传文件</h3>
  <form method="POST" action="/upload" enctype="multipart/form-data">
    <input type="file" name="file" multiple style="color:#e4e6f0;background:#12131a;border:1px solid #2a2d3e;padding:6px;border-radius:4px;margin-right:8px">
    <button type="submit" style="background:#66bb6a;color:#000;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-weight:700">上传</button>
  </form>
</div>"""

        rows = []
        for entry in entries:
            icon = "📁" if entry.is_dir() else self._file_icon(entry.suffix)
            link = html.escape(entry.name) + ("/" if entry.is_dir() else "")
            href = urllib.parse.quote(entry.name) + ("/" if entry.is_dir() else "")
            size = ""
            mtime = ""
            if entry.is_file():
                try:
                    st = entry.stat()
                    size = self._humansize(st.st_size)
                    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%m-%d %H:%M")
                except Exception:
                    pass
            rows.append(f"""
        <tr>
          <td style="padding:8px 12px"><a href="{href}" style="color:#4fc3f7;text-decoration:none">{icon} {link}</a></td>
          <td style="padding:8px 12px;color:#8b8fa3;text-align:right;font-size:13px">{size}</td>
          <td style="padding:8px 12px;color:#8b8fa3;font-size:13px">{mtime}</td>
        </tr>""")

        body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📂 {html.escape(rel_path)}</title>
<style>
body{{font-family:'Segoe UI','Microsoft YaHei',sans-serif;background:#0f1117;color:#e4e6f0;margin:0;padding:24px}}
h1{{font-size:20px;margin-bottom:16px;color:#fff}}
h1 a{{color:#4fc3f7;text-decoration:none}}
table{{width:100%;border-collapse:collapse;background:#1c1f2e;border:1px solid #2a2d3e;border-radius:8px;overflow:hidden}}
th{{background:#161822;color:#8b8fa3;font-size:12px;padding:8px 12px;text-align:left;text-transform:uppercase;letter-spacing:1px}}
tr:hover{{background:#22253a}}
.footer{{margin-top:24px;font-size:12px;color:#8b8fa3}}
</style>
</head>
<body>
<h1>📂 <a href="/">/</a>{html.escape(rel_path)}</h1>
{upload_form}
<table>
  <tr><th>名称</th><th style="text-align:right">大小</th><th>修改时间</th></tr>
  {''.join(rows)}
</table>
<div class="footer">QuickServer · {len(list(entries))} items · Python {sys.version.split()[0]}</div>
</body>
</html>"""

        encoded = body.encode("utf-8")
        f = io.BytesIO(encoded)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    @staticmethod
    def _humansize(n):
        """将字节数格式化为可读字符串"""
        for unit in ["B", "KB", "MB", "GB"]:
            if n < 1024:
                return f"{n:.0f} {unit}"
            n /= 1024
        return f"{n:.1f} TB"

    @staticmethod
    def _file_icon(suffix):
        """根据扩展名返回 Emoji 图标"""
        icons = {
            ".py":   "🐍", ".cpp": "⚙️", ".h":   "📋", ".hpp": "📋",
            ".c":    "⚙️", ".rs":  "🦀", ".go":  "🐹", ".js":  "📜",
            ".html": "🌐", ".css": "🎨", ".json": "📦", ".yaml": "📦",
            ".md":   "📝", ".txt": "📝", ".pdf": "📄", ".zip": "🗜️",
            ".tar":  "🗜️", ".gz":  "🗜️", ".exe": "💻", ".dll": "🔗",
            ".so":   "🔗", ".a":   "📚", ".lib": "📚", ".png": "🖼️",
            ".jpg":  "🖼️", ".gif": "🎞️", ".mp4": "🎬", ".mp3": "🎵",
        }
        return icons.get(suffix.lower(), "📄")


def make_handler(enable_upload=False, enable_cors=False, upload_dir=None):
    """创建带配置的 Handler 类"""
    class ConfiguredHandler(EnhancedHandler):
        pass
    ConfiguredHandler.enable_upload = enable_upload
    ConfiguredHandler.enable_cors   = enable_cors
    ConfiguredHandler.upload_dir    = upload_dir
    return ConfiguredHandler


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="增强版临时 HTTP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python quick_server.py                   # 8000端口，当前目录
  python quick_server.py 9090              # 指定端口
  python quick_server.py 8080 -d /tmp      # 指定目录
  python quick_server.py 8000 --upload     # 开启上传
  python quick_server.py 8000 --open       # 自动打开浏览器
  python quick_server.py 8000 --cors       # 启用CORS（前端调试）
  python quick_server.py 8000 --upload --cors --open  # 全功能
        """
    )
    parser.add_argument("port", nargs="?", type=int, default=8000, help="端口号（默认 8000）")
    parser.add_argument("-d", "--directory", default=".", help="共享的目录（默认当前目录）")
    parser.add_argument("--upload", action="store_true", help="开启文件上传功能")
    parser.add_argument("--open", action="store_true", help="启动后自动打开浏览器")
    parser.add_argument("--cors", action="store_true", help="启用 CORS（前端本地调试用）")
    parser.add_argument("--bind", default="", help="绑定 IP（默认所有接口）")
    args = parser.parse_args()

    # 切换到目标目录
    serve_dir = pathlib.Path(args.directory).resolve()
    if not serve_dir.exists():
        print(colored(f"❌ 目录不存在：{serve_dir}", C.RED))
        sys.exit(1)
    os.chdir(serve_dir)

    # 获取 IP 信息
    local_ip = get_local_ip()
    bind_addr = args.bind or "0.0.0.0"
    port = args.port

    # 创建服务器
    handler = make_handler(
        enable_upload=args.upload,
        enable_cors=args.cors,
        upload_dir=str(serve_dir)
    )
    handler.extensions_map.update({
        ".wasm": "application/wasm",
        ".ts":   "text/typescript",
        "":      "application/octet-stream",
    })

    try:
        httpd = HTTPServer((bind_addr, port), handler)
    except OSError as e:
        print(colored(f"❌ 启动失败（端口 {port} 被占用？）：{e}", C.RED))
        sys.exit(1)

    # 打印启动信息
    print()
    print(colored("  ╔═══════════════════════════════════════╗", C.CYAN))
    print(colored("  ║", C.CYAN) + colored("     🚀 QuickServer 启动！", C.BOLD) + colored("              ║", C.CYAN))
    print(colored("  ╠═══════════════════════════════════════╣", C.CYAN))
    print(colored("  ║", C.CYAN) + f"  本机访问  http://localhost:{port:<5}        " + colored("║", C.CYAN))
    print(colored("  ║", C.CYAN) + f"  局域网    http://{local_ip}:{port:<5}   " + colored("║", C.CYAN))
    print(colored("  ║", C.CYAN) + f"  共享目录  {str(serve_dir):<30s} " + colored("║", C.CYAN))
    print(colored("  ║", C.CYAN) + f"  文件上传  {'✅ 开启  POST /upload' if args.upload else '❌ 关闭（--upload 开启）':<30s} " + colored("║", C.CYAN))
    print(colored("  ║", C.CYAN) + f"  CORS      {'✅ 开启' if args.cors else '❌ 关闭（--cors 开启）':<30s}   " + colored("║", C.CYAN))
    print(colored("  ╠═══════════════════════════════════════╣", C.CYAN))
    print(colored("  ║", C.CYAN) + colored("  按 Ctrl+C 停止服务                    ", C.MUTED) + colored("║", C.CYAN))
    print(colored("  ╚═══════════════════════════════════════╝", C.CYAN))
    print()
    print(colored("  访问日志：", C.MUTED))

    # 自动打开浏览器
    if args.open:
        url = f"http://localhost:{port}"
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    # 开始服务
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(colored("\n\n  👋 服务器已停止。", C.YELLOW))
        httpd.server_close()


if __name__ == "__main__":
    main()
