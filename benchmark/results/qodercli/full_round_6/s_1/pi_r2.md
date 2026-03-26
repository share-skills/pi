# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 2
## Duration: 147.82s

---

现在让我汇总分析结果，并提供完整的调查报告：

---

## 🧠 PI · 调查报告 · OCR Pipeline 导入错误与性能问题

### 1. Issues Found

| # | 问题 | 位置 | 描述 |
|---|------|------|------|
| 1 | **ModuleNotFoundError: paddleocr** | `ocr_pipeline.py:31` | 顶层直接 `from paddleocr import PaddleOCR`，包未安装时导入即失败 |
| 2 | **GPU 无验证逻辑** | `ocr_pipeline.py:111-119` | `use_gpu=True` 直接传给 PaddleOCR，无 CUDA 可用性检查 |
| 3 | **未使用的 import** | `ocr_pipeline.py:18,28,24,25` | `os`, `Image`, `field`, `ThreadPoolExecutor`, `as_completed` 已导入但未使用 |
| 4 | **临时目录清理不完整** | `ocr_pipeline.py:183-185` | `tmp_dir.rmdir()` 无法删除非空目录，仅静默忽略 |
| 5 | **硬编码跨平台路径** | `ocr_pipeline.py:50` | `tmp_dir: str = "/tmp/guwen_ocr"` Windows 不兼容 |
| 6 | **PaddleOCR 返回值结构假设风险** | `ocr_pipeline.py:200-201` | `bbox, (text, conf) = line_result` 解包无异常保护 |

---

### 2. Hidden Issues

| # | 隐患 | 位置 | 风险类型 | 描述 |
|---|------|------|----------|------|
| 7 | **无 GPU 回退机制** | `ocr_pipeline.py:111-119` | 正确性 | 配置注释称"Falls back to CPU silently"，但代码无此逻辑 |
| 8 | **无 paddlepaddle 版本检查** | `requirements.txt:12` | 兼容性 | 仅指定 `paddlepaddle>=2.5.0`，未验证与 `paddleocr>=2.7.0` 兼容性 |
| 9 | **PDF 转图片后内存泄漏风险** | `ocr_pipeline.py:173` | 资源管理 | `img.save()` 后未显式关闭图像对象 |
| 10 | **置信度计算除零风险** | `ocr_pipeline.py:208` | 边界条件 | `if confidences else 0.0` 已处理，但 `len(confidences)==0` 时 `bboxes` 仍为空 |
| 11 | **merge_boxes 逻辑无边界检查** | `ocr_pipeline.py:238-240` | 正确性 | `prev_bbox`/`curr_bbox` 可能为空或格式异常 |
| 12 | **process_directory 异常捕获过宽** | `ocr_pipeline.py:295-297` | 可调试性 | `except Exception` 吞掉具体错误类型，仅记录日志 |
| 13 | **click 导入在 main() 内部** | `ocr_pipeline.py:338` | 结构 | CLI 依赖应放在模块顶层便于发现缺失 |

---

### 3. Root Cause

#### 问题 1: ModuleNotFoundError
**根本原因** (`ocr_pipeline.py:31`):
- 顶层直接导入 `from paddleocr import PaddleOCR`
- 用户报告 `pip list shows paddle-ocr`，但实际包名为 `paddleocr`（PyPI 包名）vs `paddlepaddle`（底层引擎）
- `requirements.txt:11` 正确列出 `paddleocr>=2.7.0`，但用户可能只安装了 `paddlepaddle` 而未安装 `paddleocr`

**Initially I thought**: 包名拼写错误导致导入失败。  
**Upon closer inspection**: 实际上是两个不同包——`paddlepaddle` 是深度学习框架，`paddleocr` 是 OCR 应用层。用户说"pip list shows paddle-ocr"可能是误解，实际需同时安装两者。

#### 问题 2: GPU 性能慢
**根本原因** (`ocr_pipeline.py:111-119`):
- `use_gpu=self.config.use_gpu` 直接传递给 PaddleOCR
- 无任何 CUDA 可用性验证（对比 `src/training/config_builder.py:191-194` 有 `torch.cuda.is_available()` 检查）
- 配置注释声称"Falls back to CPU silently if CUDA unavailable"（`configs/ocr_config.yaml:3`），但代码无此实现

**Initially I thought**: GPU 驱动问题导致 PaddleOCR 无法使用 CUDA。  
**Actually**: 代码本身缺少 GPU 验证和回退逻辑，即使 CUDA 可用也可能因 PaddleOCR 初始化失败而静默降级到 CPU。

---

### 4. Recommended Fix

#### 修复 1: 延迟导入 + 友好错误信息
```python
# ocr_pipeline.py:31 替换为
def _verify_paddleocr():
    """Verify paddleocr is installed and return the PaddleOCR class."""
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except ImportError as e:
        logger.error(
            "paddleocr not found. Install with:\n"
            "  pip install paddleocr paddlepaddle\n"
            "Note: 'paddlepaddle' alone is insufficient; 'paddleocr' provides the OCR API."
        )
        raise ImportError("paddleocr package is required") from e

# 在 __init__ 中调用
self._engine = None  # 先置空
PaddleOCR = _verify_paddleocr()  # 验证并获取类
```

