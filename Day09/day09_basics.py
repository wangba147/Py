"""
Day 09: C++ 项目自动化 —— CMake 辅助 & 批量编译
======================================================
本脚本覆盖：
  1. pathlib 文件系统操作
  2. CMakeLists.txt 解析
  3. CMakeLists.txt 自动生成
  4. subprocess 批量构建
  5. 增量构建检测
  6. JSON 配置驱动
  7. 代码模板生成
  8. 测试结果解析

每个知识点附带 C++ 对比注释，帮助 C++ 开发者快速理解。
"""

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from textwrap import dedent

# ============================================================
# 1. pathlib 文件系统操作
# ============================================================
# C++ 对比: C++17 std::filesystem::path / recursive_directory_iterator
# Python 的 Path 对象是不可变的，操作返回新 Path（类似 C++ filesystem::path）

def demo_pathlib():
    print("=" * 60)
    print("1. pathlib 文件系统操作")
    print("=" * 60)

    # 获取脚本所在目录
    here = Path(__file__).resolve().parent  # C++: fs::path exe = fs::canonical(argv[0]);
    print(f"脚本目录: {here}")
    print(f"父目录:   {here.parent}")

    # 路径拼接 (C++: p / "subdir" / "file.cpp")
    src = here / "src"
    print(f"源码目录: {src} (exists={src.exists()})")

    # 创建目录
    test_dir = here / "_test_output"
    test_dir.mkdir(parents=True, exist_ok=True)  # C++: fs::create_directories(test_dir);
    print(f"创建目录: {test_dir}")

    # 创建一些测试文件（模拟 C++ 项目结构）
    (test_dir / "src" / "core").mkdir(parents=True, exist_ok=True)
    (test_dir / "include" / "core").mkdir(parents=True, exist_ok=True)
    (test_dir / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.16)\n")
    (test_dir / "src" / "main.cpp").write_text("#include <iostream>\nint main() { return 0; }\n")
    (test_dir / "src" / "core" / "engine.cpp").write_text("// engine impl\n")
    (test_dir / "include" / "core" / "engine.h").write_text("#pragma once\n// engine header\n")

    # rglob 递归查找 (C++: recursive_directory_iterator)
    print("\n--- 所有 .cpp 文件 (rglob) ---")
    for f in sorted(test_dir.rglob("*.cpp")):
        rel = f.relative_to(test_dir)  # C++: fs::relative(p, base)
        print(f"  {rel}")

    # glob 单层查找
    print("\n--- 顶层 .h 文件 (glob) ---")
    include_dir = test_dir / "include"
    for f in sorted(include_dir.rglob("*.h")):
        print(f"  {f.relative_to(test_dir)}")

    # 路径属性 (C++: p.filename(), p.stem(), p.extension())
    cpp_file = test_dir / "src" / "main.cpp"
    print(f"\n路径分析: {cpp_file}")
    print(f"  name:   {cpp_file.name}")       # C++: cpp_file.filename()
    print(f"  stem:   {cpp_file.stem}")       # C++: cpp_file.stem()
    print(f"  suffix: {cpp_file.suffix}")     # C++: cpp_file.extension()
    print(f"  parent: {cpp_file.parent}")     # C++: cpp_file.parent_path()

    return test_dir


# ============================================================
# 2. CMakeLists.txt 解析
# ============================================================
# C++ 对比: 用 C++ 写这种文本解析比 Python 冗长 3-5 倍
# Python 的正则 + 字符串处理让解析变得简单

@dataclass
class CMakeTarget:
    """CMake 目标信息"""
    name: str
    target_type: str          # "executable" | "library"
    sources: list = field(default_factory=list)
    links: list = field(default_factory=list)
    includes: list = field(default_factory=list)


