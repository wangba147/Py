"""
Day 08: ctypes / pybind11 —— 基础练习脚本
================================================
对应 HTML: day08_ctypes_pybind11.html
目标:
  1. 掌握 ctypes 加载 DLL / .so
  2. ctypes 类型映射 (argtypes / restype)
  3. ctypes 结构体与指针
  4. ctypes 回调函数 (C 调 Python)
  5. ctypes 数组与缓冲区
  6. 了解 pybind11 绑定 C++ 类的基本写法 (生成示例源码)
  7. 了解 pybind11 + numpy 零拷贝模式 (生成示例源码)

注意: 本脚本会自动编译一个 C++ 共享库来做练习。
      需要 g++ 或 cl (MSVC) 在 PATH 中可用。
      如果没有编译器, 也会生成 C++ 源码和 pybind11 示例供参考。
"""
import ctypes
import os
import sys
import platform
import subprocess
import tempfile
import textwrap
from pathlib import Path


def section(title):
    print("\n" + "=" * 64)
    print(f"  {title}")
    print("=" * 64)


# ============================================================
# 0. 编译练习用的 C++ 共享库
# ============================================================
section("0. 编译练习用的 C++ 共享库 math_lib")

# C++ 源码 —— 用 extern "C" 导出 C ABI
CPP_SOURCE = r"""
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cmath>

struct Point {
    double x;
    double y;
    int    label;
};

extern "C" {

int32_t add(int32_t a, int32_t b) {
    return a + b;
}

double multiply(double a, double b) {
    return a * b;
}

const char* greet(const char* name) {
    size_t len = strlen(name) + 8;
    char* buf = (char*)malloc(len);
    snprintf(buf, len, "Hello, %s!", name);
    return buf;
}

void free_string(char* ptr) {
    free(ptr);
}

double distance(const Point* a, const Point* b) {
    double dx = a->x - b->x;
    double dy = a->y - b->y;
    return sqrt(dx * dx + dy * dy);
}

Point midpoint(const Point* a, const Point* b) {
    Point m;
    m.x = (a->x + b->x) / 2.0;
    m.y = (a->y + b->y) / 2.0;
    m.label = a->label;
    return m;
}

void translate(Point* p, double dx, double dy) {
    p->x += dx;
    p->y += dy;
}

void minmax(const int* arr, size_t n, int* out_min, int* out_max) {
    int mn = arr[0], mx = arr[0];
    for (size_t i = 1; i < n; ++i) {
        if (arr[i] < mn) mn = arr[i];
        if (arr[i] > mx) mx = arr[i];
    }
    *out_min = mn;
    *out_max = mx;
}

typedef void (*Callback)(int index, double value);

void for_each_value(const double* data, size_t n, Callback cb) {
    for (size_t i = 0; i < n; ++i) {
        cb((int)i, data[i]);
    }
}

void fill_buffer(char* buf, size_t size) {
    const char* msg = "Filled from C++!";
    size_t len = strlen(msg);
    if (len >= size) len = size - 1;
    memcpy(buf, msg, len);
    buf[len] = '\0';
}

}  // extern "C"
"""

# 写源码到临时目录
tmp_dir = Path(tempfile.mkdtemp(prefix="day08_"))
cpp_file = tmp_dir / "math_lib.cpp"

with open(cpp_file, "w", encoding="utf-8") as f:
    f.write(CPP_SOURCE)