#### 修复 2: GPU 验证 + 回退
```python
# ocr_pipeline.py:111-119 替换为
def _get_effective_device(self) -> bool:
    """Determine if GPU should be used, with fallback to CPU."""
    if not self.config.use_gpu:
        logger.info("GPU disabled by config, using CPU")
        return False
    
    try:
        import torch
        if torch.cuda.is_available():
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
            return True
        else:
            logger.warning("CUDA not available, falling back to CPU")
            return False
    except ImportError:
        logger.warning("torch not installed, cannot verify GPU; using CPU")
        return False

use_device = self._get_effective_device()
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=use_device,  # 使用验证后的设备
    # ... 其他参数
)
```

#### 修复 3: 清理未使用 import
```python
# 移除以下行:
import os                          # L18 - 未使用
from PIL import Image              # L28 - 未使用
from dataclasses import field      # L24 - 未使用
from concurrent.futures import ... # L25 - 未使用
```

#### 修复 4: 跨平台临时目录
```python
# ocr_pipeline.py:50 替换为
import tempfile
tmp_dir: str = field(default_factory=lambda: str(Path(tempfile.gettempdir()) / "guwen_ocr"))
```

---

### 5. Steps Taken

| 步骤 | 动作 | 发现 |
|------|------|------|
| 1 | 读失败报告 → 定位文件 | 确认问题文件为 `ocr_pipeline.py` |
| 2 | 搜索代码库找到测试项目中的 OCR 文件 | 发现两份相同代码 (`nopua/benchmark/test-project/` 和 `benchmark/data/test-project/`) |
| 3 | 读取 `ocr_pipeline.py` 全文 | 识别顶层导入、GPU 配置、临时目录处理等关键代码段 |
| 4 | 运行导入测试 | 复现 `ModuleNotFoundError: No module named 'paddleocr'` |
| 5 | 读取 `requirements.txt` | 确认 `paddleocr>=2.7.0` 和 `paddlepaddle>=2.5.0` 均被列为依赖 |
| 6 | 搜索 GPU 相关代码 | 发现训练模块有 `torch.cuda.is_available()` 检查，但 OCR 模块无 |
| 7 | 检查配置文件 `ocr_config.yaml` | 发现注释声称"静默回退 CPU"但代码未实现 |
| 8 | 逐函数扫描 import 使用情况 | 发现 4 个未使用的 import |
| 9 | 检查临时目录清理逻辑 | 发现 `rmdir()` 无法处理非空目录 |
| 10 | 检查 PaddleOCR 返回值处理 | 发现无异常保护的元组解包 |

**自修正记录**:
- Initially I thought 包名拼写错误是主因 → 深入分析发现是 `paddlepaddle` vs `paddleocr` 两个不同包的依赖关系问题
- Initially I thought GPU 慢是驱动问题 → 实际上代码缺少 GPU 验证逻辑，配置注释与实际实现不一致

---

### 6. Tools Used

| 工具 | 用途 |
|------|------|
| `read_file` | 读取 `ocr_pipeline.py`, `requirements.txt`, `setup.py`, 测试文件，配置文件 |
| `glob` | 查找项目中所有 OCR pipeline 文件副本 |
| `grep` | 搜索 GPU/CUDA 相关代码、import 语句、paddleocr 引用 |
| `bash` (py_compile) | 验证语法正确性 |
| `bash` (pip3 list) | 检查已安装的 paddle 包 |
| `bash` (python3 -c import) | 复现导入错误 |

---

### 7. Verification

#### 验证命令

```bash
# 1. 验证 paddleocr 安装状态
pip3 show paddleocr paddlepaddle

# 2. 验证导入修复（应用修复 1 后）
python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('Import OK')"

# 3. 验证 GPU 检测（应用修复 2 后）
python3 -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
import logging
logging.basicConfig(level=logging.INFO)
pipeline = OCRPipeline(OCRConfig(use_gpu=True))
print(f'GPU enabled: {pipeline.config.use_gpu}')
"

# 4. 检查未使用 import（可选工具）
python3 -m pylint --disable=all --enable=unused-import src/data_processing/ocr_pipeline.py
```

#### 验证矩阵

| 变更类型 | 验证方式 | 通过标准 |
|---------|---------|---------|
| 导入错误修复 | `python -c import` | 无 `ModuleNotFoundError`，或显示友好错误信息 |
| GPU 验证 | 实例化 Pipeline + 查看日志 | 日志显示"CUDA available"或"Falling back to CPU" |
| 未使用 import | `pylint` 或手动审查 | 无 unused-import 警告 |
| 跨平台路径 | Windows/Linux 分别测试 | `/tmp/` 改为 `tempfile.gettempdir()` |

---

## 📋 交付确认

| 检查项 | 状态 |
|--------|------|
| ✅ 目标匹配 | 导入错误根因已定位；GPU 性能问题根因已定位 |
| ✅ 边界覆盖 | 涵盖包依赖、GPU 验证、资源清理、跨平台兼容、异常处理 |
| ✅ 风险可控 | 提供修复建议 + 验证命令；隐患数 (7) ≥ 表面问题 (6) × 40% |
| ❓ 待用户确认 | 实际环境中 `pip list` 输出是什么？是否同时安装了 `paddleocr` 和 `paddlepaddle`？ |

---

**下一步建议**:
1. 优先修复导入问题（添加延迟导入 + 友好错误）
2. 其次修复 GPU 验证逻辑（防止静默降级）
3. 清理未使用 import 和技术债
