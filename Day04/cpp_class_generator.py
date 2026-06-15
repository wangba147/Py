#!/usr/bin/env python3
"""
C++ 类代码生成器 — 从 Python 数据类定义自动生成 C++ .h / .cpp 骨架

核心思路：
  Python 的 dataclass/类定义简洁灵活 → 自动生成 C++ 样板代码

用法：
  python cpp_class_generator.py              # 交互模式
  python cpp_class_generator.py --demo       # 运行演示
  python cpp_class_generator.py --json spec.json  # 从 JSON 规格文件生成

适用场景：
  - 快速生成 C++ 类骨架（包含头文件 + 实现文件）
  - 批量创建项目中的 POJO / DTO / 配置结构体
  - 从接口定义生成 C++ 实现桩
"""

import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


# ============================================================
# 类型映射表: Python 类型 → C++ 类型
# ============================================================
TYPE_MAP = {
    "int": "int",
    "float": "float",
    "double": "double",
    "bool": "bool",
    "str": "std::string",
    "string": "std::string",
    "list[str]": "std::vector<std::string>",
    "list[int]": "std::vector<int>",
    "list[float]": "std::vector<double>",
    "list[double]": "std::vector<double>",
    "list[bool]": "std::vector<bool>",
    "vector[str]": "std::vector<std::string>",
    "vector[int]": "std::vector<int>",
    "vector<double]": "std::vector<double>",
    "optional[str]": "std::optional<std::string>",
    "optional[int]": "std::optional<int>",
    "optional[double]": "std::optional<double>",
    "dict[str,str]": "std::unordered_map<std::string, std::string>",
    "dict[str,int]": "std::unordered_map<std::string, int>",
    "map[str,str]": "std::unordered_map<std::string, std::string>",
    "any": "std::any",
    "NoneType": "std::nullptr_t",
}


def py_type_to_cpp(py_type: str) -> str:
    """将 Python 类型字符串映射为 C++ 类型"""
    py_type = py_type.strip().lower()
    return TYPE_MAP.get(py_type, py_type)  # 未映射的直接使用


# ============================================================
# 核心生成器
# ============================================================
@dataclass
class MemberSpec:
    """成员变量规格"""
    name: str
    py_type: str
    default: Optional[str] = None  # 字符串形式的默认值
    is_const: bool = False
    is_static: bool = False


@dataclass
class MethodSpec:
    """成员方法规格"""
    name: str
    return_type: str
    params: List[Dict[str, str]] = field(default_factory=list)
    is_const: bool = False
    is_virtual: bool = False
    is_static: bool = False
    is_pure_virtual: bool = False
    body: str = ""  # 方法体（C++ 代码）


@dataclass
class ClassSpec:
    """完整的类规格"""
    name: str
    namespace: Optional[str] = None
    members: List[MemberSpec] = field(default_factory=list)
    methods: List[MethodSpec] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)
    use_pragma_once: bool = True
    include_headers: List[str] = field(default_factory=list)
    description: str = ""


