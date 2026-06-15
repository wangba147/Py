#!/usr/bin/env python3
"""Day 05: 模块、包与标准库 — 练习脚本

面向 C++ 开发者的 Python 学习
运行: python day05_basics.py
"""

import sys
import os
from pathlib import Path
from collections import defaultdict, Counter, namedtuple
import json
import argparse

# ============================================================
# 1. import 的多种方式
# ============================================================
# C++: #include "mylib.h" + using namespace mylib;
# Python: 有多种 import 风格

print("=" * 60)
print("1. import 的多种方式")
print("=" * 60)

# 方式一：导入整个模块（推荐，命名空间清晰）
# C++ 等价: #include "math.h" + math::sqrt()
import math
print(f"math.sqrt(16) = {math.sqrt(16)}")

# 方式二：导入特定名称
# C++ 等价: using mylib::add;
from os.path import exists, join
print(f"exists('.') = {exists('.')}")

# 方式三：别名（常见于大型库）
# C++ 等价: namespace fs = std::filesystem;
# import numpy as np  # 需要安装: pip install numpy
# 上面的例子说明别名是常见惯例（如 import numpy as np）

# 用标准库演示别名
from collections import defaultdict as ddict
d = ddict(list)
d["cpp"].append("main.cpp")
print(f"defaultdict alias: {dict(d)}")

# 方式四：不推荐 — import *
# C++ 等价: using namespace std; (在头文件中)
# from os import *  # 污染命名空间，不要这样做！

print()

# ============================================================
# 2. __name__ 与模块自测
# ============================================================
# C++ 没有直接对应；C++ 需要单独的 test 文件
# Python 每个 .py 文件都可以判断自己是主程序还是被导入

print("=" * 60)
print("2. __name__ 与模块自测")
print("=" * 60)

def add(a, b):
    """加法函数 — 带自测"""
    return a + b

# C++ 无法在库文件中直接写测试，必须分离 test 文件
# Python 用 __name__ 惯例实现"同文件测试"
if __name__ == "__main__":
    # 只有直接运行此文件时才执行测试
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    print("__name__ 测试通过！当前 __name__ =", __name__)
else:
    print(f"  被导入时 __name__ = {__name__}")

# 查看模块缓存
# C++ 的 include guard 只防止重复包含
# Python 的 sys.modules 缓存整个模块对象
print(f"'math' in sys.modules: {'math' in sys.modules}")
print(f"sys.modules['math'] = {sys.modules['math']}")

print()

# ============================================================
# 3. sys.path — 模块搜索路径
# ============================================================
# C++ 对应: -I 编译选项 / INCLUDE 环境变量
# Python: sys.path 列表，运行时可修改

print("=" * 60)
print("3. sys.path — 模块搜索路径")
print("=" * 60)

print("sys.path 搜索顺序:")
for i, p in enumerate(sys.path[:5]):
    print(f"  [{i}] {p}")
if len(sys.path) > 5:
    print(f"  ... 共 {len(sys.path)} 条路径")

# 动态添加搜索路径（类似 C++ 的 -I 选项）
# sys.path.append("D:/my_libs")
# 但更好的方式是用 .pth 文件或设置 PYTHONPATH 环境变量

print()

# ============================================================
# 4. pathlib — 文件系统操作（Python 3.4+）
# ============================================================
# C++ 对应: std::filesystem (C++17)
# Python 的 pathlib 更简洁直观

print("=" * 60)
print("4. pathlib — 文件系统操作")
print("=" * 60)

# 当前目录
cwd = Path.cwd()
print(f"当前目录: {cwd}")

# 路径拼接 — Python 用 / 运算符！（比 C++ 的 / 运算符更直观）
# C++: auto p = fs::path("src") / "main.cpp";
config_path = cwd / "config.json"
print(f"路径拼接: {config_path}")

# 检查存在性
# C++: bool e = fs::exists(p);
print(f"当前目录存在: {cwd.exists()}")

# 路径属性
# C++: p.filename(), p.extension(), p.parent_path()
sample = Path("src/core/main.cpp")
print(f"文件名: {sample.name}")          # main.cpp
print(f"扩展名: {sample.suffix}")        # .cpp
print(f"无扩展名: {sample.stem}")        # main
print(f"父目录: {sample.parent}")        # src/core

# 遍历目录
# C++: for (auto& e : fs::directory_iterator("dir"))
print(f"\n当前目录的文件:")
for entry in sorted(cwd.iterdir())[:8]:
    kind = "DIR" if entry.is_dir() else "FILE"
    print(f"  [{kind}] {entry.name}")
if len(list(cwd.iterdir())) > 8:
    print("  ...")

