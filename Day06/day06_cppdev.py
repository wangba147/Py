"""
Day 06 实用工具: cpp_log_analyzer.py
====================================
C++ 项目构建日志分析器 —— 用 Python 正则 + 命令行工具,
把 GCC/Clang/MSVC 的编译错误整理成易读报告。

功能:
  - 解析 GCC/Clang 风格的编译错误
  - 解析 MSVC 风格的编译错误
  - 按文件分组、统计 error/warning 数量
  - 生成 Markdown 报告
  - 支持从文件或 stdin 读取

用法:
  python cpp_log_analyzer.py build.log
  python cpp_log_analyzer.py build.log --format md --output report.md
  g++ main.cpp 2>&1 | python cpp_log_analyzer.py -
"""
import argparse
import re
import sys
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


# ============================================================
# 数据结构
# ============================================================
@dataclass
class CompileIssue:
    file: str
    line: int
    col: int | None
    severity: str   # "error" | "warning" | "note"
    message: str
    compiler: str   # "gcc" | "clang" | "msvc" | "unknown"


@dataclass
class Report:
    issues: list[CompileIssue] = field(default_factory=list)
    compiler: str = "unknown"

    @property
    def errors(self) -> list[CompileIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[CompileIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def by_file(self) -> dict[str, list[CompileIssue]]:
        d: dict[str, list[CompileIssue]] = defaultdict(list)
        for i in self.issues:
            d[i.file].append(i)
        return d

    def file_stats(self) -> list[tuple[str, int, int]]:
        """每个文件的 error/warning 数, 按 error 数倒序."""
        d = self.by_file()
        stats = []
        for f, items in d.items():
            e = sum(1 for i in items if i.severity == "error")
            w = sum(1 for i in items if i.severity == "warning")
            stats.append((f, e, w))
        return sorted(stats, key=lambda x: (-x[1], -x[2], x[0]))


# ============================================================
# 解析器: GCC / Clang
# ============================================================
# C++ 对比:
#   std::regex gcc_re(R"(^([\w./\\-]+):(\d+):(\d+):\s*
#       (error|warning|note):\s*(.*)$)");
#   std::smatch m;
#   if (std::regex_search(line, m, gcc_re,
#       std::regex::multiline)) { ... }
#
# Python 优势: 命名分组让代码自解释
GCC_RE = re.compile(
    r"""
    ^(?P<file>[\w./\\-]+):(?P<line>\d+):(?P<col>\d+):\s*
    (?P<severity>fatal\s+error|error|warning|note):\s*
    (?P<msg>.*?)$
    """,
    re.VERBOSE | re.MULTILINE,
)


def parse_gcc(log: str) -> Iterator[CompileIssue]:
    for m in GCC_RE.finditer(log):
        d = m.groupdict()
        sev = d["severity"].replace("fatal ", "")  # "fatal error" -> "error"
        yield CompileIssue(
            file=d["file"],
            line=int(d["line"]),
            col=int(d["col"]),
            severity=sev,
            message=d["msg"].strip(),
            compiler="gcc",
        )


# ============================================================
# 解析器: MSVC
# ============================================================
# MSVC 格式:  file.cpp(line,col): error C2065: 'foo': undeclared identifier
#           或  file.cpp(line): error C2065: ...
MSVC_RE = re.compile(
    r"""
    ^(?P<file>[^()\n]+?)\((?P<line>\d+)(?:,(?P<col>\d+))?\)\s*:\s*
    (?P<severity>fatal\s+error|error|warning|note)\s+
    (?P<code>[A-Z]\d+)\s*:\s*
    (?P<msg>.*?)$
    """,
    re.VERBOSE | re.MULTILINE,
)


def parse_msvc(log: str) -> Iterator[CompileIssue]:
    for m in MSVC_RE.finditer(log):
        d = m.groupdict()
        sev = d["severity"].replace("fatal ", "")
        yield CompileIssue(
            file=d["file"].strip(),
            line=int(d["line"]),
            col=int(d["col"]) if d["col"] else None,
            severity=sev,
            message=f"[{d['code']}] {d['msg'].strip()}",
            compiler="msvc",
        )


# ============================================================
# 解析器: CMake / Make 错误
# ============================================================
# 示例:
#   make: *** [Makefile:12: main.o] Error 1
MAKE_ERROR_RE = re.compile(
    r"^make(?:\[\d+\])?:\s*\*\*\*\s*\[(?P<target>[^]]+)]\s*Error\s*(?P<code>\d+)",
    re.MULTILINE,
)


def parse_make_errors(log: str) -> list[tuple[str, int]]:
    """提取 make 层面的构建失败信息."""
    return [
        (m.group("target"), int(m.group("code")))
        for m in MAKE_ERROR_RE.finditer(log)
    ]


# ============================================================
# 主解析函数: 自动识别格式
# ============================================================
def parse_log(log: str) -> Report:
    # 优先尝试 MSVC (因为 GCC 正则不会匹配 MSVC)
    msvc_issues = list(parse_msvc(log))
    if msvc_issues:
        return Report(issues=msvc_issues, compiler="msvc")

    gcc_issues = list(parse_gcc(log))
    if gcc_issues:
        return Report(issues=gcc_issues, compiler="gcc")

    return Report(issues=[], compiler="unknown")


# ============================================================
# 报告输出
# ============================================================
def print_text_report(report: Report) -> None:
    """控制台友好输出."""
    print("=" * 70)
    print(f"  编译日志分析报告  |  编译器: {report.compiler.upper()}")
    print("=" * 70)
    print(f"  总计: {len(report.errors)} errors, {len(report.warnings)} warnings")
    print()

    if not report.issues:
        print("  [OK] 没有发现编译错误 🎉")
        return

    # 按文件分组展示
    print("─" * 70)
    print("  按文件统计 (按 error 数倒序):")
    print("─" * 70)
    print(f"  {'文件':<40} {'error':>6} {'warning':>8}")
    for f, e, w in report.file_stats()[:20]:
        f_display = f if len(f) <= 40 else "..." + f[-37:]
        print(f"  {f_display:<40} {e:>6} {w:>8}")

    # 详细错误
    if report.errors:
        print()
        print("─" * 70)
        print("  错误详情 (最多显示 20 条):")
        print("─" * 70)
        for i, issue in enumerate(report.errors[:20], 1):
            loc = f"{issue.file}:{issue.line}"
            if issue.col:
                loc += f":{issue.col}"
            print(f"  {i:3}. {loc}")
            print(f"       {issue.message[:100]}")

    # make 错误 (如果有)
    make_errors = parse_make_errors(getattr(report, "_raw", ""))
    if make_errors:
        print()
        print("─" * 70)
        print("  Make 构建失败:")
        print("─" * 70)
        for target, code in make_errors:
            print(f"  [Error {code}] target: {target}")


def print_markdown_report(report: Report, raw_log: str) -> str:
    """生成 Markdown 报告."""
    lines = []
    lines.append("# 编译日志分析报告\n")
    lines.append(f"- **编译器**: `{report.compiler}`")
    lines.append(f"- **错误数**: {len(report.errors)}")
    lines.append(f"- **警告数**: {len(report.warnings)}")
    lines.append("")

    if not report.issues:
        lines.append("✅ 没有发现编译错误\n")
        return "\n".join(lines)

    lines.append("## 按文件统计\n")
    lines.append("| 文件 | Error | Warning |")
    lines.append("|------|------:|--------:|")
    for f, e, w in report.file_stats():
        lines.append(f"| `{f}` | {e} | {w} |")
    lines.append("")

    if report.errors:
        lines.append("## 错误详情\n")
        for i, issue in enumerate(report.errors, 1):
            loc = f"{issue.file}:{issue.line}"
            if issue.col:
                loc += f":{issue.col}"
            lines.append(f"### {i}. {loc}\n")
            lines.append(f"```\n{issue.message}\n```\n")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(
        description="C++ 编译日志分析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "logfile",
        help="日志文件路径, - 表示从 stdin 读取",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "md", "json"],
        default="text",
        help="输出格式 (默认 text)",
    )
    parser.add_argument(
        "--output", "-o",
        help="输出到文件, 不指定则打印到 stdout",
    )
    parser.add_argument(
        "--top", "-n",
        type=int,
        default=10,
        help="显示前 N 个错误文件 (默认 10)",
    )
    args = parser.parse_args()

    # 读取日志
    if args.logfile == "-":
        log = sys.stdin.read()
    else:
        log = Path(args.logfile).read_text(encoding="utf-8", errors="replace")

    # 解析
    report = parse_log(log)
    report._raw = log  # 暂存原始日志,供 make 错误解析使用

    # 输出
    if args.format == "text":
        output = None
        print_text_report(report)
    elif args.format == "md":
        output = print_markdown_report(report, log)
        if output:
            print(output)
    else:  # json
        import json
        output = json.dumps(
            {
                "compiler": report.compiler,
                "errors": len(report.errors),
                "warnings": len(report.warnings),
                "issues": [
                    {
                        "file": i.file,
                        "line": i.line,
                        "col": i.col,
                        "severity": i.severity,
                        "message": i.message,
                    }
                    for i in report.issues
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        print(output)

    if args.output and output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"\n报告已写入: {args.output}")

    return 0 if not report.errors else 1


if __name__ == "__main__":
    sys.exit(main())
