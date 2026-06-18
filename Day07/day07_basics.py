"""
Day 07: subprocess 与系统调用 —— 基础练习脚本
================================================
对应 HTML: day07_subprocess.html
目标:
  1. 掌握 os.system / os.popen / subprocess 的区别
  2. subprocess.run 各个参数（capture_output, text, check, timeout）
  3. Popen 的 stdin/stdout/stderr 管道重定向
  4. C++ 程序的编译、运行、日志捕获实战
"""
import os
import sys
import shlex
import subprocess
from pathlib import Path


def section(title):
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


# ============================================================
# 1. 三种"启动外部进程"的方式对比
# ============================================================
section("1. os.system vs os.popen vs subprocess")

# 1.1 os.system: 只是"发出去"，拿不到 stdout
# C++ 对比: system("gcc -v"); ——  在 C 里也只有 int 返回值
ret = os.system("echo hello_from_system")
print(f"os.system 返回值 = {ret}  (Windows 上是 0, Linux 是 shell 退出码的左移 8 位)")

# 1.2 os.popen: 拿到 stdout，但只能读不能交互
# C++ 对比: popen("cmd", "r") + fread —— 思路完全一样
with os.popen("echo hello_from_popen") as fp:
    out = fp.read()
print(f"os.popen 读到: {out!r}")

# 1.3 subprocess.run: 现代推荐写法，可以同时控制输入/输出/返回码
# C++ 对比: 没有直接对应 ——  C++17 的 std::system 只能拿到退出码
#         std::popen 能读 stdout，但 std::cin 重定向很麻烦
r = subprocess.run(["echo", "hello_from_subprocess"], capture_output=True, text=True)
print(f"subprocess.run stdout = {r.stdout!r}")
print(f"subprocess.run returncode = {r.returncode}")


# ============================================================
# 2. subprocess.run 核心参数
# ============================================================
section("2. subprocess.run 核心参数")

# 2.1 shell=True: 让命令字符串走 shell（危险但方便）
# !!! 警告: 拼接用户输入时不要用 shell=True, 会引发命令注入
r = subprocess.run("echo $OS" if sys.platform != "win32" else "echo %OS%",
                   shell=True, capture_output=True, text=True)
print(f"shell=True 拿到环境变量: {r.stdout.strip()!r}")

# 2.2 shell=False (默认): 命令必须传列表 —— 推荐写法, 更安全
r = subprocess.run(["cmd.exe", "/c", "echo", "safe_list_form"],
                   capture_output=True, text=True)
print(f"列表形式: {r.stdout.strip()!r}")

# 2.3 check=True: 退出码非 0 时抛 CalledProcessError
try:
    subprocess.run(["cmd.exe", "/c", "exit", "1"], check=True)
except subprocess.CalledProcessError as e:
    print(f"check=True 抛异常: returncode={e.returncode}")

# 2.4 timeout=秒数: 超时强杀
# 这里故意让一个不存在的命令 "sleep 99" 卡住，再由 timeout 杀掉
try:
    if sys.platform == "win32":
        subprocess.run(["ping", "-n", "99", "127.0.0.1"], timeout=2)
    else:
        subprocess.run(["sleep", "99"], timeout=2)
except subprocess.TimeoutExpired as e:
    print(f"timeout 触发: {type(e).__name__}")


# ============================================================
# 3. 捕获 stdout / stderr 分别处理
# ============================================================
section("3. 分离 stdout 和 stderr")

# C++ 对比:
#   C 里要么 dup2 重定向到文件再回读，要么用 freopen
#   Python 一行参数搞定
r = subprocess.run(
    [sys.executable, "-c",
     "import sys; print('to stdout'); print('to stderr', file=sys.stderr)"],
    capture_output=True, text=True,
)
print(f"stdout = {r.stdout!r}")
print(f"stderr = {r.stderr!r}")


# ============================================================
# 4. Popen 进阶: 实时流式读取
# ============================================================
section("4. Popen 实时流式读取 (像 tail -f)")

# 场景: 编译 C++ 时想"边编边打印"输出
# subprocess.run 只能等进程结束；Popen 能一行行读

# 跨平台 demo: 用 python 模拟一个"慢慢吐数据"的子进程
demo_cmd = [sys.executable, "-c",
            "import sys, time\n"
            "for i in range(3):\n"
            "    print(f'line {i}')\n"
            "    sys.stdout.flush()\n"
            "    time.sleep(0.1)\n"]

proc = subprocess.Popen(demo_cmd, stdout=subprocess.PIPE, text=True)
print("Popen 实时输出:")
for line in proc.stdout:           # 迭代 stdout, 进程结束自动退出循环
    print(f"  >> {line.rstrip()}")
