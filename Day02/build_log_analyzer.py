"""
Day 02 实用工具 — C++ 构建日志分析器
分析 CMake/Make 构建日志，统计编译时间、警告、错误

用法:
  python build_log_analyzer.py <日志文件路径>
  python build_log_analyzer.py --demo    # 使用内置示例日志

示例:
  python build_log_analyzer.py build_output.log
  cmake --build build 2>&1 | python build_log_analyzer.py -
"""

import sys
import io
import re
import argparse
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

# 修复 Windows 终端 Unicode 输出问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ============================================================
# 日志解析器
# ============================================================

class BuildLogAnalyzer:
    """C++ 构建日志分析器"""

    # 常见编译警告/错误的正则模式
    WARNING_PATTERNS = [
        re.compile(r"warning\s*:", re.IGNORECASE),
        re.compile(r"\[-W\w+\]"),  # GCC/Clang 警告标签
        re.compile(r"Warning\s+\w+", re.IGNORECASE),  # MSVC 风格
    ]

    ERROR_PATTERNS = [
        re.compile(r"error\s*:", re.IGNORECASE),
        re.compile(r"fatal error", re.IGNORECASE),
        re.compile(r"Error\s+\w+", re.IGNORECASE),  # MSVC 风格
        re.compile(r"LINK\s*:", re.IGNORECASE),  # 链接错误
    ]

    def __init__(self, log_content: str):
        self.lines = log_content.splitlines()
        self.warnings: list[dict] = []
        self.errors: list[dict] = []
        self.file_compile_times: dict[str, float] = {}
        self.target_times: dict[str, float] = {}
        self.warning_categories: dict[str, int] = defaultdict(int)

    def analyze(self) -> dict:
        """执行完整分析"""
        for line_num, line in enumerate(self.lines, 1):
            self._check_warning(line, line_num)
            self._check_error(line, line_num)
            self._check_compile_time(line)
            self._check_target_time(line)
        return self._generate_report()

    def _check_warning(self, line: str, line_num: int) -> None:
        for pattern in self.WARNING_PATTERNS:
            if pattern.search(line):
                # 尝试提取文件名
                source_file = self._extract_source_file(line)
                # 尝试提取警告类别
                category = self._extract_warning_category(line)
                if category:
                    self.warning_categories[category] += 1
                self.warnings.append({
                    "line_num": line_num,
                    "source": source_file,
                    "category": category,
                    "content": line.strip(),
                })
                break

    def _check_error(self, line: str, line_num: int) -> None:
        for pattern in self.ERROR_PATTERNS:
            if pattern.search(line):
                source_file = self._extract_source_file(line)
                self.errors.append({
                    "line_num": line_num,
                    "source": source_file,
                    "content": line.strip(),
                })
                break

    def _check_compile_time(self, line: str) -> None:
        # 匹配: Building CXX object src/CMakeFiles/core.dir/main.cpp.o
        match = re.search(r"Building\s+\w+\s+object\s+.*?(\S+\.cpp)\.o", line)
        if match:
            source = Path(match.group(1)).name
            self.file_compile_times[source] = self.file_compile_times.get(source, 0)

    def _check_target_time(self, line: str) -> None:
        # 匹配: Built target MyApp (3.2 seconds)
        match = re.search(r"Built target\s+(\S+)\s+\(([\d.]+)\s+seconds?\)", line)
        if match:
            target = match.group(1)
            seconds = float(match.group(2))
            self.target_times[target] = seconds

    def _extract_source_file(self, line: str) -> str | None:
        # GCC/Clang: file.cpp:42:5: warning: ...
        match = re.search(r"(\S+\.(?:cpp|c|h|hpp|cc|cxx)):\d+", line)
        return match.group(1) if match else None

    def _extract_warning_category(self, line: str) -> str | None:
        # [-Wwarning-type]
        match = re.search(r"\[-(W\w+)\]", line)
        return match.group(1) if match else None

    def _generate_report(self) -> dict:
        # 按源文件统计警告
        warnings_by_file = defaultdict(list)
        for w in self.warnings:
            if w["source"]:
                warnings_by_file[w["source"]].append(w)

        # 按耗时排序的目标
        sorted_targets = sorted(
            self.target_times.items(), key=lambda x: x[1], reverse=True
        )

        # 总编译时间
        total_time = sum(self.target_times.values())

        return {
            "total_lines": len(self.lines),
            "warning_count": len(self.warnings),
            "error_count": len(self.errors),
            "warnings_by_file": dict(warnings_by_file),
            "warning_categories": dict(self.warning_categories),
            "errors": self.errors,
            "target_times": sorted_targets,
            "total_build_time": total_time,
        }


# ============================================================
# 报告格式化
# ============================================================

