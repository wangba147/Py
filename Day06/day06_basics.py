"""
Day 06: 正则表达式与文本处理 —— 基础练习脚本
==============================================
对应 HTML: day06_regex_text.html
目标: 掌握 re 模块的 search/match/findall/sub/compile
      掌握分组、命名分组、贪婪/非贪婪、VERBOSE
"""
import re


def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ============================================================
# 1. search / match / findall / sub
# ============================================================
section("1. 四个高频函数: search / match / findall / sub")

s = "My phone: 138-1234-5678, office: 010-8765-4321"

# C++ 对比:
#   std::regex_search(s, m, std::regex(R"(\d{3}-\d{4}-\d{4})"));
#   if (m.ready()) { std::cout << m[0].str() << std::endl; }

# 1.1 search: 在任意位置找第一个
m = re.search(r'\d{3}-\d{4}-\d{4}', s)
print(f"search  ->  {m.group() if m else None}")  # 138-1234-5678

# 1.2 match: 仅在开头匹配（C++ 里的 match_flag 概念类似，但更严格）
m2 = re.match(r'My', s)
print(f"match   ->  {m2.group() if m2 else None}")  # My
m3 = re.match(r'phone', s)  # 不在开头
print(f"match   ->  {m3}")  # None

# 1.3 findall: 提取全部
phones = re.findall(r'\d{3}-\d{4}-\d{4}', s)
print(f"findall ->  {phones}")  # ['138-1234-5678', '010-8765-4321']

# 1.4 sub: 替换
masked = re.sub(r'\d{4}', '****', s)
print(f"sub     ->  {masked}")  # My phone: 138-****-****, office: 010-****-****

# 1.5 split: 按模式切分
csv = "a,b,,c,d"
parts = re.split(r',+', csv)  # 连续逗号合并
print(f"split   ->  {parts}")


# ============================================================
# 2. 字符类与量词速查
# ============================================================
section("2. 字符类与量词")

text = "User1 has 42 points, User2 has 100 points, and 3.14 is pi"

# \d+ 数字
nums = re.findall(r'\d+', text)
print(f"\\d+     ->  {nums}")  # ['1', '42', '2', '100', '3', '14']
# \d+\.?\d* 浮点数
floats = re.findall(r'\d+\.?\d*', text)
print(f"浮点数   ->  {floats}")
# \w+ 单词
words = re.findall(r'\w+', text)[:6]
print(f"\\w+     ->  {words}")

# 量词
samples = ["a", "ab", "abc", "abcd", "abcde"]
print(f"ab?     ->  {re.findall(r'ab?', 'a ab abc abcd')}")      # 贪婪
print(f"ab{{2}}  ->  {re.findall(r'ab{2}', 'a ab abb abbb')}")    # 恰好2个
print(f"ab{{2,}} ->  {re.findall(r'ab{2,}', 'a ab abb abbb')}")   # 至少2个


# ============================================================
# 3. 分组与命名分组
# ============================================================
section("3. 分组: 匿名与命名")

# 3.1 匿名分组
date = "2024-03-15"
m = re.search(r'(\d{4})-(\d{2})-(\d{2})', date)
if m:
    print(f"匿名分组: year={m.group(1)}, month={m.group(2)}, day={m.group(3)}")
    print(f"全部 4 组: {m.groups()}")

# 3.2 命名分组 (强烈推荐)
m = re.search(r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})', date)
if m:
    print(f"命名分组: year={m.group('year')}, month={m.group('month')}, day={m.group('day')}")
    print(f"字典:     {m.groupdict()}")

# 3.3 反向引用
html = "<div>hello</div>"
m = re.search(r'<(?P<tag>\w+)>.*?</(?P=tag)>', html)
print(f"反向引用: {m.group() if m else None}")

m = re.search(r'<(?P<tag>\w+)>.*?</(?P=tag)>', "<div>wrong</span>")
print(f"错误匹配: {m}")