def parse_cmake(cmake_path: Path) -> list[CMakeTarget]:
    """
    解析 CMakeLists.txt，提取 target 信息

    支持的命令：
    - add_executable / add_library
    - target_link_libraries
    - set() 变量定义（用于替换 ${VAR}）

    C++ 对比:
      C++ 需要手写状态机或 tokenizer，还要处理文件 IO 错误。
      Python 的 read_text + re 一行搞定。
    """
    if not cmake_path.exists():
        print(f"[WARN] {cmake_path} 不存在")
        return []

    content = cmake_path.read_text(encoding="utf-8")

    # --- Step 1: 收集 set() 变量定义 ---
    variables: dict[str, str] = {}
    for m in re.finditer(r'set\s*\(\s*(\w+)\s+(.+?)\s*\)', content, re.IGNORECASE):
        variables[m.group(1)] = m.group(2).strip()

    # --- Step 2: 变量替换函数 ---
    def subst(s: str) -> str:
        """将 ${VAR} 替换为 set() 中定义的值"""
        def repl(m):
            return variables.get(m.group(1), m.group(0))
        return re.sub(r'\$\{(\w+)\}', repl, s)

    # --- Step 3: 匹配 add_executable / add_library ---
    targets = []
    pattern = r'(add_executable|add_library)\s*\(\s*(\w+)\s+(.*?)\)'
    for m in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
        cmd, name, src_block = m.group(1), m.group(2), m.group(3)
        sources = [s for s in re.split(r'\s+', src_block.strip()) if s]
        target_type = "executable" if "executable" in cmd.lower() else "library"
        targets.append(CMakeTarget(name=name, target_type=target_type, sources=sources))

    # --- Step 4: 匹配 target_link_libraries ---
    link_re = r'target_link_libraries\s*\(\s*(\w+)\s+(.*?)\)'
    for m in re.finditer(link_re, content, re.DOTALL | re.IGNORECASE):
        target_name, libs_str = m.group(1), m.group(2)
        libs = [l.strip() for l in re.split(r'\s+', libs_str.strip()) if l]
        # 过滤关键字
        keywords = {"PUBLIC", "PRIVATE", "INTERFACE"}
        libs = [l for l in libs if l.upper() not in keywords]
        for t in targets:
            if t.name == target_name:
                t.links = libs

    return targets


def demo_cmake_parse(test_dir: Path):
    print("\n" + "=" * 60)
    print("2. CMakeLists.txt 解析")
    print("=" * 60)

    # 创建一个更真实的 CMakeLists.txt
    cmake_content = dedent("""\
    cmake_minimum_required(VERSION 3.16)
    project(MyApp LANGUAGES CXX)

    set(CMAKE_CXX_STANDARD 17)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    set(MY_SOURCES src/main.cpp src/core/engine.cpp)

    find_package(fmt REQUIRED)
    find_package(spdlog REQUIRED)

    add_executable(MyApp ${MY_SOURCES})

    add_library(MyLib src/core/utils.cpp)

    target_link_libraries(MyApp PRIVATE MyLib fmt::fmt spdlog::spdlog)
    target_link_libraries(MyLib PUBLIC fmt::fmt)
    """)
    cmake_path = test_dir / "CMakeLists.txt"
    cmake_path.write_text(cmake_content)
    print(f"创建示例 CMakeLists.txt: {cmake_path}")

    # 解析
    targets = parse_cmake(cmake_path)
    for t in targets:
        print(f"\n[{t.target_type}] {t.name}")
        print(f"  Sources: {t.sources}")
        print(f"  Links:   {t.links}")

    # --- 补充：读取 compile_commands.json（如果存在）---
    # C++ 对比: 更好的方式是让 CMake 自己输出 compile_commands.json
    # cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    # Python 直接 json.loads() 即可读取，C++ 需要引入第三方 JSON 库
    cc_path = test_dir / "build" / "compile_commands.json"
    if cc_path.exists():
        print(f"\n--- compile_commands.json ---")
        data = json.loads(cc_path.read_text())
        print(f"共 {len(data)} 个编译单元")
        for entry in data[:2]:
            print(f"  {entry.get('file', '?')}: {entry.get('command', '')[:80]}...")


# ============================================================
# 3. CMakeLists.txt 自动生成
# ============================================================
# C++ 对比: 这是脚本语言的核心优势——模板生成。
# C++ 中通常只能在 CMake 里用 FILE(GLOB ...)，不够灵活。