class CppCodeGenerator:
    """C++ 代码生成器"""

    def __init__(self, spec: ClassSpec):
        self.spec = spec

    def _cpp_type(self, py_type: str) -> str:
        return py_type_to_cpp(py_type)

    def _default_value(self, member: MemberSpec) -> str:
        """生成成员默认值初始化"""
        if member.default is None and member.py_type == "str":
            return '""'
        if member.default is None and member.py_type in ("int", "float", "double"):
            return "0"
        if member.default is None and member.py_type == "bool":
            return "false"
        if member.default is None:
            return "{}"
        return member.default

    def generate_header(self) -> str:
        """生成 .h 头文件"""
        s = self.spec
        lines = []

        # 头文件保护
        if s.use_pragma_once:
            lines.append("#pragma once")
        else:
            guard = f"{s.name.upper()}_H"
            if s.namespace:
                guard = f"{s.namespace.upper()}_{guard}"
            lines.append(f"#ifndef {guard}")
            lines.append(f"#define {guard}")

        lines.append("")

        # 标准库 include
        includes = set()
        for m in s.members:
            cpp_type = self._cpp_type(m.py_type)
            if "string" in cpp_type:
                includes.add("<string>")
            if "vector" in cpp_type:
                includes.add("<vector>")
            if "optional" in cpp_type:
                includes.add("<optional>")
            if "map" in cpp_type or "unordered_map" in cpp_type:
                includes.add("<unordered_map>")
            if "any" in cpp_type:
                includes.add("<any>")
        if any(m for m in s.methods if m.is_virtual):
            includes.add("<memory>")

        for inc in sorted(includes):
            lines.append(f"#include {inc}")
        for inc in s.include_headers:
            if inc.startswith("<"):
                lines.append(f"#include {inc}")
            else:
                lines.append(f'#include "{inc}"')

        lines.append("")

        # namespace 开始
        ns_open = False
        if s.namespace:
            ns_parts = s.namespace.split("::")
            for part in ns_parts:
                lines.append(f"namespace {part} {{")
                ns_open = True

        if ns_open:
            lines.append("")

        # 类描述
        if s.description:
            lines.append(f"/**")
            lines.append(f" * {s.description}")
            lines.append(f" */")

        # 类声明
        class_decl = f"class {s.name}"
        if s.base_classes:
            bases = [f"public {b}" for b in s.base_classes]
            class_decl += " : " + ", ".join(bases)
        lines.append(f"{class_decl} {{")

        # 公共接口
        lines.append("public:")
        # 构造/析构
        lines.append(f"    {s.name}();")
        if s.members:
            # 参数化构造器
            params = []
            init_list = []
            for m in s.members:
                cpp_type = self._cpp_type(m.py_type)
                const_ref_types = {"std::string", "std::vector"}
                if any(t in cpp_type for t in ["std::string", "std::vector"]):
                    params.append(f"{cpp_type} {m.name}")
                else:
                    params.append(f"{cpp_type} {m.name}")
            params_str = ", ".join(params)
            lines.append(f"    {s.name}({params_str});")
        lines.append(f"    ~{s.name}() = default;")
        lines.append("")

        # 成员方法
        for method in s.methods:
            prefix = "virtual " if method.is_virtual else ""
            suffix = " const" if method.is_const else ""

            params = []
            for p in method.params:
                cpp_type = self._cpp_type(p["type"])
                params.append(f"{cpp_type} {p['name']}")
            params_str = ", ".join(params)

            if method.is_pure_virtual:
                lines.append(f"    {prefix}{self._cpp_type(method.return_type)} {method.name}({params_str}){suffix} = 0;")
            elif method.body and not method.is_virtual:
                # 内联实现
                indent = "        "
                body_lines = method.body.strip().split("\n")
                if len(body_lines) == 1:
                    lines.append(f"    {prefix}{self._cpp_type(method.return_type)} {method.name}({params_str}){suffix} {{ {body_lines[0]} }}")
                else:
                    lines.append(f"    {prefix}{self._cpp_type(method.return_type)} {method.name}({params_str}){suffix} {{")
                    for bl in body_lines:
                        lines.append(f"        {bl}")
                    lines.append("    }")
            else:
                lines.append(f"    {prefix}{self._cpp_type(method.return_type)} {method.name}({params_str}){suffix};")

        if s.methods:
            lines.append("")

        # getters (为每个成员自动生成)
        for m in s.members:
            cpp_type = self._cpp_type(m.py_type)
            const_ref_types = {"std::string", "std::vector"}
            if any(t in cpp_type for t in const_ref_types):
                lines.append(f"    const {cpp_type}& get_{m.name}() const {{ return {m.name}_; }}")
            else:
                lines.append(f"    {cpp_type} get_{m.name}() const {{ return {m.name}_; }}")

        # setters
        for m in s.members:
            cpp_type = self._cpp_type(m.py_type)
            const_ref_types = {"std::string", "std::vector"}
            if any(t in cpp_type for t in const_ref_types):
                lines.append(f"    void set_{m.name}(const {cpp_type}& val) {{ {m.name}_ = val; }}")
            else:
                lines.append(f"    void set_{m.name}({cpp_type} val) {{ {m.name}_ = val; }}")

        # 私有成员
        lines.append("")
        lines.append("private:")
        for m in s.members:
            cpp_type = self._cpp_type(m.py_type)
            default = self._default_value(m)
            mod = "static " if m.is_static else ""
            const = "const " if m.is_const else ""
            if default:
                lines.append(f"    {mod}{const}{cpp_type} {m.name}_ = {default};")
            else:
                lines.append(f"    {mod}{const}{cpp_type} {m.name}_;")

        lines.append("};")

        # namespace 结束
        if ns_open:
            ns_parts = s.namespace.split("::")
            lines.append("")
            for part in reversed(ns_parts):
                lines.append(f"}}  // namespace {part}")

        return "\n".join(lines) + "\n"

    def generate_source(self) -> str:
        """生成 .cpp 实现文件"""
        s = self.spec
        lines = []

        # include 头文件
        if s.namespace:
            ns_path = s.namespace.replace("::", "/")
            lines.append(f'#include "{ns_path}/{s.name}.h"')
        else:
            lines.append(f'#include "{s.name}.h"')
        lines.append("")

        # namespace
        ns_open = False
        if s.namespace:
            for part in s.namespace.split("::"):
                lines.append(f"namespace {part} {{")
                ns_open = True
            lines.append("")

        # 默认构造函数
        if s.members:
            init_members = []
            for m in s.members:
                if m.default is not None:
                    init_members.append(f"{m.name}_({self._default_value(m)})")
            if init_members:
                init_str = "\n    : " + "\n    , ".join(init_members)
                lines.append(f"{s.name}::{s.name}(){init_str}")
                lines.append("{")
                lines.append("}")
            else:
                lines.append(f"{s.name}::{s.name}() {{}}")

            # 参数化构造函数
            params = []
            init_list = []
            for m in s.members:
                cpp_type = self._cpp_type(m.py_type)
                const_ref_types = {"std::string", "std::vector"}
                if any(t in cpp_type for t in const_ref_types):
                    params.append(f"const {cpp_type}& {m.name}")
                    init_list.append(f"{m.name}_(std::move({m.name}))")
                else:
                    params.append(f"{cpp_type} {m.name}")
                    init_list.append(f"{m.name}_({m.name})")
            params_str = ",\n    ".join(params)
            init_str = "\n    : " + "\n    , ".join(init_list)
            lines.append("")
            lines.append(f"{s.name}::{s.name}({params_str}){init_str}")
            lines.append("{")
            lines.append("}")
        else:
            lines.append(f"{s.name}::{s.name}() {{}}")

        # 有实现的非虚方法
        for method in s.methods:
            if method.is_pure_virtual or method.body or method.is_virtual:
                continue
            params = []
            for p in method.params:
                cpp_type = self._cpp_type(p["type"])
                params.append(f"{cpp_type} {p['name']}")
            params_str = ", ".join(params)
            suffix = " const" if method.is_const else ""
            return_type = self._cpp_type(method.return_type)

            lines.append("")
            lines.append(f"{return_type} {s.name}::{method.name}({params_str}){suffix}")
            lines.append("{")
            if return_type == "void":
                lines.append("    // TODO: 实现")
            else:
                lines.append(f"    return {{}};  // TODO: 实现")
            lines.append("}")

        # namespace 结束
        if ns_open:
            lines.append("")
            for part in reversed(s.namespace.split("::")):
                lines.append(f"}}  // namespace {part}")

        return "\n".join(lines) + "\n"