# 递归 glob 查找
# C++: fs::recursive_directory_iterator + 过滤
# Python: Path.rglob("*.py")
py_files = list(cwd.rglob("*.py"))
print(f"\n当前目录下 .py 文件数: {len(py_files)}")
for f in py_files[:5]:
    print(f"  {f.relative_to(cwd)}")

print()

# ============================================================
# 5. collections — 高级数据结构
# ============================================================
# C++ 对应: std::unordered_map, 手写统计, struct

print("=" * 60)
print("5. collections — 高级数据结构")
print("=" * 60)

# defaultdict — 自动初始化缺失 key
# C++ 等价: std::unordered_map<K, std::vector<V>> + 检查 key 存在
# C++ 的 map[] 会自动创建默认值，但 unordered_map 的 value 类型
# 必须默认可构造；Python 更灵活，可指定工厂函数

file_groups = defaultdict(list)
for name, ext in [("main", ".cpp"), ("utils", ".h"),
                   ("core", ".cpp"), ("config", ".h"),
                   ("test", ".cpp")]:
    file_groups[ext].append(name)

print("文件分组（defaultdict）:")
for ext, names in sorted(file_groups.items()):
    print(f"  {ext}: {names}")

# Counter — 频率统计
# C++ 等价: std::unordered_map<string, int> + 手动递增
log_lines = [
    "ERROR: segfault in main.cpp:42",
    "WARNING: unused variable in utils.h",
    "ERROR: null pointer in core.cpp:15",
    "ERROR: segfault in main.cpp:42",
    "WARNING: implicit conversion in core.cpp",
    "INFO: build complete",
    "ERROR: null pointer in core.cpp:15",
]

# 提取日志级别
levels = [line.split(":")[0] for line in log_lines]
level_counts = Counter(levels)
print(f"\n日志级别统计: {dict(level_counts)}")
print(f"最多的: {level_counts.most_common(1)}")

# namedtuple — 轻量结构体
# C++ 等价: struct CompileResult { bool success; string output; vector<string> errors; };
CompileResult = namedtuple("CompileResult", ["success", "output", "errors"])

result = CompileResult(True, "build/main.o", [])
print(f"\nCompileResult: success={result.success}, output={result.output}")
# namedtuple 也可以按索引访问（像 tuple）
print(f"  按索引: result[0]={result[0]}")

print()

# ============================================================
# 6. json — 配置文件处理
# ============================================================
# C++ 对应: nlohmann/json (第三方) 或 手写解析

print("=" * 60)
print("6. json — 配置文件处理")
print("=" * 60)

# 模拟 C++ 项目的编译数据库
compile_db = [
    {
        "directory": "/home/user/project",
        "command": "clang++ -std=c++20 -c main.cpp -o main.o",
        "file": "main.cpp"
    },
    {
        "directory": "/home/user/project",
        "command": "clang++ -std=c++20 -c utils.cpp -o utils.o",
        "file": "utils.cpp"
    },
    {
        "directory": "/home/user/project",
        "command": "clang++ -std=c++20 -c core.cpp -o core.o",
        "file": "core.cpp"
    },
]

# 序列化为 JSON 字符串
# C++: json j = compile_db; string s = j.dump(2);
json_str = json.dumps(compile_db, indent=2)
print("compile_commands.json:")
print(json_str[:300] + "...")

# 反序列化
# C++: auto data = json::parse(json_str);
parsed = json.loads(json_str)
cpp_files = [e["file"] for e in parsed if e["file"].endswith(".cpp")]
print(f"\n.cpp 文件: {cpp_files}")

# 解析编译标志
# C++: 需要手动 split 或用 string_view
flags = set()
for entry in parsed:
    parts = entry["command"].split()
    for p in parts:
        if p.startswith("-"):
            flags.add(p)
print(f"编译标志: {sorted(flags)}")

print()

# ============================================================
# 7. argparse — 命令行参数
# ============================================================
# C++ 对应: CLI11 / cxxopts / getopt（均为第三方）

print("=" * 60)
print("7. argparse — 命令行参数")
print("=" * 60)

# 演示用：手动构造参数，避免干扰实际命令行
def demo_argparse():
    """演示 argparse 的用法"""
    parser = argparse.ArgumentParser(
        description="C++ 项目构建辅助工具",
        epilog="示例: python tool.py -j 8 --release src/"
    )

    # 位置参数（必选）
    parser.add_argument("project_dir", help="项目根目录")

    # 可选参数
    parser.add_argument("-j", "--jobs", type=int, default=4,
                        help="并行编译任务数 (默认: 4)")
    parser.add_argument("--release", action="store_true",
                        help="Release 模式（默认 Debug）")
    parser.add_argument("--compiler", default="clang++",
                        choices=["clang++", "g++", "msvc"],
                        help="编译器选择")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="详细输出 (-v, -vv)")

    # 模拟解析（实际使用时不传 args 则用 sys.argv）
    args = parser.parse_args(["D:/my_project", "-j", "8", "--release", "-vvv"])

    print(f"项目目录: {args.project_dir}")
    print(f"并行任务: {args.jobs}")
    print(f"Release:  {args.release}")
    print(f"编译器:   {args.compiler}")
    print(f"详细级别: {args.verbose}")

