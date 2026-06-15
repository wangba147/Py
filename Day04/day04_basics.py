#!/usr/bin/env python3
"""
Day 04: 面向对象编程（Python vs C++）— 练习脚本
每个知识点都带有 C++ 对比注释，面向 C++ 开发者
直接运行: python day04_basics.py
"""

# ============================================================
# 1. 类定义基础
# C++: class Dog { public: ... private: ... };
# Python: 一切都是动态的，无需声明类型
# ============================================================
print("=" * 60)
print("1. 类定义基础")
print("=" * 60)


class Dog:
    """Dog 类 — Python 版，对比 C++ class"""

    # 类属性 = C++ 中的 static 成员变量
    # C++: static const char* kingdom = "Animalia";
    kingdom = "Animalia"

    def __init__(self, name, age):
        """构造函数。对比 C++: Dog(string name, int age) : name_(name), age_(age) {}"""
        # Python 没有成员初始化列表，直接在 __init__ 中赋值
        # 属性也不需要预先声明，运行时会动态创建
        self.name = name
        self.age = age

    def bark(self):
        """普通成员方法。对比 C++: string bark() const { return name_ + " says Woof!"; }"""
        return f"{self.name} says Woof!"

    def celebrate_birthday(self):
        """修改实例属性。C++ 中需要显式返回或传引用"""
        self.age += 1
        return f"{self.name} is now {self.age}!"


# 实例化 — Python 不需要 new 关键字！
# C++: Dog* d = new Dog("Buddy", 3);  或  Dog d("Buddy", 3);
buddy = Dog("Buddy", 3)
print(f"  {buddy.bark()}")
print(f"  {buddy.celebrate_birthday()}")
print(f"  物种: {buddy.kingdom} (类属性，等效 C++ static)")
# Python 的类属性通过实例也能访问，但修改类属性要用 Dog.kingdom = xxx
print(f"  动态添加属性: ", end="")
buddy.color = "brown"  # C++ 中完全不可能！编译期就已经确定了所有成员
print(f"buddy.color = '{buddy.color}' (运行时动态添加)")


# ============================================================
# 2. 构造与析构：__init__ / __new__ / __del__
# C++: 构造函数 + 析构函数 (RAII 确定性析构)
# Python: __init__ + __del__（GC 调用，时机不确定）
# ============================================================
print("\n" + "=" * 60)
print("2. 构造与析构：__init__ / __new__ / __del__")
print("=" * 60)


class Resource:
    """演示 Python 对象生命周期"""

    def __new__(cls, name):
        """__new__ 在 __init__ 之前调用，负责创建实例。
        C++: operator new 分配内存
        一般不重写 __new__，除非实现单例或子类化不可变类型"""
        print(f"  1) __new__ 被调用 (分配内存, name={name})")
        instance = super().__new__(cls)
        return instance

    def __init__(self, name):
        """初始化实例。C++: 构造函数体"""
        print(f"  2) __init__ 被调用 (初始化, name={name})")
        self.name = name

    def __del__(self):
        """析构时调用。C++: ~Resource()
        ⚠️ Python 的 __del__ 不等于 C++ 析构函数！
        GC 何时调用不确定，不要依赖它做关键资源释放"""
        print(f"  3) __del__ 被调用 (GC 回收, name={self.name})")


print("  >>> 创建 Resource 对象")
r = Resource("test_resource")
print(f"  >>> r.name = {r.name}")

# 演示确定性资源释放的正确做法：上下文管理器
print("\n  >>> 资源管理的正确做法——上下文管理器（对比 C++ RAII）：")


