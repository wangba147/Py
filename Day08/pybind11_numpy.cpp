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