def generate_cmake(project_name: str,
                   src_dir: Path,
                   output: Path,
                   cpp_std: str = "17",
                   deps: list[str] | None = None):
    """
    根据源文件目录自动生成 CMakeLists.txt

    Args:
        project_name: 项目名称
        src_dir: 源码目录（含 .cpp, .h, .hpp）
        output: 输出 CMakeLists.txt 路径
        cpp_std: C++ 标准版本
        deps: 依赖库列表（如 ["fmt::fmt", "spdlog::spdlog"]）

    Returns:
        (cpp_count, h_count) 源文件和头文件数量
    """
    if deps is None:
        deps = []

    # 扫描源文件（只找 .cpp/.cc/.cxx）
    cpp_files = sorted(src_dir.rglob("*.cpp"))
    if not cpp_files:
        cpp_files = sorted(src_dir.rglob("*.cc"))

    # 扫描头文件
    h_files = sorted(src_dir.rglob("*.h")) + sorted(src_dir.rglob("*.hpp"))

    # 生成源文件列表字符串
    sources_str = "\n    ".join(
        f'"${{CMAKE_CURRENT_SOURCE_DIR}}/{f.relative_to(src_dir.parent)}"'
        for f in cpp_files
    )

    # 找包含目录
    include_dirs = sorted(set(
        str(d.relative_to(src_dir.parent))
        for f in h_files
        for d in [f.parent]
    ))
    includes_str = "\n    ".join(
        f'"${{CMAKE_CURRENT_SOURCE_DIR}}/{d}"' for d in include_dirs
    )

    # find_package 块
    find_packages = ""
    for dep in deps:
        pkg = dep.split("::")[0] if "::" in dep else dep
        find_packages += f"find_package({pkg} REQUIRED)\n"

    # target_link_libraries 块
    link_block = ""
    if deps:
        links_str = "\n        ".join(deps)
        link_block = dedent(f"""\
        target_link_libraries({project_name} PRIVATE
                {links_str}
        )""")

    # 组装完整的 CMakeLists.txt
    cmake_content = dedent(f"""\
    # Auto-generated by day09_basics.py
    # Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}

    cmake_minimum_required(VERSION 3.16)
    project({project_name} LANGUAGES CXX)

    set(CMAKE_CXX_STANDARD {cpp_std})
    set(CMAKE_CXX_STANDARD_REQUIRED ON)

    {find_packages}
    add_executable({project_name}
        {sources_str}
    )

    target_include_directories({project_name} PRIVATE
        {includes_str}
    )
    {link_block}
    """)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(cmake_content, encoding="utf-8")
    return len(cpp_files), len(h_files)


def demo_cmake_generate(test_dir: Path):
    print("\n" + "=" * 60)
    print("3. CMakeLists.txt 自动生成")
    print("=" * 60)

    cpp_count, h_count = generate_cmake(
        project_name="MyGeneratedApp",
        src_dir=test_dir / "src",
        output=test_dir / "generated" / "CMakeLists.txt",
        cpp_std="20",
        deps=["fmt::fmt", "spdlog::spdlog"]
    )
    print(f"生成完成: {cpp_count} 个 .cpp, {h_count} 个 .h")

    # 显示生成的内容
    gen_cmake = test_dir / "generated" / "CMakeLists.txt"
    print(f"\n--- 生成的 CMakeLists.txt ---")
    print(gen_cmake.read_text())


# ============================================================
# 4. subprocess 批量构建（模拟）
# ============================================================
# C++ 对比: C++ 用 system() 或 fork+exec，操作繁琐且不可移植。
# Python 的 subprocess.run() 一行搞定，自动处理 stdout/stderr/returncode。

@dataclass
class BuildResult:
    project: str
    success: bool
    duration: float
    output: str = ""
    errors: str = ""


def run_command(cmd: list[str],
                description: str = "",
                timeout: int = 30) -> tuple[bool, str, str]:
    """
    安全地运行一个命令，返回 (success, stdout, stderr)

    C++ 对比:
      C++ 需要: popen/pclose (POSIX) 或 CreateProcess (Windows)
      Python:  subprocess.run() 跨平台一行搞定
    """
    print(f"  → {description}")
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return r.returncode == 0, r.stdout, r.stderr
    except FileNotFoundError:
        return False, "", f"命令未找到: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "", f"超时 ({timeout}s): {' '.join(cmd)}"


