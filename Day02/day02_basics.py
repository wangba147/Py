"""
Day 02 练习脚本 — 流程控制与函数进阶
面向 C++ 开发者的 Python 学习

运行方式: python day02_basics.py
"""

import sys
import io

# 修复 Windows 终端 Unicode 输出问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ============================================================
# 1. 条件表达式（三元运算符）
# ============================================================
# C++: std::string result = (x > 0) ? "positive" : "non-positive";
# Python: result = "positive" if x > 0 else "non-positive"

print("=== 1. 条件表达式（三元运算符） ===")

x = 42
label = "positive" if x > 0 else "non-positive"
print(f"x={x}, label={label}")

# 嵌套条件表达式（不推荐过度使用，但偶尔很方便）
# C++: (x > 0) ? "pos" : (x < 0) ? "neg" : "zero"
sign = "positive" if x > 0 else ("negative" if x < 0 else "zero")
print(f"sign={sign}")

# 实用场景：设置默认值
# C++: std::string name = userName.empty() ? "Anonymous" : userName;
user_input = ""
display_name = user_input or "Anonymous"  # 短路求值，空字符串为 falsy
print(f"display_name={display_name}")

# ============================================================
# 2. match-case（Python 3.10+ 模式匹配）
# ============================================================
# C++ 没有原生模式匹配（需用 switch + if-else 组合）
# Python 3.10 引入了结构化模式匹配，比 switch 强大得多

print("\n=== 2. match-case 模式匹配 ===")


def http_status(code: int) -> str:
    """HTTP 状态码描述 —— match-case 示例"""
    match code:
        case 200:
            return "OK"
        case 301:
            return "Moved Permanently"
        case 400:
            return "Bad Request"
        case 404:
            return "Not Found"
        case 500:
            return "Internal Server Error"
        case _:  # 等同于 C++ 的 default
            return f"Unknown({code})"


print(f"200 → {http_status(200)}")
print(f"404 → {http_status(404)}")
print(f"418 → {http_status(418)}")

# 模式匹配的强大之处：解构匹配
print("\n--- 解构匹配 ---")


def describe_command(cmd: list) -> str:
    """描述命令 —— 结构化模式匹配"""
    match cmd:
        case ["git", "clone", url]:
            return f"克隆仓库: {url}"
        case ["git", "commit", "-m", msg]:
            return f"提交: {msg}"
        case ["git", *rest]:  # *rest 捕获剩余元素
            return f"其他 git 命令: {rest}"
        case ["cmake", *args]:
            return f"CMake 参数: {args}"
        case _:
            return "未知命令"


