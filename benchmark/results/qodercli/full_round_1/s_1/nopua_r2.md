# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 214.72s

---

## 总结

**核心问题**: 这不是一个简单的"包没安装"问题，而是**PaddleOCR 3.x 重大版本升级导致的 API 不兼容**问题。

**关键发现**:
1. `paddlepaddle` 基础框架未安装（requirements.txt 有声明但环境缺失）
2. PaddleOCR 3.x 废弃了 `use_gpu` 参数，改用 `device='gpu'/'cpu'`
3. 返回结果格式与 2.x 不兼容，需要重写解析逻辑
4. 即使修复了导入问题，现有代码也无法正确工作

**性能慢的根本原因**: 即使安装了 GPU 版本的 paddlepaddle，当前代码传递的 `use_gpu=True` 参数会被 3.x 版本拒绝，导致回退到 CPU 模式运行 OCR。