demo_argparse()

print()

# ============================================================
# 8. 包结构示例
# ============================================================
# C++ 对应: 目录 + CMakeLists.txt
# Python: 目录 + __init__.py

print("=" * 60)
print("8. 包结构演示")
print("=" * 60)

# 演示一个工具包的模块组织
print("""
推荐的 C++ 辅助工具包结构:

cppdev/
├── __init__.py          # 包入口，导出公开 API
├── scanner.py           # 扫描 C++ 源文件
├── builder.py           # 构建辅助
├── analyzer.py          # 代码分析
└── utils/
    ├── __init__.py
    ├── cmake_helper.py  # CMake 辅助
    └── log_parser.py    # 日志解析
""")

# __init__.py 中常见的模式
print("__init__.py 典型写法:")
print("""
from .scanner import scan_sources
from .builder import build_project

__version__ = "0.1.0"
__all__ = ["scan_sources", "build_project"]
""")

# 相对导入示例
print("相对导入（包内部使用）:")
print("""
# 在 cppdev/builder.py 中
from .scanner import scan_sources   # 同包内的模块
from .utils.cmake_helper import generate_cmake  # 子包

# 绝对导入（也可用，但包内推荐相对导入）
# from cppdev.scanner import scan_sources
""")

print()

# ============================================================
# 9. 虚拟环境速查
# ============================================================
print("=" * 60)
print("9. 虚拟环境速查")
print("=" * 60)
print("""
# C++ 对应: 不同 build 目录 / vcpkg manifest
# Python: 虚拟环境隔离依赖

# 创建
python -m venv .venv

# 激活 (Windows)
.venv\\Scripts\\activate

# 激活 (Linux/Mac)
source .venv/bin/activate

# 安装包
pip install pybind11 cmake-format

# 导出依赖
pip freeze > requirements.txt

# 还原依赖
pip install -r requirements.txt
""")

# 检查当前是否在虚拟环境中
in_venv = hasattr(sys, 'real_prefix') or (
    hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
)
print(f"当前是否在虚拟环境中: {in_venv}")
print(f"Python 路径: {sys.executable}")

print()

# ============================================================
# 综合练习
# ============================================================
print("=" * 60)
print("综合练习：C++ 源文件扫描工具")
print("=" * 60)

def scan_cpp_sources(root_dir, extensions=None):
    """
    扫描目录下的 C++ 源文件并按类型分组。

    C++ 等价需要:
    - std::filesystem::recursive_directory_iterator
    - std::unordered_map<string, vector<string>>
    - 手动扩展名匹配

    Python 版本只需几行！
    """
    if extensions is None:
        extensions = {".cpp", ".h", ".hpp", ".cc", ".cxx", ".c"}

    root = Path(root_dir)
    if not root.exists():
        print(f"目录不存在: {root}")
        return {}

    groups = defaultdict(list)
    for ext in extensions:
        for f in root.rglob(f"*{ext}"):
            # 排除常见忽略目录
            rel = f.relative_to(root)
            parts = rel.parts
            if any(p.startswith(".") or p in {"build", "cmake-build-*", "__pycache__"}
                   for p in parts):
                continue
            groups[ext].append(str(rel))

    return dict(groups)


# 扫描当前目录（演示）
current_dir = Path.cwd()
# 尝试扫描上级目录中的 C++ 文件（如果有的话）
for scan_dir in [current_dir, current_dir.parent]:
    if scan_dir.exists():
        result = scan_cpp_sources(scan_dir)
        if any(result.values()):
            print(f"扫描 {scan_dir}:")
            for ext, files in sorted(result.items()):
                print(f"  {ext}: {len(files)} 个文件")
                for f in files[:3]:
                    print(f"    - {f}")
                if len(files) > 3:
                    print(f"    ... 共 {len(files)} 个")
            break
else:
    print("未找到 C++ 源文件（这是正常的，如果你没有 .cpp 文件在此目录下）")

print()
print("Day 05 练习完成！关键知识点:")
print("  1. import 的四种方式（推荐 import X 或 from X import Y）")
print("  2. __name__ == '__main__' 实现模块自测")
print("  3. pathlib.Path 替代 os.path，用 / 拼接路径")
print("  4. collections: defaultdict, Counter, namedtuple")
print("  5. json 直接处理配置文件")
print("  6. argparse 内置命令行解析")
print("  7. 包 = 目录 + __init__.py")
print("  8. 虚拟环境隔离项目依赖")
