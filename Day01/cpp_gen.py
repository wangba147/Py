"""
cpp_gen.py — C++ 头文件/源文件生成器
用法: python cpp_gen.py MyClass
会在当前目录生成 MyClass.h 和 MyClass.cpp

这是 Day 01 的实战脚本，展示 Python 如何辅助 C++ 开发
"""

import sys
import os


def generate_header(class_name: str) -> str:
    """生成 .h 文件内容"""
    guard = f"{class_name.upper()}_H_"
    return f"""#ifndef {guard}
#define {guard}

class {class_name} {{
public:
    {class_name}();
    ~{class_name}();

private:
    // TODO: 成员变量
}};

#endif // {guard}
"""


def generate_source(class_name: str) -> str:
    """生成 .cpp 文件内容"""
    return f"""#include "{class_name}.h"

{class_name}::{class_name}() {{
    // TODO: 构造函数实现
}}

{class_name}::~{class_name}() {{
    // TODO: 析构函数实现
}}
"""


def main():
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} ClassName")
        print("示例: python cpp_gen.py Player")
        sys.exit(1)

    class_name = sys.argv[1]

    # 检查类名是否合法（简单校验）
    if not class_name[0].isalpha() and class_name[0] != '_':
        print(f"错误: 类名 '{class_name}' 不合法，必须以字母或下划线开头")
        sys.exit(1)

    # 写入 .h 文件
    header_path = f"{class_name}.h"
    if os.path.exists(header_path):
        print(f"警告: {header_path} 已存在，跳过")
    else:
        with open(header_path, "w", encoding="utf-8") as f:
            f.write(generate_header(class_name))
        print(f"✓ 已生成 {header_path}")

    # 写入 .cpp 文件
    source_path = f"{class_name}.cpp"
    if os.path.exists(source_path):
        print(f"警告: {source_path} 已存在，跳过")
    else:
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(generate_source(class_name))
        print(f"✓ 已生成 {source_path}")


if __name__ == "__main__":
    main()
