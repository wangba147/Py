"""
Day 03 实用工具 — C++ 项目文件扫描器
递归扫描 C++ 项目，统计代码行数、分析文件结构、生成报告

用法:
  python cpp_project_scanner.py <项目目录>
  python cpp_project_scanner.py <项目目录> -o report.json
  python cpp_project_scanner.py --demo    # 使用示例演示

示例:
  python cpp_project_scanner.py D:/MyProject
  python cpp_project_scanner.py . -o scan_result.json --summary
"""

import sys
import io
import json
import re
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from typing import Optional

# 修复 Windows 终端 Unicode 输出问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class FileInfo:
    """单个 C++ 文件的统计信息"""
    path: str                    # 相对路径
    name: str                    # 文件名
    size_bytes: int              # 文件大小（字节）
    total_lines: int             # 总行数
    code_lines: int              # 代码行
    blank_lines: int             # 空行
    comment_lines: int           # 注释行
    includes: list[str] = field(default_factory=list)  # #include 列表
    extension: str = ""          # 后缀名

    @property
    def code_density(self) -> float:
        """代码密度 = 代码行 / 总行数"""
        return self.code_lines / self.total_lines if self.total_lines > 0 else 0.0

    @property
    def is_header(self) -> bool:
        return self.extension in (".h", ".hpp", ".hxx", ".hh")

    @property
    def is_source(self) -> bool:
        return self.extension in (".cpp", ".cc", ".cxx", ".c++")


@dataclass
class ProjectReport:
    """项目扫描完整报告"""
    project_root: str
    scan_time: str
    total_files: int
    total_lines: int
    total_code_lines: int
    total_blank_lines: int
    total_comment_lines: int
    total_size_bytes: int
    source_files: int
    header_files: int
    files: list[dict] = field(default_factory=list)
    extensions_summary: dict[str, int] = field(default_factory=dict)
    top_largest: list[dict] = field(default_factory=list)  # 最大的文件


# ============================================================
# 文件分析器
# ============================================================