# ============================================================
# 便捷接口：从 Python 类定义创建 C++ 代码
# ============================================================
def from_dict(data: dict) -> str:
    """从字典定义生成 C++ 代码

    字典格式:
    {
        "name": "ClassName",
        "namespace": "my::project",  // 可选
        "members": [
            {"name": "count", "type": "int", "default": "0"},
            {"name": "label", "type": "str", "default": '"unknown"'},
            {"name": "items", "type": "list[str]"},
        ],
        "methods": [
            {"name": "process", "return": "void", "params": [
                {"name": "input", "type": "int"}
            ]},
        ],
        "base": ["BaseClass"],  // 可选
        "description": "描述文字",  // 可选
        "includes": ["<memory>", "<algorithm>"],  // 可选
    }
    """
    members = [
        MemberSpec(
            name=m["name"],
            py_type=m["type"],
            default=m.get("default"),
        )
        for m in data.get("members", [])
    ]

    methods = []
    for m in data.get("methods", []):
        methods.append(MethodSpec(
            name=m["name"],
            return_type=m.get("return", "void"),
            params=m.get("params", []),
            is_const=m.get("const", False),
            is_virtual=m.get("virtual", False),
            is_static=m.get("static", False),
            is_pure_virtual=m.get("pure_virtual", False),
            body=m.get("body", ""),
        ))

    spec = ClassSpec(
        name=data["name"],
        namespace=data.get("namespace"),
        members=members,
        methods=methods,
        base_classes=data.get("base", []),
        include_headers=data.get("includes", []),
        description=data.get("description", ""),
    )

    gen = CppCodeGenerator(spec)
    header = gen.generate_header()
    source = gen.generate_source()
    return header, source