def simulate_batch_build(test_dir: Path):
    """
    模拟批量构建流程（不会真的运行 cmake，只是演示流程）

    真实项目中，把 simulate=True 去掉即可。
    C++ 对比: 并行构建用 std::async + future，但线程管理和错误处理比 Python 复杂得多。
    """
    print("\n" + "=" * 60)
    print("4. 批量构建流程演示")
    print("=" * 60)

    # 定义"项目"（实际上不存在，只演示流程）
    projects = {
        "core": test_dir / "src" / "core",
        "net": test_dir / "src",
        "gui": test_dir,
    }

    results: list[BuildResult] = []

    max_workers = min(3, len(projects))  # 不要超过 CPU 核心数

    # C++ 对比: C++ 中类似 std::async + std::future
    # Python 的 ThreadPoolExecutor 更简洁
    # 注意：对于 CPU 密集型编译任务，用 ProcessPoolExecutor 更好
    # 这里用 ThreadPoolExecutor 是因为 subprocess 本身会 fork 进程
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}

        for name, src_dir in projects.items():
            # 模拟构建命令（真实项目中去掉 echo）
            # cmd = ["cmake", "-S", str(src_dir), "-B", str(build_dir)]
            cmd = ["echo", f"[模拟] 正在构建项目: {name} (src={src_dir})"]
            future = pool.submit(run_command, cmd, f"构建 {name}", timeout=5)
            futures[future] = name

        for future in as_completed(futures):
            name = futures[future]
            t0 = time.time()
            ok, out, err = future.result()
            elapsed = time.time() - t0
            results.append(BuildResult(name, ok, elapsed, out, err))
            status = "OK" if ok else "FAILED"
            print(f"  [{status}] {name} ({elapsed:.2f}s)")

    # 汇总报告
    ok_count = sum(1 for r in results if r.success)
    print(f"\n构建完成: {ok_count}/{len(results)} 成功")

    if ok_count < len(results):
        print("失败项目:")
        for r in results:
            if not r.success:
                print(f"  × {r.project}: {r.errors[:100]}")

    return results


# ============================================================
# 5. 增量构建检测
# ============================================================
# C++ 对比: C++17 也有 filesystem::last_write_time()，思路一样
# Python 的优势是写这类检查脚本更简短

def should_rebuild(src_dir: Path, build_marker: Path) -> bool:
    """
    判断是否需要重新构建

    检查 src_dir 下是否有任何源文件比 build_marker 更新
    """
    if not build_marker.exists():
        return True  # 从未构建过

    last_build = build_marker.stat().st_mtime

    # 检查的扩展名
    watch_extensions = (".cpp", ".h", ".hpp", ".c", ".cxx", ".cc", "CMakeLists.txt")

    for ext in watch_extensions:
        if ext == "CMakeLists.txt":
            # 特殊处理：CMakeLists.txt 没有点在前面
            for cmake_file in src_dir.rglob(ext):
                if cmake_file.stat().st_mtime > last_build:
                    print(f"  → 检测到变更: {cmake_file.name}")
                    return True
        else:
            for f in src_dir.rglob(f"*{ext}"):
                if f.stat().st_mtime > last_build:
                    print(f"  → 检测到变更: {f.relative_to(src_dir)}")
                    return True

    print("  → 无变更，跳过构建")
    return False


def demo_incremental_build(test_dir: Path):
    print("\n" + "=" * 60)
    print("5. 增量构建检测")
    print("=" * 60)

    marker = test_dir / ".last_build"

    print("第一次检查（无 marker）:")
    if should_rebuild(test_dir, marker):
        print("  需要构建 → 模拟构建...")
        # 构建完成后 touch marker
        marker.write_text(str(time.time()))

    print("\n第二次检查（有 marker）:")
    if not should_rebuild(test_dir, marker):
        print("  跳过构建 ✓")

    print("\n模拟修改源文件后:")
    # 修改一个文件
    (test_dir / "src" / "main.cpp").write_text("// modified\n")
    # 等待一下确保时间戳变化
    time.sleep(0.1)
    if should_rebuild(test_dir, marker):
        print("  检测到变更，需要重新构建 → 模拟构建...")
        marker.write_text(str(time.time()))


# ============================================================
# 6. JSON 构建配置
# ============================================================
# C++ 对比: C++ 没有标准 JSON 库（要到 C++26），需要引入 nlohmann/json 等第三方库
# Python 的 json 是标准库，开箱即用

@dataclass
class BuildConfig:
    """从 JSON 文件加载构建配置"""
    workspace: Path
    build_root: Path
    build_type: str = "Release"
    generator: str | None = None
    projects: list = field(default_factory=list)

    @classmethod
    def from_json(cls, config_path: Path) -> "BuildConfig":
        data = json.loads(config_path.read_text())
        return cls(
            workspace=Path(data["workspace"]),
            build_root=Path(data["build_root"]),
            build_type=data.get("build_type", "Release"),
            generator=data.get("generator"),
            projects=data.get("projects", [])
        )

    def get_enabled_projects(self) -> dict[str, Path]:
        """返回 {项目名: 源码路径}，跳过 skip=true 的项目"""
        return {
            p["name"]: self.workspace / p["src"]
            for p in self.projects
            if not p.get("skip", False)
        }


