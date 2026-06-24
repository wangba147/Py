"""
DLL / SO 共享库函数签名扫描器
================================
功能:
  - 扫描 Windows .dll 导出的函数列表
  - 扫描 Linux/macOS .so/.dylib 导出的符号
  - 用 ctypes 探测函数签名 (参数个数测试)
  - 生成 ctypes 绑定代码模板

用法:
  python dll_signature_scanner.py --dll math_lib.dll
  python dll_signature_scanner.py --so libmath_lib.so
  python dll_signature_scanner.py --dll math_lib.dll --generate bindings.py
  python dll_signature_scanner.py --system kernel32.dll

适用于:
  - 拿到一个 C++ 编译的 .dll/.so, 想用 ctypes 调用但不知道有哪些函数
  - 快速生成 ctypes 绑定代码骨架
  - 检查 C++ extern "C" 导出是否正确
"""
import argparse
import ctypes
import os
import platform
import subprocess
import sys
import re
from pathlib import Path


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ============================================================
# 1. Windows DLL 导出扫描 (用 dumpbin 或 objdump)
# ============================================================
def scan_dll_exports(dll_path):
    """扫描 Windows DLL 导出的函数列表"""
    exports = []

    # 方法 1: dumpbin (MSVC 自带)
    try:
        result = subprocess.run(
            ["D:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.38.33130/bin/Hostx64/x86/dumpbin", "/exports", str(dll_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # 解析 dumpbin 输出
            # 格式: "        1    0 add (00000000) int add(int, int)"
            in_exports = False
            for line in result.stdout.splitlines():
                if "ordinal" in line.lower() and "name" in line.lower():
                    in_exports = True
                    continue
                if in_exports:
                    line = line.strip()
                    if not line:
                        if exports:  # 连续空行表示结束
                            break
                        continue
                    # 解析: "1    0 add"
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            ordinal = int(parts[0])
                            hint = int(parts[1], 16) if parts[1].startswith("0x") else int(parts[1])
                            name = parts[2]
                            exports.append(name)
                        except ValueError:
                            pass
            if exports:
                return exports
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 方法 2: objdump (MinGW / binutils)
    try:
        result = subprocess.run(
            ["objdump", "-p", str(dll_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            in_exports = False
            for line in result.stdout.splitlines():
                if "Export Table" in line or "[Ordinal/Name Pointer" in line:
                    in_exports = True
                    continue
                if in_exports:
                    line = line.strip()
                    if line and not line.startswith("[") and not line.startswith("Export"):
                        # 格式: "[  0] add"
                        match = re.search(r'\[\s*\d+\]\s+(\w+)', line)
                        if match:
                            exports.append(match.group(1))
            if exports:
                return exports
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 方法 3: nm (通用)
    try:
        result = subprocess.run(
            ["nm", "-D", "--defined-only", str(dll_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 3:
                    # 格式: "00000000 T add"
                    symbol_type = parts[-2] if len(parts) >= 3 else ""
                    name = parts[-1]
                    if symbol_type in ("T", "t", "D", "d", "W", "w"):
                        exports.append(name)
            return exports
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return exports


# ============================================================
# 2. Linux SO / macOS dylib 导出扫描
# ============================================================
def scan_so_exports(so_path):
    """扫描 Linux .so / macOS .dylib 导出的符号"""
    exports = []

    # 用 nm
    try:
        result = subprocess.run(
            ["nm", "-D", "--defined-only", str(so_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 3:
                    symbol_type = parts[-2]
                    name = parts[-1]
                    # T = text (function), D = data, W = weak
                    if symbol_type in ("T", "t", "D", "d", "W", "w", "B", "b", "R", "r"):
                        # 过滤掉编译器内部符号
                        if not name.startswith("_") and not name.startswith("__"):
                            exports.append(name)
                        # macOS 的符号前面有 _
                        elif name.startswith("_") and not name.startswith("__"):
                            exports.append(name[1:])
            return exports
    except FileNotFoundError:
        pass
    except Exception:
        pass

    # 备选: readelf
    try:
        result = subprocess.run(
            ["readelf", "--dyn-syms", str(so_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "FUNC" in line and "GLOBAL" in line:
                    parts = line.split()
                    if len(parts) >= 8:
                        name = parts[-1].split("@")[0]  # 去掉 @GLIBC_x.x
                        if not name.startswith("_"):
                            exports.append(name)
            return exports
    except FileNotFoundError:
        pass
    except Exception:
        pass

    return exports


# ============================================================
# 3. 用 ctypes 探测函数信息
# ============================================================
def probe_function(lib, func_name):
    """用 ctypes 尝试获取函数对象, 探测可用性"""
    try:
        func = getattr(lib, func_name)
        return func
    except AttributeError:
        return None


def guess_return_type(lib, func_name):
    """尝试猜测函数返回类型 (通过调用约定)"""
    # 这只是一个启发式方法, 真正的类型需要查头文件
    func = getattr(lib, func_name, None)
    if func is None:
        return "unknown"
    # 默认 c_int
    return "c_int (assumed)"


# ============================================================
# 4. 生成 ctypes 绑定代码
# ============================================================
def generate_bindings(lib_name, exports, output_file=None):
    """生成 ctypes 绑定 Python 代码骨架"""
    code_lines = [
        '"""',
        f'ctypes 绑定: {lib_name}',
        f'自动生成, 请根据头文件修正 argtypes/restype',
        '"""',
        'import ctypes',
        'import os',
        'import platform',
        '',
        '',
        'def load_lib():',
        f'    """加载 {lib_name}"""',
        f'    system = platform.system()',
        f'    if system == "Windows":',
        f'        return ctypes.CDLL("{lib_name}")',
        f'    elif system == "Darwin":',
        f'        return ctypes.CDLL("{lib_name.replace(".dll", ".dylib")}")',
        f'    else:',
        f'        return ctypes.CDLL("{lib_name.replace(".dll", ".so")}")',
        '',
        '',
        'lib = load_lib()',
        '',
    ]

    for name in exports:
        code_lines.extend([
            f'# {name} —— TODO: 请根据头文件修正参数和返回类型',
            f'lib.{name}.argtypes = []  # TODO: [ctypes.c_int, ctypes.c_double, ...]',
            f'lib.{name}.restype = ctypes.c_int  # TODO: ctypes.c_double / None / ...',
            f'# {name} = lib.{name}',
            '',
        ])

    code = "\n".join(code_lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[OK] 绑定代码已生成: {output_file}")
    else:
        print("\n--- 生成的绑定代码 ---")
        print(code)

    return code


# ============================================================
# 5. 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="DLL/SO 共享库函数签名扫描器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap_example(),
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--dll", type=str, help="Windows DLL 文件路径")
    group.add_argument("--so", type=str, help="Linux .so / macOS .dylib 文件路径")
    group.add_argument("--system", type=str, help="系统库名 (如 kernel32.dll, libc.so.6)")
    parser.add_argument("--generate", type=str, default=None, help="生成 ctypes 绑定代码到指定文件")
    parser.add_argument("--probe", action="store_true", help="用 ctypes 探测函数可用性")
    parser.add_argument("--demo", action="store_true", help="运行演示")
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    # 确定库文件
    lib_path = None
    lib_name = ""
    system = platform.system()

    if args.dll:
        lib_path = Path(args.dll)
        lib_name = lib_path.name
    elif args.so:
        lib_path = Path(args.so)
        lib_name = lib_path.name
    elif args.system:
        lib_name = args.system
        lib_path = args.system  # 系统库, 直接用名字
    else:
        parser.print_help()
        return

    section(f"扫描 {lib_name}")

    # 扫描导出
    if args.dll or (args.system and system == "Windows"):
        exports = scan_dll_exports(lib_path) if lib_path else []
    else:
        exports = scan_so_exports(lib_path) if lib_path else []

    if not exports:
        print("[!] 未找到导出函数 (可能没有 extern \"C\", 或工具未安装)")
        print("    确保安装了以下工具之一: dumpbin (MSVC) / objdump (MinGW) / nm / readelf")
        return

    print(f"找到 {len(exports)} 个导出函数:\n")
    for i, name in enumerate(exports, 1):
        print(f"  {i:3d}. {name}")

    # 用 ctypes 探测
    if args.probe and lib_path:
        section("ctypes 探测")
        try:
            lib = ctypes.CDLL(str(lib_path))
            print("ctypes 加载成功, 探测函数:\n")
            for name in exports:
                func = getattr(lib, name, None)
                if func:
                    print(f"  ✓ {name} — 可调用")
                else:
                    print(f"  ✗ {name} — 不可访问")
        except OSError as e:
            print(f"ctypes 加载失败: {e}")

    # 生成绑定代码
    if args.generate:
        generate_bindings(lib_name, exports, args.generate)
    else:
        generate_bindings(lib_name, exports)


def textwrap_example():
    return """
示例:
  python dll_signature_scanner.py --dll math_lib.dll
  python dll_signature_scanner.py --so libmath_lib.so
  python dll_signature_scanner.py --dll math_lib.dll --generate bindings.py
  python dll_signature_scanner.py --system kernel32.dll --probe
  python dll_signature_scanner.py --demo
"""


# ============================================================
# 6. 演示模式
# ============================================================
def run_demo():
    """演示: 扫描系统库的导出函数"""
    section("DLL/SO 签名扫描器 —— 演示模式")
    system = platform.system()

    if system == "Windows":
        # 演示扫描 kernel32.dll 的部分函数
        lib_name = "kernel32.dll"
        print(f"扫描系统库: {lib_name}\n")

        # 用 ctypes 直接加载
        try:
            lib = ctypes.WinDLL("kernel32") if hasattr(ctypes, "WinDLL") else ctypes.CDLL("kernel32")
            print("[OK] 加载 kernel32 成功\n")
        except OSError as e:
            print(f"[!] 加载失败: {e}")
            return

        # 测试一些常见的 kernel32 函数
        known_funcs = [
            "GetTickCount", "GetCurrentProcessId", "GetLastError",
            "Sleep", "GetModuleHandleA", "GetModuleHandleW",
            "QueryPerformanceCounter", "GetConsoleMode",
            "SetConsoleMode", "GetStdHandle",
        ]

        print("已知函数探测:\n")
        for name in known_funcs:
            func = getattr(lib, name, None)
            if func:
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name} (未找到)")

        # 调用几个简单的
        print("\n调用示例:\n")

        lib.GetTickCount.restype = ctypes.c_uint32
        tick = lib.GetTickCount()
        print(f"  GetTickCount() = {tick} ({tick / 3600000:.1f} 小时)")

        lib.GetCurrentProcessId.restype = ctypes.c_uint32
        pid = lib.GetCurrentProcessId()
        print(f"  GetCurrentProcessId() = {pid}")

        # Sleep 10ms
        lib.Sleep.argtypes = [ctypes.c_uint32]
        lib.Sleep.restype = None
        lib.Sleep(10)
        print(f"  Sleep(10) — done")

        print(f"\n[提示] 完整扫描 .dll 需要安装 dumpbin 或 objdump")
        print(f"[提示] 运行 --dll <file> --generate bindings.py 生成绑定代码")

    else:
        # Linux/macOS
        lib_name = "libc.so.6" if system == "Linux" else "libc.dylib"
        print(f"扫描系统库: {lib_name}\n")

        try:
            lib = ctypes.CDLL(lib_name)
            print("[OK] 加载 libc 成功\n")
        except OSError as e:
            print(f"[!] 加载失败: {e}")
            return

        known_funcs = ["getpid", "rand", "srand", "time", "clock", "abs"]

        print("已知函数探测:\n")
        for name in known_funcs:
            func = getattr(lib, name, None)
            if func:
                print(f"  ✓ {name}")
            else:
                print(f"  ✗ {name}")

        print("\n调用示例:\n")

        lib.getpid.restype = ctypes.c_int
        print(f"  getpid() = {lib.getpid()}")

        lib.srand.argtypes = [ctypes.c_uint]
        lib.srand(42)

        lib.rand.restype = ctypes.c_int
        print(f"  rand() (seed=42) = {lib.rand()}, {lib.rand()}, {lib.rand()}")

        print(f"\n[提示] 运行 --so <file> --generate bindings.py 生成绑定代码")

    section("扫描器功能总结")
    print("""
这个工具帮助你:
  1. 发现 .dll/.so 导出了哪些 C 函数
  2. 用 ctypes 探测哪些函数可以加载
  3. 自动生成 ctypes 绑定代码骨架
  4. 快速调用系统库做实验

实际用途:
  - 拿到第三方 C++ SDK 的 .dll, 不知道有哪些函数 → 扫描它
  - 验证 extern "C" 导出是否正确 → 扫描编译产物
  - 快速写 ctypes 绑定 → --generate 生成骨架
  - 学习 Win32 API → --system kernel32.dll --probe
""")


if __name__ == "__main__":
    import textwrap
    main()
