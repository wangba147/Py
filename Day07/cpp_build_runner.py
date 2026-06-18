"""
Day 07 实战工具: cpp_build_runner.py
=====================================
功能: 给定一个 C++ 源文件, 自动用 g++/clang++ 编译并执行,
     把 stdout/stderr/退出码/耗时写到一份 JSON 报告里。

适用场景:
  - 平时手动敲 g++ ... && ./a.out, 写个脚本一次跑完
  - 提交代码前自检: 一键编译 + 跑几个简单测试
  - 教学/演示环境: 让脚本替学生跑通第一个 C++ 程序

C++ 对比:
  - 以前要写个 .bat / .sh, 加 tee, 加 errorlevel 判断, 加计时
  - Python + subprocess 几行就能搞定, 还跨平台

使用方法:
  python cpp_build_runner.py source.cpp [--compiler g++] [--std c++17]
                                       [--arg arg1 --arg arg2]
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def find_compiler(prefer: str | None = None) -> list[str] | None:
    """按优先级找可用的 C++ 编译器. C++ 里要 SearchPathW, 这里 shutil.which 一行"""
    candidates = []
    if prefer:
        candidates.append([prefer])
    for c in (["g++"], ["clang++"]):
        if c not in candidates:
            candidates.append(c)
    for cmd in candidates:
        if shutil.which(cmd[0]) is not None:
            return cmd
    return None


def build(source: Path, exe: Path, compiler: list[str], std: str, extra: list[str]) -> dict:
    """编译 source -> exe, 返回 {ok, returncode, cmd, stdout, stderr, seconds}"""
    cmd = compiler + [f"-std={std}"] + extra + [str(source), "-o", str(exe)]
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.perf_counter() - t0
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "cmd": cmd,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "seconds": round(dt, 3),
    }


def run(exe: Path, args: list[str], timeout: float) -> dict:
    """执行编译产物, 返回 {ok, returncode, stdout, stderr, seconds}"""
    cmd = [str(exe)] + args
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        dt = time.perf_counter() - t0
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "cmd": cmd,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "seconds": round(dt, 3),
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": -1,
            "cmd": cmd,
            "stdout": "",
            "stderr": f"[timeout after {timeout}s]",
            "seconds": round(time.perf_counter() - t0, 3),
        }


def main() -> int:
    p = argparse.ArgumentParser(description="编译并运行一个 C++ 源文件, 输出 JSON 报告")
    p.add_argument("source", type=Path, help="C++ 源文件路径")
    p.add_argument("--compiler", help="指定编译器 (g++/clang++/cl), 不指定则自动探测")
    p.add_argument("--std", default="c++17", help="C++ 标准 (默认 c++17)")
    p.add_argument("--arg", action="append", default=[], help="传给可执行文件的参数, 可重复")
    p.add_argument("--extra", action="append", default=[],
                   help="传给编译器的额外参数, 例如 -O2 -Wall, 可重复")
    p.add_argument("--timeout", type=float, default=10.0, help="运行超时秒数")
    p.add_argument("--report", type=Path, help="把结果写到这份 JSON 报告")
    p.add_argument("--keep-exe", action="store_true", help="保留编译产物")
    args = p.parse_args()

    if not args.source.exists():
        print(f"[!] 找不到源文件: {args.source}", file=sys.stderr)
        return 2

    compiler = find_compiler(args.compiler)
    if compiler is None:
        print("[!] 找不到任何 C++ 编译器, 请先安装 g++/clang++/MSVC", file=sys.stderr)
        return 3

    print(f"[+] 编译器: {' '.join(compiler)}")
    print(f"[+] 源文件: {args.source}  ({args.source.stat().st_size} bytes)")

    # 编译产物放在源文件同目录
    suffix = ".exe" if sys.platform == "win32" else ""
    exe = args.source.with_suffix(suffix)
    print(f"[+] 目标文件: {exe}")

    # ---- 编译 ----
    print("[*] 编译中 ...")
    b = build(args.source, exe, compiler, args.std, args.extra)
    print(f"    returncode = {b['returncode']}  ({b['seconds']}s)")
    if b["stderr"].strip():
        print("    --- stderr ---")
        print(b["stderr"].rstrip())
    if not b["ok"]:
        print("[!] 编译失败, 不再执行")
        report = {"compile": b, "run": None}
        if args.report:
            args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
        return 1

    # ---- 执行 ----
    print("[*] 运行中 ...")
    r = run(exe, args.arg, args.timeout)
    print(f"    returncode = {r['returncode']}  ({r['seconds']}s)")
    if r["stdout"].strip():
        print("    --- stdout ---")
        print(r["stdout"].rstrip())
    if r["stderr"].strip():
        print("    --- stderr ---")
        print(r["stderr"].rstrip())

    # ---- 汇总 ----
    report = {
        "source": str(args.source),
        "compiler": compiler,
        "std": args.std,
        "compile": b,
        "run": r,
        "summary": {
            "build_ok": b["ok"],
            "run_ok": r["ok"],
            "total_seconds": round(b["seconds"] + r["seconds"], 3),
        },
    }

    if args.report:
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                               encoding="utf-8")
        print(f"[+] 报告已写入: {args.report}")

    if not args.keep_exe and exe.exists():
        exe.unlink()

    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