def demo_build_config(test_dir: Path):
    print("\n" + "=" * 60)
    print("6. JSON 构建配置")
    print("=" * 60)

    # 生成示例配置
    config_json = {
        "workspace": str(test_dir),
        "build_root": "build",
        "build_type": "Release",
        "generator": "Visual Studio 17 2022",
        "projects": [
            {"name": "myapp_core",   "src": "src/core", "deps": ["fmt", "spdlog"]},
            {"name": "myapp_plugins", "src": "src",      "deps": ["myapp_core"], "skip": True},
            {"name": "tests",         "src": "src",      "deps": ["gtest_main"]},
        ]
    }
    config_path = test_dir / "build_config.json"
    config_path.write_text(json.dumps(config_json, indent=2, ensure_ascii=False))
    print(f"生成配置文件: {config_path}")

    # 加载配置
    config = BuildConfig.from_json(config_path)
    print(f"工作区:   {config.workspace}")
    print(f"构建类型: {config.build_type}")
    print(f"生成器:   {config.generator or '(默认)'}")

    projects = config.get_enabled_projects()
    print(f"\n启用项目 ({len(projects)}):")
    for name, path in projects.items():
        src_files = list(path.rglob("*.cpp")) if path.exists() else []
        print(f"  {name}: {path} ({len(src_files)} .cpp)")

    print("\n被跳过的项目:")
    for p in config.projects:
        if p.get("skip"):
            print(f"  {p['name']} (skip=true)")


# ============================================================
# 7. 代码模板生成
# ============================================================
# C++ 对比: C++ 通常用 constexpr / 模板元编程生成代码（编译期）
# Python 用模板引擎生成源代码文件（脚本期），两者互补

def demo_code_generation(test_dir: Path):
    print("\n" + "=" * 60)
    print("7. 代码模板生成 (string.Template)")
    print("=" * 60)

    # C++ 类头文件模板
    # C++ 对比: 这就像 IDE 的 "New Class" 向导，但可以批量生成
    header_template = Template(dedent("""\
    /**
     * @file ${filename}.h
     * @brief ${brief}
     * Auto-generated — DO NOT EDIT manually.
     */
    #pragma once

    #include <${main_include}>

    namespace ${namespace} {

    class ${classname} {
    public:
        ${classname}() = default;
        virtual ~${classname}() = default;

        // --- 接口 ---

    ${methods}

    private:
        // --- 数据 ---

    ${members}
    };

    } // namespace ${namespace}
    """))

    # 定义要生成的类
    classes_to_generate = [
        {
            "filename": "ILogger",
            "classname": "ILogger",
            "brief": "日志系统抽象接口",
            "namespace": "myapp",
            "main_include": "string_view",
            "methods": "    virtual void log(std::string_view msg) = 0;\n"
                       "    virtual void error(std::string_view msg) = 0;",
            "members": "    // 纯接口，无数据成员"
        },
        {
            "filename": "IConfig",
            "classname": "IConfig",
            "brief": "配置系统接口",
            "namespace": "myapp",
            "main_include": "string",
            "methods": "    virtual std::string get(std::string_view key) const = 0;\n"
                       "    virtual void set(std::string_view key, std::string_view value) = 0;",
            "members": "    // 纯接口，无数据成员"
        },
    ]

    gen_dir = test_dir / "generated" / "include"
    gen_dir.mkdir(parents=True, exist_ok=True)

    for cls in classes_to_generate:
        content = header_template.substitute(**cls)
        output = gen_dir / f"{cls['filename']}.h"
        output.write_text(content, encoding="utf-8")
        print(f"生成: {output}")

    # 预览一个文件
    print(f"\n--- 预览 {classes_to_generate[0]['filename']}.h ---")
    preview = (gen_dir / f"{classes_to_generate[0]['filename']}.h").read_text()
    print(preview)


# ============================================================
# 8. 测试结果解析
# ============================================================
# C++ 对比: 如果你用 CTest 管理测试，Python 可以解析 CTest 输出或
# JUnit XML 报告，这在 CI/CD 中非常有用。