class ManagedResource:
    """使用上下文管理器实现确定性资源释放
    C++ 等价物: RAII — 构造时获取资源，析构时释放"""

    def __init__(self, name):
        self.name = name
        print(f"      获取资源: {name}")
        self.active = True

    def do_work(self):
        """执行操作"""
        if self.active:
            return f"      执行操作 on {self.name}"
        return f"      资源 {self.name} 已释放！"

    def __enter__(self):
        """进入 with 块。C++: 构造函数执行后"""
        print(f"      __enter__: 准备使用 {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """离开 with 块。C++: 析构函数（离开作用域自动调用）
        这就是 Python 版的 RAII！"""
        self.active = False
        print(f"      __exit__: 释放 {self.name} (确定性！)")
        return False  # False = 不抑制异常


with ManagedResource("FileHandle") as res:
    print(res.do_work())
# with 块结束后，__exit__ 被调用，资源确定性地释放！
print("  (with 块结束后，资源已确定释放)")


# ============================================================
# 3. self vs this
# C++: this 是隐式指针，关键字
# Python: self 是显式参数，约定（非关键字）
# ============================================================
print("\n" + "=" * 60)
print("3. self vs this — 显式 vs 隐式")
print("=" * 60)


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self, amount=1):
        """self 是显式参数。C++: void increment(int amount=1) { this->value += amount; }"""
        self.value += amount

    def get_value(self):
        return self.value


c = Counter()
c.increment(5)
# 两种调用方式完全等价！
# C++: c.increment(5) 和 Counter::increment(&c, 5) 完全不同
Counter.increment(c, 3)  # self 就是 c，只是显式传入而已
print(f"  c.value = {c.value} (应该为 8)")

# self 不是关键字！可以改名字（但千万别这么做）
class Weird:
    def method(this_is_not_self):  # 不推荐！仅供演示
        this_is_not_self.data = 42

w = Weird()
w.method()
print(f"  Weird().data = {w.data} (self 只是约定，不是关键字)")


# ============================================================
# 4. 访问控制：约定 vs 关键字
# C++: public / private / protected (编译器强制)
# Python: _protected / __private (约定 + 名称改写)
# ============================================================
print("\n" + "=" * 60)
print("4. 访问控制")
print("=" * 60)


class AccessDemo:
    def __init__(self):
        self.public_attr = "我是公开的"          # C++: public
        self._protected_attr = "我是约定的保护"   # C++: protected
        self.__private_attr = "我是名称改写的"    # C++: private (但不完全一样)

    def _protected_method(self):
        """_ 前缀 = '请勿在类外调用' 的约定"""
        return "protected method"

    def __private_method(self):
        """__ 前缀触发名称改写 (name mangling)：变成 _AccessDemo__private_method"""
        return "private method"

    def access_private(self):
        """类内部可以访问私有成员"""
        return self.__private_method()


demo = AccessDemo()
print(f"  public_attr: {demo.public_attr}")
print(f"  _protected_attr: {demo._protected_attr}  (能访问但 IDE 会警告)")

try:
    print(demo.__private_attr)
except AttributeError as e:
    print(f"  __private_attr 直接访问: AttributeError! {e}")

# 但名称改写不是真正的私有——还是可以绕过
print(f"  绕过名称改写: {demo._AccessDemo__private_attr}")
# Python 哲学: "We're all consenting adults here"
# 对比: C++ private 在编译期强制，完全无法从外部访问


# ============================================================
# 5. @property — Python 的 getter/setter 替代品
# C++: getXxx() / setXxx() 方法
# Python: @property 让属性访问像普通属性，背后却有逻辑
# ============================================================
print("\n" + "=" * 60)
print("5. @property 装饰器")
print("=" * 60)


class Temperature:
    """温度类 — 演示 @property 的 getter/setter/deleter"""

    def __init__(self, celsius=0):
        self._celsius = celsius

    @property
    def celsius(self):
        """getter: 像访问属性一样使用"""
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        """setter: 赋值时自动触发验证"""
        if value < -273.15:
            raise ValueError(f"温度 {value}°C 低于绝对零度!")
        self._celsius = value

    @celsius.deleter
    def celsius(self, val_del=None):
        """deleter: del obj.celsius 时触发"""
        print("  重置温度到 0°C")
        self._celsius = 0

    @property
    def fahrenheit(self):
        """只读计算属性 — C++: double getFahrenheit() const"""
        return self._celsius * 9 / 5 + 32

    @property
    def kelvin(self):
        """另一个只读属性"""
        return self._celsius + 273.15


t = Temperature(25)
print(f"  初始: {t.celsius}°C = {t.fahrenheit}°F = {t.kelvin}K")

t.celsius = 30  # 触发 setter，像普通赋值一样自然
print(f"  修改后: {t.celsius}°C = {t.fahrenheit}°F")

try:
    t.celsius = -300  # setter 中的验证会抛出异常
except ValueError as e:
    print(f"  验证拒绝: {e}")

# 只读属性不能赋值
try:
    t.fahrenheit = 100
except AttributeError as e:
    print(f"  fahrenheit 是只读属性: {e}")

del t.celsius  # 触发 deleter
print(f"  删除后: {t.celsius}°C")


# ============================================================
# 6. 继承：单继承、多重继承、MRO
# C++: class Dog : public Animal { ... };
# Python: class Dog(Animal): ...
# ============================================================
print("\n" + "=" * 60)
print("6. 继承与 MRO")
print("=" * 60)


# 6.1 单继承
class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        return f"{self.name} makes a sound"


class Dog2(Animal):
    def speak(self):
        # super() 调用父类方法，类似 C++ 中 Animal::speak()
        # 但 super() 在多重继承中更强大——按 MRO 查找
        return f"{self.name} says Woof!"


class Cat(Animal):
    def speak(self):
        return f"{self.name} says Meow!"


animals = [Dog2("Buddy"), Cat("Whiskers"), Animal("Generic")]
for a in animals:
    print(f"  {a.speak()}")


# 6.2 多重继承与菱形继承
print("\n  --- 菱形继承演示 ---")


class A:
    def method(self):
        print("    A.method")


class B(A):
    def method(self):
        super().method()  # 按 MRO 找下一个，而不是硬编码父类
        print("    B.method")


class C(A):
    def method(self):
        super().method()
        print("    C.method")


class D(B, C):
    """菱形继承！D -> B -> C -> A -> object
    C++ 中这种菱形继承需要 virtual 继承来避免重复基类问题"""
    def method(self):
        super().method()  # MRO: D -> B -> C -> A
        print("    D.method")


print(f"  D 的 MRO (方法解析顺序):")
for cls in D.__mro__:
    print(f"    {cls.__name__}", end="")
print()

d = D()
print("  调用 D().method():")
d.method()
# 输出: A.method -> C.method -> B.method -> D.method
# 注意 A 只被调用一次！Python 的 MRO 自动处理了菱形继承
# C++ 不用 virtual 继承的话，A 会在 B 和 C 中各有一份


# ============================================================
# 7. 多态：鸭子类型 vs 虚函数
# C++: 虚函数 + vtable，必须继承共同基类
# Python: 鸭子类型——"如果它走起来像鸭子..."
# ============================================================
print("\n" + "=" * 60)
print("7. 鸭子类型多态")
print("=" * 60)


class Wolf:
    def howl(self):
        return "Awooo!"


class Duck:
    def quack(self):
        return "Quack!"


class Robot:
    def beep(self):
        return "Beep boop!"


# 它们没有共同基类！
# 但都可以传入 process_voice，只要有 speak 属性（即使是动态添加的）
def process_voice(thing):
    """处理任何有 'voice' 方法的对象——鸭子类型"""
    return thing.voice()


# 动态添加方法（Python 独有！C++ 做不到）
Wolf.voice = lambda self: self.howl()
Duck.voice = lambda self: self.quack()
Robot.voice = lambda self: self.beep()

for obj in [Wolf(), Duck(), Robot()]:
    print(f"  {type(obj).__name__}: {process_voice(obj)}")

# C++ 中做同样的事情需要:
#   1. 定义一个 IVoice 接口（纯虚类）
#   2. 让 Wolf、Duck、Robot 都继承它
#   3. 或者用 std::variant + std::visit


# ============================================================
# 8. 魔法方法（dunder methods）
# C++: operator+, operator==, operator<< 等
# Python: __add__, __eq__, __str__ 等
# ============================================================
print("\n" + "=" * 60)
print("8. 魔法方法 — 运算符重载")
print("=" * 60)


class Vector2D:
    """2D 向量 — 演示常用魔法方法"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        """调试表示，eval(repr(obj)) 应能重建对象"""
        return f"Vector2D({self.x}, {self.y})"

    def __str__(self):
        """用户友好表示，print() 调用"""
        return f"({self.x}, {self.y})"

    def __eq__(self, other):
        """operator=="""
        if not isinstance(other, Vector2D):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __add__(self, other):
        """operator+"""
        if isinstance(other, Vector2D):
            return Vector2D(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __sub__(self, other):
        """operator-"""
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        """operator* (标量乘法)"""
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar):
        """反向乘法: scalar * vector"""
        return self.__mul__(scalar)

    def __abs__(self):
        """向量长度, C++: 通常作为自由函数 norm(v) 或 v.length()"""
        return (self.x**2 + self.y**2) ** 0.5

    def __bool__(self):
        """operator bool — 零向量为 False"""
        return abs(self) > 0

    def __getitem__(self, index):
        """operator[] — v[0] = x, v[1] = y"""
        return (self.x, self.y)[index]

    def __len__(self):
        """len() — 维度数。C++ 中一般没有对应物"""
        return 2

    def __neg__(self):
        """一元取反: -v"""
        return Vector2D(-self.x, -self.y)


v1 = Vector2D(3, 4)
v2 = Vector2D(1, 2)

print(f"  v1 = {v1}, v2 = {v2}")
print(f"  v1 + v2 = {v1 + v2}")
print(f"  v1 - v2 = {v1 - v2}")
print(f"  v1 * 3 = {v1 * 3}")
print(f"  2 * v1 = {2 * v1}     (__rmul__)")
print(f"  |v1| = {abs(v1):.1f}")
print(f"  v1 == v2? {v1 == v2}")
print(f"  v1 == Vector2D(3, 4)? {v1 == Vector2D(3, 4)}")
print(f"  bool(v1) = {bool(v1)}, bool(Vector2D(0,0)) = {bool(Vector2D(0, 0))}")
print(f"  v1[0] = {v1[0]}, v1[1] = {v1[1]}")
print(f"  len(v1) = {len(v1)}")
print(f"  -v1 = {-v1}")


# ============================================================
# 9. @classmethod 和 @staticmethod
# C++: static 成员函数
# Python: @classmethod (接收类) / @staticmethod (不接收特殊参数)
# ============================================================
print("\n" + "=" * 60)
print("9. @classmethod 和 @staticmethod")
print("=" * 60)


class BuildSystem:
    """构建系统 — 演示三种方法类型"""

    # 类属性: C++ static 成员
    default_compiler = "g++"
    _build_count = 0

    def __init__(self, project_name, compiler=None):
        self.project_name = project_name
        self.compiler = compiler or BuildSystem.default_compiler

    # 普通实例方法: 第一个参数是 self
    # C++: void build() { ... }
    def build(self):
        BuildSystem._build_count += 1
        return f"[#{BuildSystem._build_count}] 构建 {self.project_name} 使用 {self.compiler}"

    # 类方法: 第一个参数是 cls (类本身)
    # C++: static 成员函数 + 知道类类型
    @classmethod
    def get_build_count(cls):
        """类方法可以访问类属性，常用来做替代构造器"""
        return cls._build_count

    @classmethod
    def with_cmake(cls, project_name):
        """替代构造器 (factory method pattern)
        使用: BuildSystem.with_cmake('MyProject')"""
        return cls(project_name, compiler="cmake")

    # 静态方法: 没有特殊的第一个参数
    # C++: static 成员函数（不能访问 this）
    @staticmethod
    def validate_target(target):
        """纯工具函数，不需要访问类或实例"""
        return target in {"debug", "release", "relwithdebinfo"}


# 对比三种调用方式
bs1 = BuildSystem("Engine")
bs2 = BuildSystem.with_cmake("Renderer")  # 类方法作为工厂

print(f"  {bs1.build()}")
print(f"  {bs2.build()}")
print(f"  总构建次数: {BuildSystem.get_build_count()}")
print(f"  validate_target('debug'): {BuildSystem.validate_target('debug')}")
print(f"  validate_target('fastbuild'): {BuildSystem.validate_target('fastbuild')}")


# ============================================================
# 10. dataclass — C++ struct 的升级版
# C++: struct CppProject { string name; vector<string> sources; ... };
# Python: @dataclass 自动生成 __init__/__repr__/__eq__
# ============================================================
print("\n" + "=" * 60)
print("10. dataclass")
print("=" * 60)

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CompileUnit:
    """编译单元 — 对比 C++ 中的 struct"""
    source_file: str
    object_file: str = ""
    includes: List[str] = field(default_factory=list)  # 可变默认值安全处理
    defines: List[str] = field(default_factory=list)

    def __post_init__(self):
        """dataclass 的 __init__ 之后调用 — 用于派生字段"""
        if not self.object_file:
            self.object_file = self.source_file.replace(".cpp", ".o")


@dataclass(order=True)  # 自动生成所有比较方法
class BuildTarget:
    """构建目标 — order=True 添加 <, <=, >, >="""
    name: str
    priority: int = 0
    dependencies: List[str] = field(default_factory=list, compare=False)  # 不参与比较


@dataclass(frozen=True)  # 不可变！类似 C++ const 对象
class CompilerFlags:
    """编译选项 — frozen=True 使其不可变"""
    standard: str = "c++17"
    optimization: str = "-O2"
    warnings: str = "-Wall -Wextra"

    def to_string(self) -> str:
        """dataclass 可以有自定义方法！"""
        return f"-std={self.standard} {self.optimization} {self.warnings}"


cu1 = CompileUnit("main.cpp")
cu2 = CompileUnit("utils.cpp", defines=["DEBUG"])

print(f"  cu1: {cu1}")
print(f"  cu2: {cu2}")
print(f"  cu1 == cu2: {cu1 == cu2}")
print(f"  cu1 == CompileUnit('main.cpp'): {cu1 == CompileUnit('main.cpp')}")

t1 = BuildTarget("App", priority=1)
t2 = BuildTarget("Lib", priority=2)
print(f"\n  构建目标排序:")
for t in sorted([t2, t1]):  # order=True 自动支持排序
    print(f"    {t.name} (priority={t.priority})")

flags = CompilerFlags()
print(f"\n  编译选项: {flags.to_string()}")
try:
    flags.standard = "c++20"  # frozen=True 禁止修改！
except Exception as e:
    print(f"  frozen 禁止修改: {type(e).__name__}")


# ============================================================
# 11. ABC 抽象基类
# C++: class Interface { virtual void method() = 0; };
# Python: class Interface(ABC): @abstractmethod def method(self): ...
# ============================================================
print("\n" + "=" * 60)
print("11. ABC 抽象基类")
print("=" * 60)

from abc import ABC, abstractmethod


class ICodeGenerator(ABC):
    """代码生成器接口 — 类似 C++ 纯虚基类"""

    @abstractmethod
    def generate_header(self, class_name: str) -> str:
        """生成头文件。C++: virtual string generateHeader(string) = 0;"""
        ...

    @abstractmethod
    def generate_impl(self, class_name: str) -> str:
        """生成实现文件。C++: virtual string generateImpl(string) = 0;"""
        ...

    def generate(self, class_name: str):
        """模板方法 — 有具体实现的普通方法"""
        header = self.generate_header(class_name)
        impl = self.generate_impl(class_name)
        return header + "\n" + impl


# 尝试实例化抽象类
try:
    gen = ICodeGenerator()
except TypeError as e:
    print(f"  无法实例化抽象类: {e}")
    print("  (类似于 C++ 中不能实例化有纯虚函数的类)")


class SimpleCodeGen(ICodeGenerator):
    """具体实现 — 必须实现所有抽象方法"""

    def generate_header(self, class_name: str) -> str:
        return (
            f"#pragma once\n"
            f"class {class_name} {{\n"
            f"public:\n"
            f"    {class_name}();\n"
            f"    ~{class_name}();\n"
            f"private:\n"
            f"    int data_;\n"
            f"}};\n"
        )

    def generate_impl(self, class_name: str) -> str:
        return (
            f'#include "{class_name}.h"\n'
            f"{class_name}::{class_name}() : data_(0) {{}}\n"
            f"{class_name}::~{class_name}() {{}}\n"
        )


gen = SimpleCodeGen()
code = gen.generate("MyClass")
print(f"  生成的代码:\n{code}")


# ============================================================
# 12. Mixin 模式
# C++: 多重继承 / CRTP / 组合模式
# Python: Mixin 类 — 每个只做一件事，自由组合
# ============================================================
print("=" * 60)
print("12. Mixin 模式")
print("=" * 60)


class LoggingMixin:
    """日志 Mixin: 为类添加日志功能"""

    def log(self, level, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {type(self).__name__}: {msg}")


class TimerMixin:
    """计时 Mixin: 为类添加计时功能"""

    def measure(self, label, func, *args, **kwargs):
        import time
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        if hasattr(self, 'log'):
            self.log("INFO", f"{label}: {elapsed_ms:.2f}ms")
        else:
            print(f"{label}: {elapsed_ms:.2f}ms")
        return result, elapsed_ms


class SerializerMixin:
    """序列化 Mixin: 导出公共属性"""

    def to_dict(self):
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

    def to_json(self):
        import json
        return json.dumps(self.to_dict(), default=str, indent=2)


# 自由组合！
class CppProjectAnalyzer(LoggingMixin, TimerMixin, SerializerMixin):
    """C++ 项目分析器 — 组合三个 Mixin"""

    def __init__(self, project_path):
        self.project_path = project_path
        self.file_count = 0
        self.total_lines = 0
        self.log("INFO", f"初始化分析器: {project_path}")

    def scan(self):
        """扫描项目目录"""
        import os

        self.log("INFO", "开始扫描...")

        def _scan():
            count = 0
            lines = 0
            if os.path.isdir(self.project_path):
                for root, _, files in os.walk(self.project_path):
                    for f in files:
                        if f.endswith(('.cpp', '.h', '.hpp', '.cc')):
                            count += 1
                            try:
                                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as fp:
                                    lines += sum(1 for _ in fp)
                            except Exception:
                                pass
            self.file_count = count
            self.total_lines = lines
            return count

        _, ms = self.measure("扫描完成", _scan)
        self.log("INFO", f"找到 {self.file_count} 个C++文件, {self.total_lines} 行代码")


# 使用 Mixin 组合的类
analyzer = CppProjectAnalyzer(r"D:\Code\WorkBuddy\每日Py")
analyzer.scan()
print(f"\n  to_dict: {analyzer.to_dict()}")
print(f"  to_json (前100字符): {analyzer.to_json()[:100]}...")


# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 60)
print("Day 04 完成！总结")
print("=" * 60)
print("""
  ✅ 类定义: Python 动态 vs C++ 静态，无头文件
  ✅ 构造/析构: __init__ vs 构造函数，__del__ ≠ C++ 析构
  ✅ self vs this: 显式参数 vs 隐式指针
  ✅ 访问控制: _ / __ 约定 vs public/private 编译器强制
  ✅ @property: getter/setter 自然语法
  ✅ 继承: 多重继承 + MRO vs virtual 继承
  ✅ 多态: 鸭子类型 vs 虚函数
  ✅ 魔法方法: __add__/__eq__ vs operator+/operator==
  ✅ @classmethod / @staticmethod vs static 成员函数
  ✅ dataclass: 自动生成 boilerplate，比 struct 更强大
  ✅ ABC: @abstractmethod vs = 0 纯虚函数
  ✅ Mixin: 多重继承的实战模式

  下一个主题: Day 05 — 模块、包与标准库
""")