# ============================================================
# CLI 接口
# ============================================================
def run_demo():
    """运行演示：生成几个示例 C++ 类"""
    print("=" * 60)
    print("C++ 类代码生成器 — 演示")
    print("=" * 60)

    # 示例 1: 构建配置类
    build_config = {
        "name": "BuildConfig",
        "namespace": "builder",
        "description": "C++ 项目的构建配置",
        "members": [
            {"name": "project_name", "type": "str", "default": '"Untitled"'},
            {"name": "compiler", "type": "str", "default": '"g++"'},
            {"name": "cpp_standard", "type": "str", "default": '"c++17"'},
            {"name": "optimization", "type": "str", "default": '"-O2"'},
            {"name": "source_count", "type": "int", "default": "0"},
            {"name": "use_pch", "type": "bool", "default": "false"},
            {"name": "include_dirs", "type": "list[str]"},
            {"name": "defines", "type": "list[str]"},
        ],
        "methods": [
            {"name": "add_include_dir", "return": "void", "params": [
                {"name": "path", "type": "str"}
            ]},
            {"name": "add_define", "return": "void", "params": [
                {"name": "name", "type": "str"},
                {"name": "value", "type": "str"},
            ]},
            {"name": "to_command_line", "return": "str", "const": True},
        ],
        "includes": ["<sstream>"],
    }

    # 示例 2: 编译结果类
    compile_result = {
        "name": "CompileResult",
        "namespace": "builder",
        "description": "单个编译单元的结果",
        "members": [
            {"name": "source_file", "type": "str"},
            {"name": "object_file", "type": "str", "default": '""'},
            {"name": "success", "type": "bool", "default": "true"},
            {"name": "warnings", "type": "int", "default": "0"},
            {"name": "errors", "type": "int", "default": "0"},
            {"name": "duration_ms", "type": "double", "default": "0.0"},
            {"name": "output", "type": "str", "default": '""'},
        ],
    }

    # 示例 3: 抽象接口
    code_generator = {
        "name": "ICodeGenerator",
        "description": "代码生成器抽象接口",
        "methods": [
            {"name": "generate_header", "return": "str", "params": [
                {"name": "class_name", "type": "str"}
            ], "pure_virtual": True},
            {"name": "generate_source", "return": "str", "params": [
                {"name": "class_name", "type": "str"}
            ], "pure_virtual": True},
            {"name": "get_language", "return": "str", "const": True,
             "body": "return std::string(\"c++\");"},
        ],
        "includes": ["<string>"],
    }

    examples = [
        (build_config, "BuildConfig", "构建配置类"),
        (compile_result, "CompileResult", "编译结果类"),
        (code_generator, "ICodeGenerator", "抽象接口"),
    ]

    for data, name, desc in examples:
        print(f"\n{'─' * 60}")
        print(f"  [{desc}] {name}")
        print(f"{'─' * 60}")

        header, source = from_dict(data)

        print(f"\n  --- {name}.h ---")
        for line in header.split("\n"):
            print(f"  {line}")

        print(f"\n  --- {name}.cpp ---")
        for line in source.split("\n"):
            print(f"  {line}")

    print(f"\n{'=' * 60}")
    print("演示完成！使用 --json 参数从 JSON 文件生成实际代码文件")
    print("=" * 60)


