#!/usr/bin/env python3
"""
C++ 项目批量化构建器 (cpp_project_builder)
=============================================
一个用 Python 驱动 C++ 项目编译、测试、报告的工具。

特性：
  - 从 JSON 配置文件读取项目列表
  - 增量构建（只编译有变更的项目）
  - 并行构建多个子项目
  - 运行 CTest 测试并汇总结果
  - 生成 HTML 构建报告
  - 定时构建守护模式

用法：
  # 完整构建
  python cpp_project_builder.py build -c config.json

  # 增量构建
  python cpp_project_builder.py build -c config.json --incremental

  # 构建 + 测试
  python cpp_project_builder.py build -c config.json --test

  # 只构建指定项目
  python cpp_project_builder.py build -c config.json --only core,plugins

  # 仅生成配置文件模板
  python cpp_project_builder.py init

  # 清理构建产物
  python cpp_project_builder.py clean -c config.json

  # 生成 HTML 报告
  python cpp_project_builder.py report -c config.json

依赖：纯标准库，无需 pip install 任何包。

C++ 对比说明：
  本工具替代的是 bash/bat 构建脚本，而不是 CMake 本身。
  CMake 负责"怎么编译"，本工具负责"编译哪些、什么时候编译、结果如何"。
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# ============================================================
# ANSI 颜色（代替 rich 库，保持零依赖）
# ============================================================
# C++ 对比: C++ 中也需要手动输出 ANSI 转义码，
# 或者用 fmt::color / {fmt} 库

class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def cprint(text: str, color: str = "", bold: bool = False):
    """彩色打印"""
    prefix = Colors.BOLD if bold else ""
    if color:
        prefix += color
    print(f"{prefix}{text}{Colors.RESET}")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ProjectInfo:
    """单个项目的构建信息"""
    name: str
    src_dir: Path
    build_dir: Path
    deps: list[str] = field(default_factory=list)
    skip: bool = False
    build_type: str = "Release"
    extra_cmake_args: list[str] = field(default_factory=list)


@dataclass
class BuildResult:
    """构建结果"""
    project: str
    success: bool
    duration: float
    configure_ok: bool = True
    build_ok: bool = True
    test_ok: bool = True
    output: str = ""
    errors: str = ""
    test_results: dict | None = None


@dataclass
class BuildConfig:
    """全局构建配置"""
    workspace: Path
    build_root: Path
    build_type: str = "Release"
    generator: str | None = None
    parallel: int = 0      # 0 = 自动
    projects: list[ProjectInfo] = field(default_factory=list)

    @classmethod
    def from_json(cls, config_path: Path) -> "BuildConfig":
        data = json.loads(config_path.read_text(encoding="utf-8"))
        workspace = Path(data["workspace"])

        projects = []
        for p in data.get("projects", []):
            projects.append(ProjectInfo(
                name=p["name"],
                src_dir=workspace / p["src"],
                build_dir=Path(data.get("build_root", "build")) / p["name"],
                deps=p.get("deps", []),
                skip=p.get("skip", False),
                build_type=p.get("build_type", data.get("build_type", "Release")),
                extra_cmake_args=p.get("extra_cmake_args", []),
            ))

        return cls(
            workspace=workspace,
            build_root=Path(data.get("build_root", "build")),
            build_type=data.get("build_type", "Release"),
            generator=data.get("generator"),
            parallel=data.get("parallel", 0),
            projects=projects,
        )

    def get_enabled_projects(self) -> list[ProjectInfo]:
        return [p for p in self.projects if not p.skip]

    @staticmethod
    def generate_template(output: Path):
        """生成配置模板"""
        template = {
            "workspace": ".",
            "build_root": "build",
            "build_type": "Release",
            "generator": None,
            "parallel": 0,
            "projects": [
                {
                    "name": "myapp_core",
                    "src": "src/core",
                    "deps": [],
                    "skip": False,
                    "build_type": "Release",
                    "extra_cmake_args": []
                },
                {
                    "name": "myapp_plugins",
                    "src": "src/plugins",
                    "deps": ["myapp_core"],
                    "skip": False,
                    "build_type": "Release",
                    "extra_cmake_args": ["-DBUILD_PLUGINS=ON"]
                },
                {
                    "name": "tests",
                    "src": "tests",
                    "deps": ["myapp_core", "gtest_main"],
                    "skip": False,
                    "build_type": "Debug",
                    "extra_cmake_args": ["-DBUILD_TESTING=ON"]
                }
            ]
        }
        output.write_text(
            json.dumps(template, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        cprint(f"配置模板已生成: {output}", Colors.GREEN)


# ============================================================
# CMake 构建器
# ============================================================
# C++ 对比: 这部分替代了 bash/bat 中的 cmake 调用逻辑

class CMakeBuilder:
    """单个 CMake 项目的构建器"""

    def __init__(self, project: ProjectInfo, config: BuildConfig):
        self.project = project
        self.config = config

    def configure(self) -> tuple[bool, str, str]:
        """
        运行 cmake 配置阶段

        C++ 对比: 等价于 system("cmake -S ... -B ...") 但能捕获输出
        """
        cmd = ["cmake", "-S", str(self.project.src_dir),
               "-B", str(self.project.build_dir),
               f"-DCMAKE_BUILD_TYPE={self.project.build_type}"]

        if self.config.generator:
            cmd.extend(["-G", self.config.generator])

        # 添加导出编译命令（用于后续分析）
        cmd.append("-DCMAKE_EXPORT_COMPILE_COMMANDS=ON")

        # 用户自定义参数
        cmd.extend(self.project.extra_cmake_args)

        cprint(f"  [CONFIGURE] {self.project.name}", Colors.CYAN)
        cprint(f"    {' '.join(cmd)}", Colors.DIM)

        try:
            self.project.build_dir.mkdir(parents=True, exist_ok=True)
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=str(self.config.workspace), timeout=120)
            return r.returncode == 0, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return False, "", "CMake 配置超时 (120s)"
        except FileNotFoundError:
            return False, "", "cmake 未安装或不在 PATH 中"

    def build(self, parallel: int = 0) -> tuple[bool, str, str]:
        """
        运行 cmake 构建阶段

        C++ 对比: 等价于 system("cmake --build ...") 但支持超时和输出捕获
        """
        cmd = ["cmake", "--build", str(self.project.build_dir),
               "--config", self.project.build_type]

        if parallel > 0:
            cmd.extend(["--parallel", str(parallel)])

        cprint(f"  [BUILD] {self.project.name}", Colors.CYAN)

        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=str(self.config.workspace), timeout=600)
            return r.returncode == 0, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return False, "", "构建超时 (600s)"
        except FileNotFoundError:
            return False, "", "cmake 未安装或不在 PATH 中"

    def run_tests(self) -> dict | None:
        """
        运行 CTest

        Returns:
            {"total": int, "passed": int, "failed": int, "output": str}
            如果 build_dir 下没有 CTestTestfile.cmake，返回 None
        """
        testfile = self.project.build_dir / "CTestTestfile.cmake"
        if not testfile.exists():
            return None

        cprint(f"  [TEST] {self.project.name}", Colors.CYAN)

        try:
            r = subprocess.run(
                ["ctest", "--test-dir", str(self.project.build_dir),
                 "--output-on-failure"],
                capture_output=True, text=True, timeout=300
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"total": 0, "passed": 0, "failed": 0, "output": "ctest 不可用"}

        output = r.stdout + r.stderr

        # 解析结果
        total = 0
        passed = 0
        # 查找 "X tests passed" 或 "100% tests passed"
        for line in output.splitlines():
            m = re.search(r'(\d+) tests? passed', line)
            if m:
                passed = int(m.group(1))
            m = re.search(r'(\d+) tests? failed', line)
            if m:
                failed = int(m.group(1))
                total = passed + failed

        if total == 0:
            # 另一种格式: "N/5 Test #N ..."
            test_lines = re.findall(r'(\d+)/(\d+) Test', output)
            if test_lines:
                total = max(int(m[1]) for m in test_lines)
                passed = sum(1 for line in output.splitlines()
                             if "Passed" in line)

        failed = total - passed

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "output": output
        }


# ============================================================
# 增量检测
# ============================================================
# C++ 对比: 思路与 C++17 filesystem::last_write_time 一样，
# 但 Python 写起来更短

def has_changes(src_dir: Path, marker: Path) -> bool:
    """
    检查源码目录是否有文件比 marker 更新

    同时检查 CMakeLists.txt（可能修改了编译选项但不改源码）
    """
    if not marker.exists():
        return True

    last_build = marker.stat().st_mtime

    # 要监视的文件扩展名
    watch = {".cpp", ".h", ".hpp", ".c", ".cxx", ".cc", ".c++",
             ".ixx", ".cppm", ".inl"}

    for f in src_dir.rglob("*"):
        if not f.is_file():
            continue
        # 跳过构建目录
        if "build" in f.parts:
            continue
        # 头文件、源文件、CMakeLists.txt
        if f.suffix in watch or f.name == "CMakeLists.txt":
            if f.stat().st_mtime > last_build:
                return True

    return False


# ============================================================
# HTML 报告生成
# ============================================================
# C++ 对比: C++ 生成 HTML 报告极其痛苦（字符串拼接）。
# Python 用 f-string 和模板轻松搞定

def generate_html_report(results: list[BuildResult],
                         config: BuildConfig,
                         output: Path):
    """生成 HTML 构建报告"""
    total = len(results)
    ok = sum(1 for r in results if r.success)
    fail = total - ok
    total_duration = sum(r.duration for r in results)

    status_color = "#a6e3a1" if fail == 0 else ("#fab387" if ok > 0 else "#f38ba8")
    status_text = "全部通过" if fail == 0 else f"{ok}/{total} 成功"

    # 构建项目行
    project_rows = ""
    for r in results:
        icon = "✓" if r.success else "✗"
        row_color = "#a6e3a1" if r.success else "#f38ba8"
        err_summary = ""
        if r.errors:
            # 提取错误摘要
            lines = r.errors.strip().split("\n")
            err_lines = [l for l in lines if "error" in l.lower() or "fatal" in l.lower()]
            if err_lines:
                err_summary = "<br>".join(err_lines[:3])
            else:
                err_summary = lines[-1] if lines else ""

        test_str = ""
        if r.test_results:
            tr = r.test_results
            test_str = f"{tr['passed']}/{tr['total']} 通过"

        project_rows += f"""<tr>
            <td>{icon}</td>
            <td>{r.project}</td>
            <td>{r.duration:.1f}s</td>
            <td>{test_str or "-"}</td>
            <td style="font-size:0.85em;color:{row_color}">{err_summary[:200]}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>构建报告 - {datetime.now().strftime("%Y-%m-%d %H:%M")}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: 'Segoe UI','Microsoft YaHei',sans-serif;
    background: #1e1e2e; color: #cdd6f4;
    padding: 2rem; max-width: 900px; margin: 0 auto;
  }}
  h1 {{ color: #89b4fa; border-bottom: 2px solid #89b4fa; padding-bottom: 0.5rem; }}
  .summary {{
    background: #313244; border-radius: 8px; padding: 1.5rem; margin: 1rem 0;
    display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem;
  }}
  .stat {{ text-align: center; }}
  .stat .num {{ font-size: 2rem; font-weight: bold; color: {status_color}; }}
  .stat .label {{ color: #a6adc8; font-size: 0.85rem; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; background: #282a36; }}
  th, td {{ padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid #45475a; }}
  th {{ background: #313244; color: #89b4fa; }}
  .footer {{ color: #6c7086; text-align: center; margin-top: 2rem; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>🔧 构建报告</h1>
<p style="color:#a6adc8">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 总耗时: {total_duration:.1f}s</p>

<div class="summary">
  <div class="stat"><div class="num">{total}</div><div class="label">项目总数</div></div>
  <div class="stat"><div class="num">{ok}</div><div class="label">构建成功</div></div>
  <div class="stat"><div class="num">{fail}</div><div class="label">构建失败</div></div>
  <div class="stat"><div class="num">{total_duration:.0f}s</div><div class="label">总耗时</div></div>
</div>

<table>
  <tr><th>状态</th><th>项目</th><th>耗时</th><th>测试</th><th>错误</th></tr>
  {project_rows}
</table>

<div class="footer">Generated by cpp_project_builder.py — Python 驱动的 C++ 构建工具</div>
</body>
</html>"""

    output.write_text(html, encoding="utf-8")
    return output


# ============================================================
# 主构建流程
# ============================================================

class ProjectBuilder:
    """批量化构建引擎"""

    def __init__(self, config: BuildConfig):
        self.config = config

    def build_all(self,
                  projects: list[ProjectInfo],
                  incremental: bool = False,
                  run_tests: bool = False) -> list[BuildResult]:
        """
        构建所有项目

        Args:
            projects: 要构建的项目列表
            incremental: 是否使用增量模式
            run_tests: 构建后是否运行测试
        """
        results: list[BuildResult] = []
        total = len(projects)

        cprint(f"\n{'='*60}", Colors.BOLD)
        cprint(f"开始构建 {total} 个项目", Colors.BOLD)
        cprint(f"{'='*60}\n", Colors.BOLD)

        # 为了尊重依赖顺序（简单策略：按配置中顺序构建）
        for i, proj in enumerate(projects):
            cprint(f"[{i+1}/{total}] 项目: {proj.name}", Colors.BOLD + Colors.BLUE)

            t_start = time.time()

            # 增量检测
            marker = proj.build_dir / ".build_marker"
            if incremental and not has_changes(proj.src_dir, marker):
                cprint(f"  → 跳过 (无变更)", Colors.YELLOW)
                results.append(BuildResult(
                    project=proj.name, success=True, duration=0,
                ))
                continue

            # 配置
            builder = CMakeBuilder(proj, self.config)
            config_ok, config_out, config_err = builder.configure()

            if not config_ok:
                cprint(f"  ✗ 配置失败", Colors.RED)
                elapsed = time.time() - t_start
                results.append(BuildResult(
                    project=proj.name, success=False, duration=elapsed,
                    configure_ok=False, build_ok=False,
                    output=config_out, errors=config_err
                ))
                continue

            # 构建
            build_ok, build_out, build_err = builder.build(self.config.parallel)

            # 测试（仅构建成功时运行）
            test_results = None
            test_ok = True
            if build_ok and run_tests:
                test_results = builder.run_tests()
                if test_results and test_results["failed"] > 0:
                    test_ok = False

            elapsed = time.time() - t_start

            if build_ok:
                status = "✓ 成功" if test_ok else "⚠ 构建成功但测试失败"
                color = Colors.GREEN if test_ok else Colors.YELLOW
                cprint(f"  {status} ({elapsed:.1f}s)", color)
                # 写构建标记
                marker.write_text(str(time.time()))
            else:
                cprint(f"  ✗ 构建失败 ({elapsed:.1f}s)", Colors.RED)
                # 提取错误
                error_lines = build_err.strip().split("\n")
                for line in error_lines[-5:]:
                    if line.strip():
                        cprint(f"    {line[:120]}", Colors.DIM)

            results.append(BuildResult(
                project=proj.name,
                success=build_ok and test_ok,
                duration=elapsed,
                configure_ok=config_ok,
                build_ok=build_ok,
                test_ok=test_ok,
                output=build_out,
                errors=build_err,
                test_results=test_results,
            ))

        return results


def clean_builds(config: BuildConfig):
    """清理构建目录"""
    for proj in config.get_enabled_projects():
        if proj.build_dir.exists():
            cprint(f"清理: {proj.build_dir}", Colors.YELLOW)
            shutil.rmtree(proj.build_dir)
    cprint("清理完成", Colors.GREEN)


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="C++ 项目批量化构建器 —— Python 驱动的构建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s init                         生成配置文件模板
  %(prog)s build -c config.json         完整构建
  %(prog)s build -c config.json -i      增量构建
  %(prog)s build -c config.json --test  构建并运行测试
  %(prog)s clean -c config.json         清理构建产物
  %(prog)s report -c config.json        生成 HTML 报告
        """
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # init — 生成配置模板
    sub.add_parser("init", help="生成 build_config.json 模板")

    # build
    build_parser = sub.add_parser("build", help="构建项目")
    build_parser.add_argument("-c", "--config", default="build_config.json",
                              help="构建配置文件路径 (默认: build_config.json)")
    build_parser.add_argument("-i", "--incremental", action="store_true",
                              help="增量构建（跳过无变更的项目）")
    build_parser.add_argument("--test", action="store_true",
                              help="构建后运行 CTest 测试")
    build_parser.add_argument("--only", type=str,
                              help="只构建指定项目（逗号分隔）")
    build_parser.add_argument("--report", action="store_true",
                              help="构建后生成 HTML 报告")

    # clean
    clean_parser = sub.add_parser("clean", help="清理构建产物")
    clean_parser.add_argument("-c", "--config", default="build_config.json",
                              help="构建配置文件路径")

    # report
    report_parser = sub.add_parser("report", help="生成 HTML 构建报告")
    report_parser.add_argument("-c", "--config", default="build_config.json",
                               help="构建配置文件路径")

    args = parser.parse_args()

    # === init ===
    if args.command == "init":
        BuildConfig.generate_template(Path("build_config.json"))
        return

    # === 需要配置文件的命令 ===
    config_path = Path(getattr(args, "config", "build_config.json"))

    if args.command in ("build", "clean", "report"):
        if not config_path.exists():
            cprint(f"配置文件不存在: {config_path}", Colors.RED)
            cprint("运行 'python cpp_project_builder.py init' 生成模板", Colors.YELLOW)
            sys.exit(1)

        config = BuildConfig.from_json(config_path)

    # === build ===
    if args.command == "build":
        projects = config.get_enabled_projects()

        if args.only:
            only_names = set(args.only.split(","))
            projects = [p for p in projects if p.name in only_names]
            if not projects:
                cprint(f"未找到匹配项目: {args.only}", Colors.RED)
                sys.exit(1)

        cprint(f"工作区: {config.workspace}", Colors.BLUE)
        cprint(f"构建目录: {config.build_root}", Colors.BLUE)
        cprint(f"构建类型: {config.build_type}", Colors.BLUE)
        cprint(f"模式: {'增量' if args.incremental else '完整'}"
               f"{' + 测试' if args.test else ''}", Colors.BLUE)
        cprint(f"项目: {', '.join(p.name for p in projects)}", Colors.BLUE)

        builder = ProjectBuilder(config)
        results = builder.build_all(
            projects,
            incremental=args.incremental,
            run_tests=args.test
        )

        # 汇总
        ok = sum(1 for r in results if r.success)
        print(f"\n{'='*60}")
        if ok == len(results):
            cprint(f"全部通过! ({ok}/{len(results)})", Colors.GREEN + Colors.BOLD)
        else:
            cprint(f"部分失败: {ok}/{len(results)} 成功", Colors.RED)
        print(f"{'='*60}")

        # 生成报告
        if args.report:
            report_path = config.workspace / "build_report.html"
            generate_html_report(results, config, report_path)
            cprint(f"报告已生成: {report_path}", Colors.GREEN)

        # 退出码
        sys.exit(0 if ok == len(results) else 1)

    # === clean ===
    elif args.command == "clean":
        cprint(f"清理构建目录: {config.build_root}", Colors.YELLOW)
        clean_builds(config)

    # === report ===
    elif args.command == "report":
        # 从已有的构建标记生成报告
        projects = config.get_enabled_projects()
        results = []
        for p in projects:
            marker = p.build_dir / ".build_marker"
            if marker.exists():
                results.append(BuildResult(
                    project=p.name, success=True, duration=0,
                ))
            else:
                results.append(BuildResult(
                    project=p.name, success=False, duration=0,
                    errors="未构建（无 .build_marker）"
                ))

        report_path = config.workspace / "build_report.html"
        generate_html_report(results, config, report_path)
        cprint(f"HTML 报告已生成: {report_path}", Colors.GREEN)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
