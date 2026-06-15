"""
Day 01 练习脚本 — Python 基础语法体验
面向 C++ 开发者的 Python 入门

运行方式: python day01_basics.py
"""

import sys
import io

# 修复 Windows 终端 Unicode 输出问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ============================================================
# 1. 变量与动态类型
# ============================================================
# C++: int x = 42;    → 类型固定，编译时确定
# Python: x = 42      → 类型运行时推断，可随时改变

x = 42
print(f"x = {x}, type = {type(x).__name__}")  # x = 42, type = int

x = "now I'm a string"  # C++ 中这是编译错误，Python 完全合法
print(f"x = {x!r}, type = {type(x).__name__}")

# 但推荐使用类型注解（不强制，但 IDE 和 mypy 会检查）
age: int = 25
name: str = "Developer"
print(f"{name}, age = {age}")

# ============================================================
# 2. 数据类型对照
# ============================================================

# --- int: 任意精度，不会溢出！ ---
# C++: int 溢出是未定义行为
big_number = 2 ** 100  # 2的100次方
print(f"\n2^100 = {big_number}")  # 精确计算，不会溢出

# --- float: 对应 C++ 的 double ---
pi = 3.141592653589793
print(f"pi = {pi:.4f}")  # 格式化输出，类似 printf("%.4f", pi)

# --- bool: True/False（注意首字母大写） ---
# C++: true/false
is_cpp_dev = True
print(f"is_cpp_dev = {is_cpp_dev}")

# --- str: 不可变字符串 ---
# C++: std::string（可变）
greeting = "Hello, C++ Developer!"
print(f"greeting = {greeting}")
# greeting[0] = "h"  # 这会报错！str 是不可变的

# f-string（Python 3.6+）—— 最推荐的格式化方式
# C++: printf 或 std::format (C++20)
msg = f"Welcome, {name}! Age in hex: {age:#x}"
print(msg)

# --- list: 动态数组（对应 std::vector） ---
# C++: std::vector<int> nums = {1, 2, 3};
nums = [1, 2, 3, 4, 5]
nums.append(6)         # C++: nums.push_back(6)
nums.insert(0, 0)      # C++: nums.insert(nums.begin(), 0)
print(f"nums = {nums}")
print(f"len = {len(nums)}")  # C++: nums.size()
print(f"slice [1:4] = {nums[1:4]}")  # C++ 没有切片

# --- dict: 哈希表（对应 std::unordered_map） ---
# C++: std::unordered_map<std::string, int>
config = {
    "project": "MyApp",
    "version": 2,
    "debug": True
}
print(f"\nconfig = {config}")
print(f"project = {config['project']}")
print(f"safe access: {config.get('author', 'unknown')}")  # 不存在时返回默认值

# --- tuple: 不可变序列（对应 std::tuple） ---
point = (3, 4)
x_val, y_val = point  # 解包，C++: std::get<0>(point), std::get<1>(point)
print(f"\npoint = {point}, x = {x_val}, y = {y_val}")

# --- set: 哈希集合（对应 std::unordered_set） ---
unique_ids = {1, 2, 3, 3, 2}  # 自动去重
print(f"unique_ids = {unique_ids}")

# ============================================================
# 3. 基本运算
# ============================================================
print("\n--- 基本运算 ---")

# 整数除法 vs 浮点除法
print(f"7 / 2 = {7 / 2}")    # 3.5（浮点除法，C++ 中 int/int=3）
print(f"7 // 2 = {7 // 2}")  # 3   （整数除法，类似 C++ 的 int/int）
print(f"7 % 2 = {7 % 2}")    # 1   （取模，同 C++）
print(f"2 ** 10 = {2 ** 10}")# 1024（幂运算，C++ 需要 pow()）

# ============================================================
# 4. 字符串操作（高频使用）
# ============================================================
print("\n--- 字符串操作 ---")

s = "Hello, World!"
print(f"原始: {s}")
print(f"大写: {s.upper()}")
print(f"小写: {s.lower()}")
print(f"分割: {s.split(', ')}")
print(f"替换: {s.replace('World', 'Python')}")
print(f"切片 [7:12]: {s[7:12]}")  # "World"
print(f"反转: {s[::-1]}")          # C++ 需要 std::reverse
print(f"是否包含 'World': {'World' in s}")  # C++: s.find("World") != string::npos