def print_report(report: dict, verbose: bool = False) -> None:
    """打印格式化的分析报告"""

    # 摘要
    print("=" * 60)
    print("  C++ 构建日志分析报告")
    print("=" * 60)
    print(f"  日志总行数:   {report['total_lines']}")
    print(f"  警告数量:     {report['warning_count']}")
    print(f"  错误数量:     {report['error_count']}")
    print(f"  总构建时间:   {report['total_build_time']:.1f}s")

    # 状态判断
    if report["error_count"] > 0:
        print(f"\n  ❌ 构建失败！有 {report['error_count']} 个错误")
    elif report["warning_count"] > 0:
        print(f"\n  ⚠️  构建成功，但有 {report['warning_count']} 个警告")
    else:
        print("\n  ✅ 构建成功，无警告无错误")

    # 编译耗时排名
    if report["target_times"]:
        print("\n--- 编译耗时排名 ---")
        for i, (target, seconds) in enumerate(report["target_times"], 1):
            bar = "█" * int(seconds * 2)  # 简易柱状图
            print(f"  {i}. {target:<25s} {seconds:>6.1f}s {bar}")

    # 警告类别统计
    if report["warning_categories"]:
        print("\n--- 警告类别统计 ---")
        sorted_cats = sorted(
            report["warning_categories"].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        for cat, count in sorted_cats:
            print(f"  -{cat:<30s} ×{count}")

    # 按文件统计警告
    if report["warnings_by_file"]:
        print("\n--- 文件警告分布 ---")
        sorted_files = sorted(
            report["warnings_by_file"].items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )
        for file, warnings in sorted_files:
            print(f"  {file}: {len(warnings)} 个警告")
            if verbose:
                for w in warnings[:3]:
                    print(f"    L{w['line_num']}: {w['content'][:80]}")

    # 错误详情
    if report["errors"]:
        print("\n--- 错误详情 ---")
        for e in report["errors"][:10]:
            source_info = f" ({e['source']})" if e["source"] else ""
            print(f"  L{e['line_num']}{source_info}: {e['content'][:80]}")

    print("\n" + "=" * 60)


# ============================================================
# 内置示例日志
# ============================================================

DEMO_LOG = """
[  5%] Building CXX object src/CMakeFiles/core.dir/main.cpp.o
[ 10%] Building CXX object src/CMakeFiles/core.dir/app.cpp.o
[ 15%] Building CXX object src/CMakeFiles/core.dir/config.cpp.o
src/config.cpp:25:10: warning: unused variable 'bufferSize' [-Wunused-variable]
[ 20%] Building CXX object src/CMakeFiles/core.dir/logger.cpp.o
[ 25%] Building CXX object src/CMakeFiles/core.dir/parser.cpp.o
src/parser.cpp:42:5: warning: unused variable 'temp' [-Wunused-variable]
src/parser.cpp:55:12: warning: comparison between signed and unsigned integer expressions [-Wsign-compare]
[ 30%] Building CXX object src/CMakeFiles/core.dir/renderer.cpp.o
src/renderer.cpp:108:10: error: 'glClearColor' was not declared in this scope
src/renderer.cpp:108:10: note: suggested alternative: 'glClear'
src/renderer.cpp:200:3: warning: comparison between signed and unsigned [-Wsign-compare]
src/renderer.cpp:230:8: warning: implicit conversion from 'double' to 'float' [-Wconversion]
[ 50%] Built target core (4.8 seconds)
[ 55%] Building CXX object src/CMakeFiles/ui.dir/mainwindow.cpp.o
src/mainwindow.cpp:88:15: warning: unused parameter 'event' [-Wunused-parameter]
src/mainwindow.cpp:102:5: warning: missing field 'flags' initializer [-Wmissing-field-initializers]
[ 60%] Building CXX object src/CMakeFiles/ui.dir/dialog.cpp.o
[ 65%] Building CXX object src/CMakeFiles/ui.dir/toolbar.cpp.o
src/toolbar.cpp:30:5: warning: unused variable 'iconSize' [-Wunused-variable]
[ 70%] Built target ui (2.3 seconds)
[ 75%] Building CXX object tests/CMakeFiles/tests.dir/test_main.cpp.o
[ 80%] Building CXX object tests/CMakeFiles/tests.dir/test_parser.cpp.o
tests/test_parser.cpp:30:5: warning: implicit conversion from 'double' to 'float' [-Wconversion]
tests/test_parser.cpp:45:10: error: no matching function for call to 'parse(const char [5])'
[ 85%] Built target tests (1.5 seconds)
[ 90%] Linking CXX executable MyCppApp
[ 95%] Built target MyCppApp (5.2 seconds)
[100%] Built target All (15.3 seconds)
"""


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="C++ 构建日志分析器 — 统计编译耗时、警告和错误"
    )
    parser.add_argument(
        "logfile",
        nargs="?",
        default=None,
        help="构建日志文件路径（使用 - 读取标准输入）",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用内置示例日志进行分析",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细的警告/错误内容",
    )

    args = parser.parse_args()

    # 获取日志内容
    if args.demo:
        log_content = DEMO_LOG
    elif args.logfile:
        if args.logfile == "-":
            log_content = sys.stdin.read()
        else:
            log_path = Path(args.logfile)
            if not log_path.exists():
                print(f"错误: 文件不存在 — {args.logfile}", file=sys.stderr)
                sys.exit(1)
            log_content = log_path.read_text(encoding="utf-8", errors="replace")
    else:
        # 无参数时使用 demo 模式
        print("未指定日志文件，使用 --demo 模式\n")
        log_content = DEMO_LOG

    # 分析
    analyzer = BuildLogAnalyzer(log_content)
    report = analyzer.analyze()

    # 输出报告
    print_report(report, verbose=args.verbose)

    # 返回码：有错误时返回 1
    sys.exit(1 if report["error_count"] > 0 else 0)


if __name__ == "__main__":
    main()