def generate_from_json(json_path: str, output_dir: str = "."):
    """从 JSON 规格文件生成 C++ 代码"""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 支持单个类或类数组
    classes = data if isinstance(data, list) else [data]

    for cls_data in classes:
        header, source = from_dict(cls_data)
        name = cls_data["name"]

        # 写入文件
        os.makedirs(output_dir, exist_ok=True)
        header_path = os.path.join(output_dir, f"{name}.h")
        source_path = os.path.join(output_dir, f"{name}.cpp")

        with open(header_path, "w", encoding="utf-8") as f:
            f.write(header)
        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source)

        print(f"✅ 生成 {header_path}")
        print(f"✅ 生成 {source_path}")


def interactive_mode():
    """交互模式：逐步输入类定义"""
    print("C++ 类代码生成器 — 交互模式")
    print("=" * 50)
    name = input("类名: ").strip()
    if not name:
        print("已取消")
        return

    namespace = input("命名空间 (可选, 回车跳过): ").strip() or None

    print("\n输入成员变量 (格式: name:type 或 name:type=default, 空行结束):")
    print("  支持类型: int, str, bool, float, double, list[str], optional[int] 等")
    members = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        parts = line.split("=", 1)
        name_type = parts[0].split(":", 1)
        if len(name_type) == 2:
            members.append({
                "name": name_type[0].strip(),
                "type": name_type[1].strip(),
                "default": parts[1].strip() if len(parts) > 1 else None,
            })

    print("\n输入方法 (格式: return_type method_name(type1 param1, type2 param2), 空行结束):")
    methods = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        # 简单解析：return_type name(params)
        ret_and_rest = line.split(" ", 1)
        if len(ret_and_rest) < 2:
            continue
        return_type = ret_and_rest[0]
        name_and_params = ret_and_rest[1]
        method_parts = name_and_params.split("(", 1)
        method_name = method_parts[0].strip()
        params = []
        if len(method_parts) > 1:
            params_str = method_parts[1].rstrip(")")
            if params_str.strip():
                for p in params_str.split(","):
                    p = p.strip()
                    pt = p.split(" ")
                    if len(pt) >= 2:
                        params.append({"type": pt[0].strip(), "name": pt[1].strip()})
        methods.append({
            "name": method_name,
            "return": return_type,
            "params": params,
        })

    data = {
        "name": name,
        "members": members,
        "methods": methods,
    }
    if namespace:
        data["namespace"] = namespace

    header, source = from_dict(data)

    # 写入当前目录
    with open(f"{name}.h", "w", encoding="utf-8") as f:
        f.write(header)
    with open(f"{name}.cpp", "w", encoding="utf-8") as f:
        f.write(source)

    print(f"\n✅ 生成 {name}.h")
    print(f"✅ 生成 {name}.cpp")
    print(f"\n预览 {name}.h:")
    print(header)


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    elif "--json" in sys.argv:
        idx = sys.argv.index("--json")
        json_path = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        output_dir = sys.argv[idx + 2] if idx + 2 < len(sys.argv) else "."
        if not json_path:
            print("用法: python cpp_class_generator.py --json spec.json [output_dir]")
            sys.exit(1)
        generate_from_json(json_path, output_dir)
    elif len(sys.argv) == 1:
        run_demo()  # 默认运行演示
    else:
        print("用法:")
        print("  python cpp_class_generator.py              # 运行演示")
        print("  python cpp_class_generator.py --demo       # 运行演示")
        print("  python cpp_class_generator.py --json spec.json [output_dir]")
        print("  python cpp_class_generator.py --interact   # 交互模式")