# ============================================================
# 4. 贪婪 vs 非贪婪
# ============================================================
section("4. 贪婪 vs 非贪婪")

html = "<b>foo</b>middle<b>bar</b>"

# 贪婪: 匹配最长
greedy = re.findall(r'<b>.*</b>', html)
print(f"贪婪   ->  {greedy}")

# 非贪婪: 匹配最短
lazy = re.findall(r'<b>.*?</b>', html)
print(f"非贪婪 ->  {lazy}")


# ============================================================
# 5. compile 与性能
# ============================================================
section("5. re.compile: 循环中的最佳实践")

# 错误示范: 每次循环都解析正则
lines = [f"line {i}: value={i * 10}" for i in range(10000)]

# 方式 1: 每次调用 re.search (慢)
# for line in lines:
#     m = re.search(r'value=(\d+)', line)

# 方式 2: 预编译 (快 5~10 倍)
import time
pattern = re.compile(r'value=(\d+)')

t0 = time.perf_counter()
total = 0
for line in lines:
    m = pattern.search(line)
    if m:
        total += int(m.group(1))
t1 = time.perf_counter()
print(f"compile 方式: 耗时 {(t1 - t0) * 1000:.2f} ms, total={total}")


# ============================================================
# 6. 标志位: IGNORECASE / MULTILINE / DOTALL / VERBOSE
# ============================================================
section("6. 标志位: 改变匹配行为")

# 6.1 IGNORECASE
text = "Hello HELLO hello HeLLo"
matches = re.findall(r'hello', text, re.IGNORECASE)
print(f"IGNORECASE  ->  {matches}  (匹配到 {len(matches)} 个)")

# 6.2 MULTILINE: ^ $ 匹配每行
log = "error: line1\nwarning: line2\nerror: line3"
errors = re.findall(r'^error:.*$', log, re.MULTILINE)
print(f"MULTILINE   ->  {errors}")

# 6.3 DOTALL: . 匹配换行
multi = "start\nmiddle\nend"
m = re.search(r'start.*end', multi, re.DOTALL)
print(f"DOTALL      ->  {m.group() if m else None}")
m = re.search(r'start.*end', multi)  # 不加 DOTALL
print(f"默认行为    ->  {m}")

# 6.4 VERBOSE: 可读性
phone_re = re.compile(r'''
    ^(?P<area>\d{3})-
    (?P<num1>\d{4})-
    (?P<num2>\d{4})$
''', re.VERBOSE)

m = phone_re.search("138-1234-5678")
print(f"VERBOSE     ->  {m.groupdict() if m else None}")


# ============================================================
# 7. 字符串方法 (不需要正则也能做)
# ============================================================
section("7. 字符串自带方法: split/strip/replace/join")

# split
line = "  hello, world, foo, bar  "
parts = [p.strip() for p in line.strip().split(",")]
print(f"split       ->  {parts}")

# replace
path = "C:\\Users\\foo\\bar.cpp"
unix_style = path.replace("\\", "/")
print(f"path 转换   ->  {unix_style}")

# join
words = ["g++", "-O2", "-std=c++17", "main.cpp", "-o", "main"]
cmd = " ".join(words)
print(f"join        ->  {cmd}")

# startswith/endswith
files = ["main.cpp", "utils.h", "CMakeLists.txt", "README.md"]
cpp_files = [f for f in files if f.endswith((".cpp", ".h", ".hpp"))]
print(f"过滤 C++    ->  {cpp_files}")


# ============================================================
# 8. 实战: 解析 GCC 编译错误
# ============================================================
section("8. 实战: 解析 GCC 编译错误")

log = """
main.cpp: In function 'int main()':
main.cpp:12:5: error: 'foo' was not declared in this scope
   12 |     foo();
      |     ^~~
main.cpp:15:9: warning: unused variable 'x' [-Wunused-variable]
   15 |     int x = 42;
      |         ^
utils.cpp:42:1: error: expected '}' at end of input
   42 |
      | ^
"""

