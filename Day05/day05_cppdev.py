#!/usr/bin/env python3
"""cppdev — C++ 项目辅助工具包

演示 Python 包的组织结构，以及标准库在 C++ 开发中的实际应用。

用法:
    python -m day05_cppdev scan <目录>        # 扫描 C++ 源文件
    python -m day05_cppdev scan <目录> -j     # 输出 JSON 格式
    python -m day05_cppdev stats <目录>       # 统计代码行数
"""

import sys
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter


# ---- 扫描模块 ----

def scan_sources(root_dir, extensions=None, ignore_dirs=None):
    """
    扫描目录下的 C++ 源文件，按扩展名分组。

    C++ 对应: 递归遍历 std::filesystem + 手动分组
    Python: pathlib.rglob + defaultdict，几行搞定

    Args:
        root_dir: 项目根目录
        extensions: 要扫描的扩展名集合
        ignore_dirs: 要忽略的目录名集合

    Returns:
        dict: {扩展名: [相对路径列表]}
    """
    if extensions is None:
        extensions = {".cpp", ".h", ".hpp", ".cc", ".cxx", ".c", ".hxx"}
    if ignore_dirs is None:
        ignore_dirs = {".git", ".svn", "build", "cmake-build-debug",
                       "cmake-build-release", "__pycache__", "node_modules",
                       ".vs", "out", "x64", "Debug", "Release"}

    root = Path(root_dir)
    if not root.exists():
        print(f"错误: 目录不存在 — {root}", file=sys.stderr)
        return {}

    groups = defaultdict(list)

    for f in root.rglob("*"):
        if not f.is_file():
            continue

        # 检查扩展名
        if f.suffix not in extensions:
            continue

        # 检查是否在忽略目录中
        rel = f.relative_to(root)
        if any(part in ignore_dirs or part.startswith(".")
               for part in rel.parts):
            continue

        groups[f.suffix].append(str(rel))

    return dict(groups)


# ---- 统计模块 ----

def count_lines(filepath):
    """
    统计代码行数、空行数、注释行数。

    简化版 C++ 行数统计（仅支持 // 和 /* */ 注释）。
    C++ 用脚本做这类分析很麻烦，Python 几行搞定。
    """
    path = Path(filepath)
    if not path.exists():
        return None

    total = 0
    blank = 0
    comment = 0
    in_block_comment = False

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                total += 1
                stripped = line.strip()

                if not stripped:
                    blank += 1
                    continue

                if in_block_comment:
                    comment += 1
                    if "*/" in stripped:
                        in_block_comment = False
                    continue

                if stripped.startswith("//"):
                    comment += 1
                elif stripped.startswith("/*"):
                    comment += 1
                    if "*/" not in stripped:
                        in_block_comment = True
    except Exception as e:
        print(f"  警告: 无法读取 {filepath}: {e}", file=sys.stderr)
        return None

    return {
        "total": total,
        "blank": blank,
        "comment": comment,
        "code": total - blank - comment,
    }


def project_stats(root_dir, extensions=None):
    """
    统计项目代码量。

    返回包含汇总信息的结果，适合生成报告或输出 JSON。
    """
    sources = scan_sources(root_dir, extensions)
    if not sources:
        return {"files": 0, "summary": None}

    totals = Counter()
    details = []

    for ext, files in sorted(sources.items()):
        ext_stats = {"extension": ext, "files": len(files), "lines": Counter()}

        for f in files:
            full_path = Path(root_dir) / f
            lc = count_lines(full_path)
            if lc:
                for key in ["total", "blank", "comment", "code"]:
                    ext_stats["lines"][key] += lc[key]
                    totals[key] += lc[key]

        details.append(ext_stats)

    return {
        "files": sum(len(v) for v in sources.values()),
        "summary": dict(totals),
        "by_extension": details,
    }


# ---- 主入口 ----

def main():
    """命令行入口，用 argparse 解析参数。"""
    parser = argparse.ArgumentParser(
        prog="cppdev",
        description="C++ 项目辅助工具",
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # scan 子命令
    scan_parser = sub.add_parser("scan", help="扫描 C++ 源文件")
    scan_parser.add_argument("directory", help="项目目录")
    scan_parser.add_argument("-j", "--json", action="store_true",
                             help="输出 JSON 格式")

    # stats 子命令
    stats_parser = sub.add_parser("stats", help="统计代码行数")
    stats_parser.add_argument("directory", help="项目目录")
    stats_parser.add_argument("-j", "--json", action="store_true",
                              help="输出 JSON 格式")

    args = parser.parse_args()

    if args.command == "scan":
        result = scan_sources(args.directory)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            for ext, files in sorted(result.items()):
                print(f"\n{ext} ({len(files)} 个文件):")
                for f in files:
                    print(f"  {f}")

    elif args.command == "stats":
        result = project_stats(args.directory)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            s = result.get("summary")
            if s:
                print(f"\n代码统计:")
                print(f"  文件数:   {result['files']}")
                print(f"  总行数:   {s['total']}")
                print(f"  代码行:   {s['code']}")
                print(f"  注释行:   {s['comment']}")
                print(f"  空行:     {s['blank']}")
                print(f"\n按扩展名:")
                for ext_info in result.get("by_extension", []):
                    lines = ext_info["lines"]
                    print(f"  {ext_info['extension']}: "
                          f"{ext_info['files']} 文件, "
                          f"{lines.get('code', 0)} 行代码, "
                          f"{lines.get('comment', 0)} 行注释")
            else:
                print("未找到 C++ 源文件")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