class CppFileAnalyzer:
    """分析单个 C++ 文件的代码行数、注释、include"""

    # 这是 Python 支持的模式，C++ 需要 constexpr 或 static const
    SOURCE_EXTS = {".cpp", ".cc", ".cxx", ".c++"}
    HEADER_EXTS = {".h", ".hpp", ".hxx", ".hh", ".inl"}
    ALL_EXTS = SOURCE_EXTS | HEADER_EXTS

    @classmethod
    def is_cpp_file(cls, filepath: Path) -> bool:
        """判断是否是 C++ 文件"""
        return filepath.suffix.lower() in cls.ALL_EXTS

    @classmethod
    def analyze(cls, filepath: Path, root: Path) -> Optional[FileInfo]:
        """
        分析单个 C++ 文件
        返回 FileInfo，失败返回 None
        """
        # EAFP 风格：先尝试，失败再处理
        # C++ 中需要手动检查文件存在、权限等
        try:
            stat = filepath.stat()
            # 使用 with 语句自动关闭文件
            # 类似 C++ RAII，但更显式
            with open(filepath, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except PermissionError:
            # 特定异常捕获 —— 比 except: 精确得多
            return None
        except (OSError, UnicodeDecodeError) as e:
            print(f"  ⚠ 跳过 {filepath.name}: {e}", file=sys.stderr)
            return None

        code = blank = comment = 0
        includes = []
        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                blank += 1
                continue

            # 块注释处理（/* ... */）
            if in_block_comment:
                comment += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue

            if stripped.startswith("/*"):
                comment += 1
                if "*/" not in stripped:
                    in_block_comment = True
                continue

            # 单行注释
            if stripped.startswith("//"):
                comment += 1
            else:
                code += 1

            # 提取 #include 指令
            if stripped.startswith("#include"):
                includes.append(stripped)

        return FileInfo(
            path=str(filepath.relative_to(root)),
            name=filepath.name,
            size_bytes=stat.st_size,
            total_lines=len(lines),
            code_lines=code,
            blank_lines=blank,
            comment_lines=comment,
            includes=includes,
            extension=filepath.suffix.lower(),
        )


# ============================================================
# 项目扫描器
# ============================================================

class CppProjectScanner:
    """递归扫描 C++ 项目，统计所有源文件"""

    def __init__(self, root: Path):
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ValueError(f"项目目录不存在: {self.root}")  # raise 类似 throw

    def scan(self, verbose: bool = False) -> list[FileInfo]:
        """
        递归扫描所有 C++ 源文件
        返回 FileInfo 列表（按路径排序）
        """
        files = []

        # 遍历所有扩展名模式 —— rglob 递归匹配
        # C++ 中需要 std::filesystem::recursive_directory_iterator
        for ext in CppFileAnalyzer.ALL_EXTS:
            pattern = f"*{ext}"
            # rglob 的优雅在于不需要手动处理递归
            for filepath in self.root.rglob(pattern):
                # 跳过隐藏目录（.git, .vs 等）
                if self._is_hidden(filepath):
                    continue

                info = CppFileAnalyzer.analyze(filepath, self.root)
                if info:
                    files.append(info)
                    if verbose:
                        print(f"  ✓ {info.path} ({info.total_lines} 行)")

        files.sort(key=lambda f: f.path)  # lambda 类似 C++ 的 [](auto& a, auto& b)
        return files

    def generate_report(self, files: list[FileInfo]) -> ProjectReport:
        """生成完整的分析报告"""
        from datetime import datetime

        if not files:
            raise RuntimeError("没有找到 C++ 文件")

        # 按后缀分类统计
        ext_counts = defaultdict(int)
        for f in files:
            ext_counts[f.extension] += 1

        # 最大的文件（Top 10）
        largest = sorted(files, key=lambda f: f.total_lines, reverse=True)[:10]

        report = ProjectReport(
            project_root=str(self.root),
            scan_time=datetime.now().isoformat(),
            total_files=len(files),
            total_lines=sum(f.total_lines for f in files),
            total_code_lines=sum(f.code_lines for f in files),
            total_blank_lines=sum(f.blank_lines for f in files),
            total_comment_lines=sum(f.comment_lines for f in files),
            total_size_bytes=sum(f.size_bytes for f in files),
            source_files=sum(1 for f in files if f.is_source),
            header_files=sum(1 for f in files if f.is_header),
            files=[asdict(f) for f in files],
            extensions_summary=dict(ext_counts),
            top_largest=[{
                "path": f.path,
                "total_lines": f.total_lines,
                "code_lines": f.code_lines,
                "comment_lines": f.comment_lines,
                "code_density": round(f.code_density, 3),
            } for f in largest],
        )
        return report

    @staticmethod
    def _is_hidden(filepath: Path) -> bool:
        """检查路径中是否包含隐藏目录"""
        return any(part.startswith(".") for part in filepath.parts)


# ============================================================
# 报告输出
# ============================================================

def print_summary(report: ProjectReport) -> None:
    """打印可读的摘要报告"""
    size_mb = report.total_size_bytes / (1024 * 1024)

    print("\n" + "=" * 60)
    print("  C++ 项目文件扫描报告")
    print("=" * 60)
    print(f"  项目路径:      {report.project_root}")
    print(f"  扫描时间:      {report.scan_time[:19]}")
    print(f"  ─────────────────────────────────────")
    print(f"  文件总数:      {report.total_files}")
    print(f"  源文件:        {report.source_files}  (.cpp/.cc/.cxx)")
    print(f"  头文件:        {report.header_files}  (.h/.hpp/.hxx)")
    print(f"  总行数:        {report.total_lines:,}")
    print(f"  代码行:        {report.total_code_lines:,}")
    print(f"  注释行:        {report.total_comment_lines:,}")
    print(f"  空行:          {report.total_blank_lines:,}")
    print(f"  项目体积:      {size_mb:.2f} MB")
    print(f"  ─────────────────────────────────────")

    # 扩展名分布
    if report.extensions_summary:
        print(f"  扩展名分布:")
        for ext, count in sorted(report.extensions_summary.items(),
                                  key=lambda x: x[1], reverse=True):
            bar = "█" * count
            print(f"    {ext:8s} {count:4d}  {bar}")

    # 最大的文件
    if report.top_largest:
        print(f"\n  🔝 最大的 5 个文件:")
        for i, f in enumerate(report.top_largest[:5], 1):
            density_pct = f["code_density"] * 100
            print(f"    {i}. {f['path']}")
            print(f"       {f['total_lines']} 行 | "
                  f"代码: {f['code_lines']} | "
                  f"密度: {density_pct:.0f}%")

    print("=" * 60)


def create_demo_report() -> ProjectReport:
    """创建演示用的示例报告（不需要真实项目）"""
    from dataclasses import asdict
    from datetime import datetime

    demo_files = [
        FileInfo("src/main.cpp", "main.cpp", 2048, 80, 50, 10, 20,
                 ['#include <iostream>', '#include "app.h"'], ".cpp"),
        FileInfo("src/core/renderer.cpp", "renderer.cpp", 8192, 320, 220, 40, 60,
                 ['#include "renderer.h"', '#include <GL/gl.h>',
                  '#include <glm/glm.hpp>', '#include "mesh.h"'], ".cpp"),
        FileInfo("src/core/renderer.h", "renderer.h", 1024, 45, 25, 5, 15,
                 ['#include <vector>', '#include <memory>'], ".h"),
        FileInfo("src/network/socket.cpp", "socket.cpp", 4096, 150, 100, 20, 30,
                 ['#include "socket.h"', '#include <sys/socket.h>',
                  '#include <netinet/in.h>', '#include <unistd.h>',
                  '#include <cstring>'], ".cpp"),
        FileInfo("src/network/socket.h", "socket.h", 512, 30, 15, 3, 12,
                 ['#include <string>', '#include <cstdint>'], ".h"),
        FileInfo("src/utils/string_utils.cpp", "utils/string_utils.cpp", 2048, 90, 55, 10, 25,
                 ['#include "string_utils.h"', '#include <algorithm>'], ".cpp"),
        FileInfo("src/utils/string_utils.h", "utils/string_utils.h", 768, 25, 12, 3, 10,
                 ['#include <string>', '#include <vector>'], ".h"),
        FileInfo("tests/test_main.cpp", "tests/test_main.cpp", 3072, 120, 80, 15, 25,
                 ['#include <gtest/gtest.h>', '#include "app.h"'], ".cpp"),
    ]

    ext_counts = defaultdict(int)
    for f in demo_files:
        ext_counts[f.extension] += 1

    return ProjectReport(
        project_root="/path/to/demo/project",
        scan_time=datetime.now().isoformat(),
        total_files=len(demo_files),
        total_lines=sum(f.total_lines for f in demo_files),
        total_code_lines=sum(f.code_lines for f in demo_files),
        total_blank_lines=sum(f.blank_lines for f in demo_files),
        total_comment_lines=sum(f.comment_lines for f in demo_files),
        total_size_bytes=sum(f.size_bytes for f in demo_files),
        source_files=sum(1 for f in demo_files if f.is_source),
        header_files=sum(1 for f in demo_files if f.is_header),
        files=[asdict(f) for f in demo_files],
        extensions_summary=dict(ext_counts),
        top_largest=[{
            "path": f.path, "total_lines": f.total_lines,
            "code_lines": f.code_lines, "comment_lines": f.comment_lines,
            "code_density": round(f.code_density, 3),
        } for f in sorted(demo_files, key=lambda x: x.total_lines, reverse=True)[:10]],
    )


# ============================================================
# 主入口
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="C++ 项目文件扫描器 — 统计代码行数、分析文件结构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cpp_project_scanner.py .                    # 扫描当前目录
  python cpp_project_scanner.py D:\\MyProject        # 扫描指定项目
  python cpp_project_scanner.py . -o report.json     # 输出 JSON 报告
  python cpp_project_scanner.py --demo               # 查看演示
        """,
    )
    parser.add_argument(
        "project_dir", nargs="?", default=".",
        help="C++ 项目根目录（默认: 当前目录）"
    )
    parser.add_argument(
        "-o", "--output", metavar="FILE",
        help="将完整报告输出到 JSON 文件"
    )
    parser.add_argument(
        "-s", "--summary", action="store_true", default=True,
        help="打印摘要报告（默认启用）"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="详细模式：打印每个文件的分析结果"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="使用内置示例数据进行演示"
    )

    args = parser.parse_args()

    # --demo 模式：使用示例数据
    if args.demo:
        report = create_demo_report()
        print("[演示模式] 以下是模拟数据的结果：")
    else:
        # 正常扫描模式
        project_root = Path(args.project_dir).resolve()

        print(f"🔍 扫描项目: {project_root}")
        print(f"   正在搜索 C++ 文件...")

        try:
            scanner = CppProjectScanner(project_root)
        except ValueError as e:
            print(f"❌ 错误: {e}", file=sys.stderr)
            sys.exit(1)

        files = scanner.scan(verbose=args.verbose)

        if not files:
            print(f"❌ 未在 {project_root} 中找到 C++ 文件", file=sys.stderr)
            sys.exit(1)

        print(f"   找到 {len(files)} 个文件，正在分析...")

        try:
            report = scanner.generate_report(files)
        except RuntimeError as e:
            print(f"❌ 生成报告失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 打印摘要
    if args.summary:
        print_summary(report)

    # 输出 JSON 报告
    from dataclasses import asdict
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        print(f"\n📄 完整报告已保存: {output_path.resolve()}")
        print(f"   大小: {output_path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