pattern = re.compile(
    r'^(?P<file>[\w./\\-]+):(?P<line>\d+):(?P<col>\d+):\s*'
    r'(?P<severity>error|warning|note):\s*(?P<msg>.*)$',
    re.MULTILINE
)

print("原始错误日志解析:")
for m in pattern.finditer(log):
    d = m.groupdict()
    sev = d['severity'].upper().ljust(7)
    print(f"  [{sev}] {d['file']}:{d['line']} {d['msg'].strip()}")


# ============================================================
# 9. 实战: 提取 TODO/FIXME 注释
# ============================================================
section("9. 实战: 提取 TODO/FIXME")

sample_code = """
#include <iostream>

// TODO(alice): 2024-03-15: 实现 serialize 方法
class Serializer {
    // FIXME: 这里有内存泄漏
    void save();
    // HACK: 临时方案，后续要重构
    void process();
};

/* NOTE: 性能敏感，不要随便改 */
int main() {
    // xxx: 这段是无效注释（不会匹配）
    return 0;
}
"""

todo_re = re.compile(r'''
    (?P<tag>TODO|FIXME|XXX|HACK|NOTE)
    (?:\((?P<owner>[\w]+)\))?
    (?::\s*(?P<date>\d{4}-\d{2}-\d{2}))?
    \s*:\s*
    (?P<msg>.*?)
    \s*$
''', re.VERBOSE | re.IGNORECASE | re.MULTILINE)

print("扫描结果:")
for i, line in enumerate(sample_code.splitlines(), 1):
    for m in todo_re.finditer(line):
        d = m.groupdict()
        owner = d['owner'] or 'unassigned'
        date = d['date'] or '----------'
        print(f"  L{i:3} {d['tag']:6} | owner={owner:10} | date={date} | {d['msg']}")


# ============================================================
# 10. 实战: 批量重命名 (安全替换)
# ============================================================
section("10. 实战: 批量重命名 — 只替换完整单词")

# 模拟几个文件
import tempfile, os
tmpdir = tempfile.mkdtemp()
files_content = {
    "Widget.h":   "class Widget { Widget* parent; };",
    "main.cpp":   "Widget w; WidgetFactory::create();",
    "bad.txt":    "Widgetry should NOT be replaced",
}

for name, content in files_content.items():
    p = os.path.join(tmpdir, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)

# 替换 OldName -> NewName
pattern = re.compile(r'\bWidget\b')  # \b 是单词边界

print("替换 'Widget' -> 'Component':")
for name in os.listdir(tmpdir):
    path = os.path.join(tmpdir, name)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    new_text, n = pattern.subn("Component", text)
    if n > 0:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        print(f"  {name}: {n} 处 -> {new_text}")
    else:
        print(f"  {name}: 0 处 (无变化)")

# 清理
import shutil
shutil.rmtree(tmpdir)


# ============================================================
# 11. 总结对比表
# ============================================================
section("11. C++ std::regex vs Python re 对比")

table = """
| 功能         | C++ std::regex                  | Python re            |
|--------------|--------------------------------|----------------------|
| 编译         | std::regex re("...")            | re.compile("...")    |
| 搜索         | std::regex_search(s, m, re)    | re.search(pat, s)    |
| 匹配开头     | std::regex_match(s, m, re)     | re.match(pat, s)     |
| 全部匹配     | std::sregex_iterator           | re.findall/finditer  |
| 替换         | std::regex_replace             | re.sub               |
| 命名分组     | ❌ 不支持 (C++17 起仍无)        | ✅ (?P<name>...)     |
| 非贪婪       | ✅ *? +? ??                    | ✅ *? +? ??          |
| 标志位       | std::regex::icase 等枚举       | re.IGNORECASE 等     |
| 性能         | 一般                           | 一般 (compile 后 OK) |
| 易用性       | 难用                           | 易用                 |
"""
print(table)


print("\n" + "=" * 60)
print("  Day 06 练习完成!")
print("  下一节: Day 07 - subprocess 与系统调用")
print("=" * 60)