print(describe_command(["git", "clone", "https://github.com/example/repo"]))
print(describe_command(["git", "commit", "-m", "fix: null pointer crash"]))
print(describe_command(["git", "status"]))
print(describe_command(["cmake", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"]))

# ============================================================
# 3. 循环进阶
# ============================================================
print("\n=== 3. 循环进阶 ===")

# --- range() 的完整形式 ---
# C++: for (int i = 5; i < 15; i += 3)
# Python: range(start, stop, step)
print("range(5, 15, 3):", list(range(5, 15, 3)))

# 倒序
# C++: for (int i = 10; i > 0; i -= 2)
print("range(10, 0, -2):", list(range(10, 0, -2)))

# --- break 和 continue ---
# 与 C++ 完全一致，但 Python 还有 else 子句！
print("\n--- 循环的 else 子句 ---")

# 循环的 else：只有循环"正常结束"（没被 break）时才执行
# C++ 没有这个特性，通常用布尔标志位模拟

def find_first_even(nums: list[int]) -> int | None:
    """找第一个偶数，找不到返回 None"""
    for n in nums:
        if n % 2 == 0:
            print(f"  找到偶数: {n}")
            break
    else:
        # 只有循环没被 break 时才执行
        print("  没有找到偶数")
        return None
    return n

find_first_even([1, 3, 5, 6, 7])   # 找到 6
find_first_even([1, 3, 5, 7])       # 没找到

# --- zip()：并行遍历 ---
# C++ 需要手动管理两个迭代器
# C++23 有 std::views::zip，但大多数项目还用不上
print("\n--- zip() 并行遍历 ---")
files = ["main.cpp", "utils.cpp", "parser.cpp"]
sizes = [2048, 1024, 4096]
for f, s in zip(files, sizes):
    print(f"  {f}: {s} bytes")

# zip_longest：不等长时填充默认值
from itertools import zip_longest
logs = ["error.log", "access.log", "debug.log", "trace.log"]
levels = ["ERROR", "INFO"]
for log, level in zip_longest(logs, levels, fillvalue="UNKNOWN"):
    print(f"  {log}: {level}")

# --- itertools 常用工具 ---
# C++ 没有直接对应，通常需要手写循环
from itertools import chain, count, islice

# chain：拼接多个可迭代对象
# C++ 需要先把多个 vector 拼成一个
combined = list(chain(files, sizes))
print(f"\nchain: {combined}")

# count：无限计数器
# C++: for (int i = 100; ; i++) — 没有优雅的抽象
for i in islice(count(100, 5), 5):  # 从 100 开始步进 5，取 5 个
    print(f"  count: {i}", end="")
print()

# ============================================================
# 4. 函数进阶
# ============================================================
print("\n=== 4. 函数进阶 ===")

# --- 默认参数（陷阱！） ---
# C++ 默认参数：在声明处求值
# Python 默认参数：在函数定义时求值（只一次！）

print("--- 默认参数陷阱 ---")

# ❌ 错误示范：可变默认参数
# def bad_append(item, lst=[]):  # lst 只创建一次！
#     lst.append(item)
#     return lst
# bad_append(1) → [1]
# bad_append(2) → [1, 2]  ← 累积了！

# ✅ 正确做法：用 None 作为哨兵
def good_append(item: int, lst: list[int] | None = None) -> list[int]:
    if lst is None:
        lst = []
    lst.append(item)
    return lst

print(f"good_append(1) = {good_append(1)}")
print(f"good_append(2) = {good_append(2)}")  # [2]，不会累积

# --- *args 和 **kwargs ---
# C++: 可变参数用 va_list（不安全）或模板参数包（复杂）
# Python: *args 收集位置参数，**kwargs 收集关键字参数

print("\n--- *args 和 **kwargs ---")


def log_message(level: str, *args, **kwargs) -> None:
    """灵活的日志函数"""
    message = " ".join(str(a) for a in args)
    print(f"[{level}] {message}")
    if kwargs:
        print(f"  附加信息: {kwargs}")


log_message("INFO", "Build", "started")
log_message("WARN", "Memory", "low", threshold=85, unit="%")
log_message("ERROR", "Crash", "at", 0xDEAD, module="renderer", line=42)

# --- 强制关键字参数 ---
# C++ 没有命名参数，Python 可以强制要求

print("\n--- 强制关键字参数 ---")


def compile_project(
    target: str,
    mode: str = "Release",
    *,  # 此后的参数必须用关键字传递
    verbose: bool = False,
    jobs: int = 4,
) -> None:
    """编译项目 —— * 之后的参数必须关键字传递"""
    print(f"  编译 {target} | mode={mode} | verbose={verbose} | jobs={jobs}")


compile_project("MyApp")                                # OK
compile_project("MyApp", "Debug")                       # OK
compile_project("MyApp", "Debug", verbose=True, jobs=8) # OK
# compile_project("MyApp", "Debug", True, 8)            # ❌ TypeError!

# --- lambda 表达式 ---
# C++: auto square = [](int x) { return x * x; };
# Python: square = lambda x: x * x

print("\n--- lambda 表达式 ---")
square = lambda x: x * x
print(f"square(5) = {square(5)}")

# Python 的 lambda 只能是单表达式，不如 C++ lambda 灵活
# 但配合 sorted/filter/map 等很好用

# sorted 的 key 参数（极高频用法）
# C++: std::sort + 自定义比较函数
projects = [
    ("MyApp", 3, 15000),
    ("Utils", 1, 3000),
    ("Engine", 5, 50000),
]
# 按第三列（代码行数）排序
by_size = sorted(projects, key=lambda p: p[2])
print(f"按代码行排序: {by_size}")

# 按第二列（复杂度）降序
by_complexity = sorted(projects, key=lambda p: p[1], reverse=True)
print(f"按复杂度降序: {by_complexity}")

# ============================================================
# 5. 装饰器（Decorator）
# ============================================================
# C++ 没有直接对应。最接近的是模板 CRTP 或宏，但概念完全不同
# 装饰器 = 接受函数、返回函数的高阶函数

print("\n=== 5. 装饰器 ===")


import time
import functools


def timer(func):
    """计时装饰器 —— 测量函数执行时间"""
    @functools.wraps(func)  # 保留原函数的元信息
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  ⏱ {func.__name__}() 耗时 {elapsed:.6f}s")
        return result
    return wrapper


def retry(max_attempts: int = 3, delay: float = 1.0):
    """重试装饰器工厂 —— 可以带参数的装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"  ⚠ {func.__name__}() 第{attempt}次失败: {e}，{delay}s 后重试...")
                    time.sleep(delay)
        return wrapper
    return decorator


@timer
def slow_calculation() -> int:
    """模拟耗时计算"""
    total = 0
    for i in range(1000000):
        total += i
    return total


result = slow_calculation()
print(f"  计算结果: {result}")


# 带参数的装饰器
@retry(max_attempts=3, delay=0.1)
def flaky_network_call(url: str) -> str:
    """模拟不稳定的网络调用"""
    import random
    if random.random() < 0.6:  # 60% 概率失败
        raise ConnectionError(f"连接失败: {url}")
    return f"OK: {url}"


try:
    resp = flaky_network_call("https://api.example.com")
    print(f"  网络结果: {resp}")
except ConnectionError as e:
    print(f"  最终失败: {e}")

# ============================================================
# 6. 生成器（Generator）
# ============================================================
# C++20 协程可以模拟，但语法远比 Python 复杂
# Python 生成器：用 yield 暂停函数，惰性求值

print("\n=== 6. 生成器 ===")


def fibonacci(limit: int):
    """生成斐波那契数列 —— 惰性求值，不占内存"""
    a, b = 0, 1
    while a < limit:
        yield a  # 暂停，返回值，下次从这里继续
        a, b = b, a + b


# 生成器不会一次性计算所有值
fib = fibonacci(100)
print(f"生成器对象: {fib}")
print(f"前10个斐波那契数: {list(islice(fib, 10))}")

# 实用场景：逐行处理大文件
# C++ 需要手写迭代器类，Python 只需 yield


def read_log_chunks(filepath: str, chunk_size: int = 4096):
    """分块读取日志文件（模拟大文件处理）"""
    # 实际使用时打开真实文件，这里用内存模拟
    content = """[ERROR] 2024-01-15 Segfault in renderer
[WARN]  2024-01-15 Low memory warning
[INFO]  2024-01-15 Build completed
[ERROR] 2024-01-16 Null pointer dereference
[INFO]  2024-01-16 Tests passed"""
    for line in content.strip().split("\n"):
        yield line.strip()


# 过滤错误日志
errors = [line for line in read_log_chunks("app.log") if "[ERROR]" in line]
print(f"错误日志: {errors}")

# 生成器表达式（类似列表推导式，但惰性求值）
# C++: 需要手动构建结果 vector
# Python: 用圆括号代替方括号
total_size = sum(s for _, s in zip(files, sizes))  # 不会创建中间列表
print(f"文件总大小: {total_size} bytes")

# yield from：委托给子生成器
def flatten(nested: list):
    """展平嵌套列表"""
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)  # 递归委托
        else:
            yield item

nested = [1, [2, 3], [4, [5, 6]], 7]
print(f"展平: {list(flatten(nested))}")

# ============================================================
# 7. 闭包与高阶函数
# ============================================================
print("\n=== 7. 闭包与高阶函数 ===")

# 闭包：函数记住其定义时的环境
# C++: lambda 捕获变量（[=] 或 [&]）

def make_threshold_checker(threshold: int):
    """创建阈值检查器 —— 闭包示例"""
    def check(value: int) -> bool:
        return value >= threshold  # 记住了 threshold
    return check

is_warning = make_threshold_checker(80)
is_critical = make_threshold_checker(95)
print(f"is_warning(85) = {is_warning(85)}")
print(f"is_critical(85) = {is_critical(85)}")

# 高阶函数：map / filter / reduce
from functools import reduce

# C++: std::transform / std::copy_if / std::accumulate
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# map：变换每个元素
doubled = list(map(lambda x: x * 2, numbers))
print(f"map x2: {doubled}")

# filter：过滤
odds = list(filter(lambda x: x % 2 != 0, numbers))
print(f"filter 奇数: {odds}")

# reduce：累积（C++: std::accumulate）
total = reduce(lambda acc, x: acc + x, numbers, 0)
print(f"reduce 求和: {total}")

# 但在 Python 中，列表推导式通常比 map/filter 更 Pythonic
doubled_v2 = [x * 2 for x in numbers]
odds_v2 = [x for x in numbers if x % 2 != 0]
print(f"推导式版: doubled={doubled_v2}, odds={odds_v2}")

# ============================================================
# 8. 实战：C++ 构建日志分析器
# ============================================================
print("\n=== 8. 实战：C++ 构建日志分析器 ===")


def analyze_build_log(log_content: str) -> dict:
    """
    分析 C++ 构建日志，统计警告、错误、各文件编译时间
    """
    lines = log_content.strip().split("\n")

    # 使用生成器表达式过滤
    warnings = list(filter(lambda l: "warning" in l.lower(), lines))
    errors = list(filter(lambda l: "error" in l.lower(), lines))

    # 提取编译时间
    compile_times = {}
    for line in lines:
        if "Built target" in line and "seconds" in line:
            # 示例行: "[  85%] Built target MyApp (3.2 seconds)"
            parts = line.split("Built target")
            if len(parts) == 2:
                rest = parts[1].strip()
                target_end = rest.find("(")
                if target_end > 0:
                    target = rest[:target_end].strip()
                    time_str = rest[target_end + 1:rest.find("seconds")].strip()
                    try:
                        compile_times[target] = float(time_str)
                    except ValueError:
                        pass

    # 按编译时间排序（降序）
    sorted_targets = sorted(compile_times.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_lines": len(lines),
        "warnings": len(warnings),
        "errors": len(errors),
        "warning_lines": warnings[:5],  # 只保留前5条
        "error_lines": errors[:5],
        "compile_times": sorted_targets,
    }


# 模拟 CMake 构建日志
sample_log = """
[  10%] Building CXX object src/CMakeFiles/core.dir/main.cpp.o
[  20%] Building CXX object src/CMakeFiles/core.dir/parser.cpp.o
src/parser.cpp:42:5: warning: unused variable 'temp' [-Wunused-variable]
[  30%] Building CXX object src/CMakeFiles/core.dir/renderer.cpp.o
src/renderer.cpp:108:10: error: 'glClearColor' was not declared in this scope
src/renderer.cpp:200:3: warning: comparison between signed and unsigned [-Wsign-compare]
[  50%] Built target core (2.5 seconds)
[  60%] Building CXX object tests/CMakeFiles/tests.dir/test_main.cpp.o
[  70%] Building CXX object tests/CMakeFiles/tests.dir/test_parser.cpp.o
tests/test_parser.cpp:30:5: warning: implicit conversion from 'double' to 'float' [-Wconversion]
[  80%] Built target tests (1.8 seconds)
[  90%] Linking CXX executable MyApp
[  85%] Built target MyApp (3.2 seconds)
[100%] Built target AllTargets (8.5 seconds)
"""

report = analyze_build_log(sample_log)
print(f"总行数: {report['total_lines']}")
print(f"警告数: {report['warnings']}")
print(f"错误数: {report['errors']}")
print(f"编译耗时排名:")
for target, t in report["compile_times"]:
    print(f"  {target}: {t}s")
if report["warning_lines"]:
    print("警告示例:")
    for w in report["warning_lines"][:3]:
        print(f"  {w.strip()}")
if report["error_lines"]:
    print("错误示例:")
    for e in report["error_lines"][:3]:
        print(f"  {e.strip()}")

print("\n" + "=" * 50)
print("Day 02 练习脚本运行完毕！")
print("关键收获:")
print("  1. Python 条件表达式比 C++ 三元运算符更可读")
print("  2. match-case 远比 switch 强大（支持解构）")
print("  3. 可变默认参数是经典陷阱，用 None 代替")
print("  4. 装饰器是 Python 的杀手级特性，C++ 没有直接对应")
print("  5. 生成器用 yield 实现惰性求值，处理大数据利器")
print("=" * 50)