proc.wait()
print(f"  进程退出码 = {proc.returncode}")


# ============================================================
# 5. 实战: 编译并运行一段 C++ 代码
# ============================================================
section("5. 实战: 编译并运行一段 C++ 代码")

CPP_SRC = r"""
#include <iostream>
int main(int argc, char** argv) {
    std::cout << "Hello from C++!" << std::endl;
    for (int i = 0; i < argc; ++i) {
        std::cout << "  argv[" << i << "] = " << argv[i] << std::endl;
    }
    return 0;
}
"""

# 找 g++/cl; 没有就跳过这一段
# C++ 对比: C 里没有 portable 的 "which" ——  Windows 要 SearchPathW, Linux 要 access(..., X_OK)
# Python 直接用 shutil.which, 跨平台一行搞定
import shutil

compiler = None
for cand in (["g++"], ["clang++"]):
    if shutil.which(cand[0]) is not None:
        compiler = cand
        break
if sys.platform == "win32" and compiler is None and shutil.which("cl") is not None:
    compiler = ["cl"]

if compiler is None:
    print("本机没找到 g++/clang++/cl, 跳过 C++ 编译演示")
else:
    src_path = Path("demo.cpp")
    exe_path = Path("demo.exe" if sys.platform == "win32" else "demo")
    src_path.write_text(CPP_SRC, encoding="utf-8")

    print(f"使用编译器: {compiler}")
    compile_cmd = compiler + ["-std=c++17", str(src_path), "-o", str(exe_path)]
    print(f"  编译命令: {' '.join(compile_cmd)}")
    cr = subprocess.run(compile_cmd, capture_output=True, text=True)
    print(f"  编译 returncode = {cr.returncode}")
    if cr.returncode != 0:
        print(f"  编译 stderr = {cr.stderr}")
    else:
        run_cmd = [str(exe_path), "alpha", "beta"]
        rr = subprocess.run(run_cmd, capture_output=True, text=True)
        print(f"  运行输出:\n{rr.stdout}")

    # 清理
    for p in (src_path, exe_path):
        if p.exists():
            p.unlink()


# ============================================================
# 6. 进程间通信: 传 stdin
# ============================================================
section("6. 通过 stdin 给子进程喂数据")

# C++ 对比:
#   C 里要用 pipe() + fork() + dup2() 拼起来 —— Python 几行搞定
r = subprocess.run(
    [sys.executable, "-c",
     "data = input('请输入名字: '); print(f'收到: {data}')"],
    input="Nova\n",
    capture_output=True, text=True,
)
print(r.stdout)
print("---")


# ============================================================
# 7. 跨平台小工具: 列出当前目录的所有 .cpp 文件并尝试编译
# ============================================================
section("7. 跨平台小工具: 批量查找 .cpp 文件")

# C++ 对比:
#   自己用 <filesystem> 遍历 + system() 调用 —— Python 的 pathlib 更直观
workdir = Path(".")
cpp_files = list(workdir.rglob("*.cpp"))
print(f"当前目录下 .cpp 文件数: {len(cpp_files)}")
for f in cpp_files[:5]:
    print(f"  - {f}  ({f.stat().st_size} bytes)")


# ============================================================
# 8. 沙箱演示: 把 C++ 程序的运行结果存到日志文件
# ============================================================
section("8. 把 C++ 程序输出重定向到日志文件")

# 这是 C++ 开发者最常见的"自动化"诉求: 跑测试, 把结果落盘
log_path = Path("build_output.log")
with log_path.open("w", encoding="utf-8") as logf:
    # 用 python -u (unbuffered) 模拟一个"会产生输出"的子进程
    demo = [sys.executable, "-u", "-c",
            "import time\n"
            "print('[1/3] parsing...')\n"
            "print('[2/3] optimizing...')\n"
            "print('[3/3] linking...')\n"
            "print('done.')\n"]
    proc = subprocess.Popen(demo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in proc.stdout:
        print("  ", line, end="")
        logf.write(line)
    proc.wait()

print(f"\n日志已写入 {log_path} ({log_path.stat().st_size} bytes)")
log_path.unlink()


# ============================================================
# 9. shlex: 安全地拼接命令字符串
# ============================================================
section("9. shlex: 跨平台的命令字符串解析")

# 场景: 用户传进来一串命令, 你想安全地转成 list
cmd_str = 'g++ -std=c++17 -O2 -DFOO=1 main.cpp -o main'
args = shlex.split(cmd_str, posix=(sys.platform != "win32"))
print(f"解析结果: {args}")
# 之后可以 subprocess.run(args, ...) 安全执行

print("\n=== Day 07 基础练习结束 ===")