def demo_test_runner(test_dir: Path):
    print("\n" + "=" * 60)
    print("8. 测试运行与结果解析（模拟）")
    print("=" * 60)

    # 模拟 CTest 输出
    mock_ctest_output = dedent("""\
    Test project /home/user/project/build
        Start 1: test_logger
    1/5 Test #1: test_logger .....................   Passed    0.05 sec
        Start 2: test_config
    2/5 Test #2: test_config .....................   Passed    0.03 sec
        Start 3: test_network
    3/5 Test #3: test_network ....................***Failed    0.12 sec
        Start 4: test_database
    4/5 Test #4: test_database ...................   Passed    0.45 sec
        Start 5: test_renderer
    5/5 Test #5: test_renderer ...................***Failed    0.08 sec

    60% tests passed, 2 tests failed out of 5
    """)

    print("模拟 CTest 输出:")
    print(mock_ctest_output)

    # 解析（正则提取）
    passed = []
    failed = []
    for line in mock_ctest_output.splitlines():
        if "Passed" in line:
            m = re.match(r'.*Test #(\d+):\s+(\S+)', line)
            if m:
                passed.append({"num": int(m.group(1)), "name": m.group(2)})
        elif "Failed" in line or "***Failed" in line:
            m = re.match(r'.*Test #(\d+):\s+(\S+)', line)
            if m:
                failed.append({"num": int(m.group(1)), "name": m.group(2)})

    # 生成 JUnit XML 报告（CI 系统通用格式）
    # C++ 对比: 很多 CI 系统（Jenkins, GitLab CI）都支持 JUnit XML
    # Python 用 xml.etree.ElementTree 生成更简洁
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    testsuites = ET.Element("testsuites")
    testsuite = ET.SubElement(testsuites, "testsuite",
                              name="MyApp",
                              tests=str(len(passed) + len(failed)),
                              failures=str(len(failed)))

    for t in passed:
        ET.SubElement(testsuite, "testcase", name=t["name"],
                      classname="myapp.tests",
                      time="0.0")

    for t in failed:
        tc = ET.SubElement(testsuite, "testcase", name=t["name"],
                           classname="myapp.tests", time="0.0")
        ET.SubElement(tc, "failure", message="Test failed")

    xml_str = minidom.parseString(ET.tostring(testsuites)).toprettyxml(indent="  ")
    xml_path = test_dir / "test_report.xml"
    xml_path.write_text(xml_str, encoding="utf-8")

    print(f"\n--- JUnit XML 报告 ---")
    print(f"生成: {xml_path}")
    print(f"  Passed: {len(passed)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Rate:   {len(passed)/(len(passed)+len(failed))*100:.0f}%")


# ============================================================
# 9. 清理测试文件
# ============================================================
# C++ 对比: 清理构建产物也是常见需求
# rm -rf 在 Windows 上不可用，Python 的 shutil.rmtree 跨平台

def demo_cleanup(test_dir: Path):
    print("\n" + "=" * 60)
    print("9. 清理")
    print("=" * 60)

    import shutil
    # 清理整个测试目录
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"已清理: {test_dir}")


# ============================================================
# 主入口
# ============================================================
def main():
    """运行所有演示"""
    print("Day 09: C++ 项目自动化 (CMake 辅助 & 批量编译)")
    print("=" * 60)
    print("本脚本通过模拟演示各核心知识点，不会执行真实的 cmake 编译。")
    print("所有演示文件和输出放在 _test_output/ 和 generated/ 目录。")
    print()

    test_dir = demo_pathlib()
    demo_cmake_parse(test_dir)
    demo_cmake_generate(test_dir)
    simulate_batch_build(test_dir)
    demo_incremental_build(test_dir)
    demo_build_config(test_dir)
    demo_code_generation(test_dir)
    demo_test_runner(test_dir)
    demo_cleanup(test_dir)

    print("\n" + "=" * 60)
    print("全部演示完成！")
    print("=" * 60)
    print()
    print("C++ 开发者要点回顾:")
    print("  1. pathlib  ≈ C++17 std::filesystem::path（但更简洁）")
    print("  2. re 正则  ≈ C++ std::regex（Python 更方便）")
    print("  3. subprocess ≈ system()/fork+exec（Python 跨平台）")
    print("  4. json      ≈ 无标准等价物（C++26 才有）")
    print("  5. ThreadPoolExecutor ≈ std::async（Python 更简单）")
    print("  6. 模板生成  —— Python 的天然优势，C++ 不适合做")
    print()
    print("下一步: 查看 Day09/cpp_project_builder.py 完整工具")


if __name__ == "__main__":
    main()
