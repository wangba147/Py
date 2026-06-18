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