# 多行字符串（C++ 原始字符串 R"(...)"）
code = """
int main() {
    return 0;
}
"""
print(f"多行字符串长度: {len(code.strip())}")

# ============================================================
# 5. 列表推导式（Python 杀手级特性）
# ============================================================
print("\n--- 列表推导式 ---")

# C++ 需要循环 + push_back:
#   std::vector<int> squares;
#   for (int i = 0; i < 10; i++) squares.push_back(i * i);
squares = [i * i for i in range(10)]
print(f"平方: {squares}")

# 带条件过滤
evens = [i for i in range(20) if i % 2 == 0]
print(f"偶数: {evens}")

# 字典推导式
word_len = {w: len(w) for w in ["hello", "world", "python"]}
print(f"词长: {word_len}")

# ============================================================
# 6. 流程控制基础
# ============================================================
print("\n--- 流程控制 ---")

# if-elif-else（注意冒号和缩进！）
score = 85
if score >= 90:
    grade = "A"
elif score >= 80:  # C++: else if
    grade = "B"
elif score >= 70:
    grade = "C"
else:
    grade = "D"
print(f"score={score}, grade={grade}")

# for 循环（最常用）
# C++: for (int i = 0; i < 5; i++)
for i in range(5):
    print(f"  i = {i}", end="")
print()  # 换行

# 遍历容器
fruits = ["apple", "banana", "cherry"]
for idx, fruit in enumerate(fruits):  # enumerate 类似 C++ 的索引+值
    print(f"  [{idx}] {fruit}")

# while 循环
count = 3
while count > 0:
    print(f"  倒计时: {count}")
    count -= 1

# ============================================================
# 7. 函数定义
# ============================================================
print("\n--- 函数定义 ---")


def add(a: int, b: int) -> int:
    """两数相加（文档字符串，类似 Doxygen 注释）"""
    return a + b


def greet(name: str = "World") -> None:
    """带默认参数的函数"""
    print(f"  Hello, {name}!")


print(f"add(3, 4) = {add(3, 4)}")
greet()
greet("Python")

# 多返回值（实际返回 tuple）
def divide(a: int, b: int) -> tuple[int, int]:
    """返回商和余数"""
    return a // b, a % b

quotient, remainder = divide(17, 5)
print(f"17 ÷ 5 = {quotient} ... {remainder}")

# ============================================================
# 8. 文件读写（Python 的 with 类似 C++ 的 RAII）
# ============================================================
print("\n--- 文件读写 ---")

# 写文件
with open("day01_test.txt", "w", encoding="utf-8") as f:
    f.write("Hello from Python!\n")
    f.write("This file is auto-generated.\n")
print("✓ 已写入 day01_test.txt")

# 读文件
with open("day01_test.txt", "r", encoding="utf-8") as f:
    content = f.read()
print(f"读取内容:\n{content}")

# 逐行读取
with open("day01_test.txt", "r", encoding="utf-8") as f:
    for line_num, line in enumerate(f, 1):
        print(f"  Line {line_num}: {line.rstrip()}")  # rstrip 去掉末尾换行

# ============================================================
# 9. C++ 开发实用片段：读取配置文件
# ============================================================
print("\n--- 实用：解析简单配置 ---")


def parse_config(filepath: str) -> dict[str, str]:
    """
    解析简单的 key=value 配置文件
    类似 C++ 中手写的 INI 解析器，但 Python 只需几行
    """
    config = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # 跳过空行和注释
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"  警告: 配置文件 {filepath} 不存在")
    return config


# 创建示例配置文件
with open("day01_sample.cfg", "w", encoding="utf-8") as f:
    f.write("# 应用配置\n")
    f.write("app_name = MyCppApp\n")
    f.write("version = 1.0.0\n")
    f.write("debug = true\n")
    f.write("# log_level = verbose\n")

cfg = parse_config("day01_sample.cfg")
print(f"配置解析结果: {cfg}")

# ============================================================
# 10. 清理测试文件
# ============================================================
import os

os.remove("day01_test.txt")
os.remove("day01_sample.cfg")
print("\n✓ 测试文件已清理")

print("\n" + "=" * 50)
print("Day 01 练习脚本运行完毕！")
print("下一步: 尝试修改本脚本中的值，观察输出变化")
print("=" * 50)