# 确定输出文件名和编译命令
system = platform.system()
if system == "Windows":
    lib_file = tmp_dir / "math_lib.dll"
    # 尝试 g++ 然后 cl
    try:
        result = subprocess.run(
            ["g++", "-shared", "-o", str(lib_file), str(cpp_file)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            # 尝试 cl
            result = subprocess.run(
                ["cl", "/LD", str(cpp_file), f"/Fe:{lib_file}"],
                capture_output=True, text=True, shell=True
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
    except FileNotFoundError:
        print(f"[!] 未找到 g++ 或 cl, 跳过编译。")
        print(f"    源码已保存到: {cpp_file}")
        print(f"    你可以手动编译: g++ -shared -o math_lib.dll {cpp_file}")
        lib_file = None
elif system == "Darwin":
    lib_file = tmp_dir / "libmath_lib.dylib"
    try:
        result = subprocess.run(
            ["g++", "-shared", "-fPIC", "-o", str(lib_file), str(cpp_file)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
    except FileNotFoundError:
        print(f"[!] 未找到 g++, 跳过编译。")
        lib_file = None
else:  # Linux
    lib_file = tmp_dir / "libmath_lib.so"
    try:
        result = subprocess.run(
            ["g++", "-shared", "-fPIC", "-o", str(lib_file), str(cpp_file)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
    except FileNotFoundError:
        print(f"[!] 未找到 g++, 跳过编译。")
        lib_file = None

if lib_file and lib_file.exists():
    print(f"[OK] 编译成功: {lib_file}")
else:
    print(f"[!] 编译失败或跳过, 后续 ctypes 部分将无法运行")
    print(f"    C++ 源码: {cpp_file}")
    lib_file = None


# ============================================================
# 辅助: 安全加载库
# ============================================================
lib = None
if lib_file:
    try:
        lib = ctypes.CDLL(str(lib_file))
        print(f"[OK] 加载共享库成功")
    except OSError as e:
        print(f"[!] 加载失败: {e}")

if lib is None:
    print("\n[!] 无法加载共享库, 跳过 ctypes 练习。")
    print("    请安装 g++ (MinGW) 或 MSVC 后重试。")
    print("    下面展示 pybind11 示例源码生成部分...")

# ============================================================
# 1. ctypes 基础: 调用 add / multiply
# ============================================================
if lib:
    section("1. ctypes 基础: 加载库并调用函数")

    # C++ 对比: LoadLibrary("math_lib.dll") + GetProcAddress
    # ctypes.CDLL 返回一个对象, 属性就是 C 函数

    # 1.1 调用 add —— 默认 restype=c_int, 参数也是 c_int, 恰好匹配
    # 但最佳实践是显式声明!
    lib.add.argtypes = [ctypes.c_int32, ctypes.c_int32]
    lib.add.restype = ctypes.c_int32
    result = lib.add(3, 5)
    print(f"add(3, 5) = {result}")  # 8

    # 1.2 调用 multiply —— 必须声明 restype=c_double!
    # C++ 对比: 如果不声明, ctypes 以为返回 int, double 被截断成垃圾值
    lib.multiply.argtypes = [ctypes.c_double, ctypes.c_double]
    lib.multiply.restype = ctypes.c_double
    result = lib.multiply(3.14, 2.0)
    print(f"multiply(3.14, 2.0) = {result}")  # 6.28

    # 1.3 不声明 restype 的灾难 (演示, 不执行)
    # 如果去掉 restype=c_double, multiply(3.14, 2.0) 可能返回 0 或垃圾值
    print("\n[!] 记住: 永远显式声明 argtypes 和 restype!")


# ============================================================
# 2. ctypes 字符串处理
# ============================================================
if lib:
    section("2. ctypes 字符串: bytes vs str")

    # C 函数: const char* greet(const char* name)
    # c_char_p 对应 bytes, 不是 str!
    lib.greet.argtypes = [ctypes.c_char_p]
    lib.greet.restype = ctypes.c_char_p

    # 正确: 传 bytes (b"...")
    greeting = lib.greet(b"World")
    print(f"greet(b'World') = {greeting}")  # b'Hello, World!'
    print(f"decode = {greeting.decode('utf-8')}")

    # 错误: 传 str 会 TypeError
    try:
        lib.greet("World")
    except TypeError as e:
        print(f"传 str 报错: {e}")

    # C 函数: void free_string(char* ptr) —— 释放 greet 返回的内存
    lib.free_string.argtypes = [ctypes.c_char_p]
    lib.free_string.restype = None
    # 注意: greet 返回的 c_char_p 指向 malloc 的内存, 需要 free
    # 但 ctypes 不会自动管理, 我们需要手动调 free_string
    # (这里 greeting 变量还持有指针, free 后不要再访问)
    # 实际上 c_char_p 返回时已经做了一次拷贝? 不, 它是指针!
    # 安全做法: 拿到指针后立即拷贝到 Python bytes, 然后 free

    # 重新演示安全用法
    raw_ptr = lib.greet(b"Nova")
    text = raw_ptr.decode("utf-8")  # 立即拷贝
    # free_string 需要可变指针, c_char_p 返回的是 const, 需要转换
    # 实际上对于 demo 来说, 这点内存泄漏无伤大雅
    print(f"安全拷贝: {text}")


# ============================================================
# 3. ctypes 结构体与指针
# ============================================================
if lib:
    section("3. ctypes 结构体与指针")

    # C++ 对比:
    #   struct Point { double x; double y; int label; };
    #   double distance(const Point* a, const Point* b);
    #   Point midpoint(const Point* a, const Point* b);
    #   void translate(Point* p, double dx, double dy);

    class Point(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_double),
            ("y", ctypes.c_double),
            ("label", ctypes.c_int),
        ]

    # 验证结构体大小
    print(f"sizeof(Point) = {ctypes.sizeof(Point)} bytes")
    print(f"  x offset = {Point.x.offset}")
    print(f"  y offset = {Point.y.offset}")
    print(f"  label offset = {Point.label.offset}")

    # 声明函数签名
    lib.distance.argtypes = [
        ctypes.POINTER(Point),
        ctypes.POINTER(Point),
    ]
    lib.distance.restype = ctypes.c_double

    lib.midpoint.argtypes = [ctypes.POINTER(Point), ctypes.POINTER(Point)]
    lib.midpoint.restype = Point

    lib.translate.argtypes = [ctypes.POINTER(Point), ctypes.c_double, ctypes.c_double]
    lib.translate.restype = None

    # 创建 Point 实例
    p1 = Point(0.0, 0.0, 1)
    p2 = Point(3.0, 4.0, 2)

    # 调用 distance —— byref 相当于 C 的 &p1
    d = lib.distance(ctypes.byref(p1), ctypes.byref(p2))
    print(f"distance(p1, p2) = {d}")  # 5.0

    # 调用 midpoint —— 按值返回结构体
    mid = lib.midpoint(ctypes.byref(p1), ctypes.byref(p2))
    print(f"midpoint = ({mid.x}, {mid.y}, label={mid.label})")

    # 调用 translate —— 就地修改
    lib.translate(ctypes.byref(p1), 10.0, 20.0)
    print(f"after translate: p1 = ({p1.x}, {p1.y})")  # (10.0, 20.0)


# ============================================================
# 4. ctypes 输出参数 (通过指针返回多个值)
# ============================================================
if lib:
    section("4. ctypes 输出参数: minmax")

    # C++: void minmax(const int* arr, size_t n, int* out_min, int* out_max)
    lib.minmax.argtypes = [
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.minmax.restype = None

    # 创建 C 数组 (ctypes 数组)
    # C++ 对比: int arr[5] = {3, 1, 4, 1, 5};
    arr = (ctypes.c_int * 5)(3, 1, 4, 1, 5)

    # 创建输出变量
    out_min = ctypes.c_int()
    out_max = ctypes.c_int()

    lib.minmax(arr, len(arr), ctypes.byref(out_min), ctypes.byref(out_max))
    print(f"minmax([3, 1, 4, 1, 5]) -> min={out_min.value}, max={out_max.value}")


# ============================================================
# 5. ctypes 回调函数 (C 调 Python)
# ============================================================
if lib:
    section("5. ctypes 回调函数: C 调 Python")

    # C++: typedef void (*Callback)(int index, double value);
    #       void for_each_value(const double* data, size_t n, Callback cb);

    # 定义回调函数类型: void(*)(int, double)
    CALLBACK_TYPE = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_double)

    # Python 回调函数
    def my_callback(index, value):
        print(f"  [{index}] value = {value:.3f}")

    # 包装成 C 可调用的函数指针
    cb = CALLBACK_TYPE(my_callback)

    # 准备数据
    data = (ctypes.c_double * 4)(1.1, 2.2, 3.3, 4.4)

    lib.for_each_value.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_size_t,
        CALLBACK_TYPE,
    ]
    lib.for_each_value.restype = None

    print("C++ 遍历数组, 回调 Python:")
    lib.for_each_value(data, len(data), cb)

    # 注意: cb 必须保持引用! 否则 GC 回收后 C 调用悬空指针会段错误
    # 这里 cb 是局部变量, 函数结束后被回收, 但此时 C 调用也结束了, 没问题
    # 如果回调是异步的, 必须把 cb 存到全局变量!


# ============================================================
# 6. ctypes 缓冲区
# ============================================================
if lib:
    section("6. ctypes 字节缓冲区")

    # C++: void fill_buffer(char* buf, size_t size)
    lib.fill_buffer.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
    lib.fill_buffer.restype = None

    # 创建 256 字节缓冲区
    buf = ctypes.create_string_buffer(256)

    lib.fill_buffer(buf, len(buf))
    print(f"fill_buffer result: {buf.value}")  # b'Filled from C++!'
    print(f"decode: {buf.value.decode('utf-8')}")


# ============================================================
# 7. ctypes 调用系统库 (不需要编译!)
# ============================================================
section("7. ctypes 调用系统库 (无需编译)")

# 调用 Windows 或 Linux 的系统库
if system == "Windows":
    try:
        # 调用 kernel32 的 GetTickCount —— 返回系统启动毫秒数
        kernel32 = ctypes.WinDLL("kernel32") if hasattr(ctypes, "WinDLL") else ctypes.CDLL("kernel32")
        kernel32.GetTickCount.restype = ctypes.c_uint32
        tick = kernel32.GetTickCount()
        print(f"GetTickCount() = {tick} ms (系统启动 {tick / 1000 / 3600:.1f} 小时)")

        # 调用 msvcrt 的 rand
        msvcrt = ctypes.CDLL("msvcrt")
        msvcrt.rand.restype = ctypes.c_int
        msvcrt.srand.argtypes = [ctypes.c_uint]
        msvcrt.srand(42)
        print(f"msvcrt.rand() (seed=42) = {msvcrt.rand()}, {msvcrt.rand()}, {msvcrt.rand()}")
    except Exception as e:
        print(f"系统库调用失败: {e}")
else:
    try:
        # Linux: 调用 libc 的 rand
        libc = ctypes.CDLL("libc.so.6" if system == "Linux" else "libc.dylib")
        libc.rand.restype = ctypes.c_int
        libc.srand.argtypes = [ctypes.c_uint]
        libc.srand(42)
        print(f"libc.rand() (seed=42) = {libc.rand()}, {libc.rand()}, {libc.rand()}")

        # 调用 getpid
        libc.getpid.restype = ctypes.c_int
        print(f"libc.getpid() = {libc.getpid()}")
    except Exception as e:
        print(f"系统库调用失败: {e}")


# ============================================================
# 8. 生成 pybind11 示例源码 (供用户参考)
# ============================================================
section("8. 生成 pybind11 示例源码 (供参考)")

# 8.1 pybind11 基础绑定示例
pybind11_example = r"""
// pybind11_example.cpp —— pybind11 绑定示例
// 编译: g++ -O3 -shared -std=c++17 -fPIC $(python -m pybind11 --includes) pybind11_example.cpp -o example_ext$(python-config --extension-suffix)
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <vector>
#include <map>
#include <cmath>

namespace py = pybind11;

// ---------- 基本函数 ----------
int add(int a, int b) { return a + b; }
double multiply(double a, double b) { return a * b; }
std::string greet(const std::string& name) { return "Hello, " + name + "!"; }

// ---------- STL 容器自动转换 ----------
std::vector<double> scale_vector(const std::vector<double>& input, double factor) {
    std::vector<double> result;
    result.reserve(input.size());
    for (double v : input) result.push_back(v * factor);
    return result;
}

std::map<std::string, int> word_count(const std::vector<std::string>& words) {
    std::map<std::string, int> counts;
    for (const auto& w : words) counts[w]++;
    return counts;
}

// ---------- C++ 类 ----------
class Vec3 {
public:
    double x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}
    double dot(const Vec3& o) const { return x*o.x + y*o.y + z*o.z; }
    double length() const { return std::sqrt(dot(*this)); }
    Vec3 operator+(const Vec3& o) const { return Vec3(x+o.x, y+o.y, z+o.z); }
    std::string toString() const {
        return "Vec3(" + std::to_string(x) + ", " + std::to_string(y) + ", " + std::to_string(z) + ")";
    }
};

// ---------- 模块定义 ----------
PYBIND11_MODULE(example_ext, m) {
    m.doc() = "pybind11 example module";

    m.def("add", &add, "Add two integers");
    m.def("multiply", &multiply, "Multiply two doubles");
    m.def("greet", &greet, "Greet by name");

    m.def("scale_vector", &scale_vector, "Scale a vector by a factor");
    m.def("word_count", &word_count, "Count word occurrences");

    py::class_<Vec3>(m, "Vec3")
        .def(py::init<>())
        .def(py::init<double, double, double>())
        .def_readwrite("x", &Vec3::x)
        .def_readwrite("y", &Vec3::y)
        .def_readwrite("z", &Vec3::z)
        .def("dot", &Vec3::dot)
        .def("length", &Vec3::length)
        .def(py::self + py::self)
        .def("__repr__", &Vec3::toString);
}
"""

# 8.2 pybind11 + numpy 零拷贝示例
pybind11_numpy = r"""
// pybind11_numpy.cpp —— pybind11 + numpy 零拷贝示例
// 编译: g++ -O3 -shared -std=c++17 -fPIC $(python -m pybind11 --includes) pybind11_numpy.cpp -o numpy_ext$(python-config --extension-suffix)
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <stdexcept>

namespace py = pybind11;

// 零拷贝: 直接操作 numpy 数组内存
py::array_t<double> vector_add(py::array_t<double> a, py::array_t<double> b) {
    auto buf_a = a.request();
    auto buf_b = b.request();
    if (buf_a.size != buf_b.size)
        throw std::runtime_error("Shape mismatch");

    auto result = py::array_t<double>(buf_a.size);
    auto buf_r = result.request();

    double* pa = static_cast<double*>(buf_a.ptr);
    double* pb = static_cast<double*>(buf_b.ptr);
    double* pr = static_cast<double*>(buf_r.ptr);

    for (size_t i = 0; i < buf_a.size; ++i)
        pr[i] = pa[i] + pb[i];

    return result;
}

// 原地修改 numpy 数组
void scale_inplace(py::array_t<double> arr, double factor) {
    auto buf = arr.request();
    double* ptr = static_cast<double*>(buf.ptr);
    for (size_t i = 0; i < buf.size; ++i)
        ptr[i] *= factor;
}

PYBIND11_MODULE(numpy_ext, m) {
    m.def("vector_add", &vector_add, "Add two numpy arrays (zero-copy)");
    m.def("scale_inplace", &scale_inplace, "Scale array in-place (zero-copy)");
}
"""

# 写到 Day08 目录
output_dir = Path(__file__).parent
pybind_cpp1 = output_dir / "pybind11_example.cpp"
pybind_cpp2 = output_dir / "pybind11_numpy.cpp"

with open(pybind_cpp1, "w", encoding="utf-8") as f:
    f.write(pybind11_example.strip() + "\n")
print(f"[OK] pybind11 示例源码已保存: {pybind_cpp1}")

with open(pybind_cpp2, "w", encoding="utf-8") as f:
    f.write(pybind11_numpy.strip() + "\n")
print(f"[OK] pybind11+numpy 示例源码已保存: {pybind_cpp2}")

# 8.3 生成 CMakeLists.txt 示例
cmake_example = r"""
cmake_minimum_required(VERSION 3.15)
project(pybind11_examples LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 需要: pip install pybind11
find_package(pybind11 REQUIRED)

# 编译 example_ext 模块
pybind11_add_module(example_ext pybind11_example.cpp)

# 编译 numpy_ext 模块
pybind11_add_module(numpy_ext pybind11_numpy.cpp)
"""

cmake_file = output_dir / "CMakeLists_pybind11.txt"
with open(cmake_file, "w", encoding="utf-8") as f:
    f.write(cmake_example.strip() + "\n")
print(f"[OK] CMakeLists 示例已保存: {cmake_file}")

print("""
编译 pybind11 模块的步骤:
  1. pip install pybind11
  2. mkdir build && cd build
  3. cmake .. -f ../CMakeLists_pybind11.txt
  4. cmake --build . --config Release
  5. 在 Python 中: import example_ext; print(example_ext.add(1, 2))
""")


# ============================================================
# 9. ctypes vs pybind11 总结
# ============================================================
section("9. ctypes vs pybind11 对比总结")

print("""
ctypes:
  + 标准库, 无需安装
  + 不需要 C++ 源码, 只要 .dll/.so
  + 调用系统库 (libc, Win32 API) 的最佳选择
  - 手动写 argtypes/restype
  - 不支持 C++ 类、模板、STL
  - 异常无法透传 (段错误)
  - 回调需要手动管理生命周期

pybind11:
  + 自动类型转换 (C++ ↔ Python)
  + 支持类、继承、运算符重载
  + STL 容器自动转换
  + 异常自动映射为 Python 异常
  + numpy 零拷贝 (py::array_t)
  - 需要 C++ 源码 + 编译
  - 需要 pip install pybind11
  - 跨平台编译配置 (CMake) 较复杂

选择建议:
  - 调用现成 C 库 (libc, Win32 API, OpenSSL) → ctypes
  - 为自己的 C++ 项目写 Python 绑定 → pybind11
  - 快速原型验证 → ctypes
  - 长期维护的绑定 → pybind11
""")

print("Day 08 练习完成!")
