# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 2
## Duration: 36.35s

---

# 🧠 PI · 深度调查 · OCR Pipeline 导入错误

## 1. Issues Found

| # | 问题 | 行号 |
|---|------|------|
| 1 | **ModuleNotFoundError: paddleocr** - 导入语句 `from paddleocr import PaddleOCR` 无法找到模块 | 24 |
| 2 | **GPU 配置可能未生效** - `use_gpu=True` 但用户报告速度慢，需验证 GPU 是否实际使用 | 16, 97-105 |
| 3 | **硬编码临时目录路径** - `/tmp/guwen_ocr` 在 Windows 上无效 | 27 |
| 4 | **缺失 pdf2image 依赖导入检查** - `_process_pdf` 方法动态导入但未在安装要求中声明 | 149 |
| 5 | **ThreadPoolExecutor 未使用** - 导入了并发工具但在 `process_directory` 中顺序执行 | 11, 213 |
| 6 | **异常处理不完善** - `_process_pdf` 的 finally 块仅尝试 rmdir，未清理图像文件 | 168-171 |
| 7 | **未使用的 sys 导入** - 导入了 sys 但从未使用 | 8 |

## 2. Hidden Issues

| # | 问题类型 | 描述 | 行号 |
|---|----------|------|------|
| 1 | **资源泄漏** | PDF 转图像的临时文件未清理，仅在 finally 中尝试 rmdir（会失败因为目录非空） | 168-171 |
| 2 | **跨平台兼容** | `tmp_dir` 默认值 `/tmp/guwen_ocr` 在 Windows 上无效，应使用 `tempfile.gettempdir()` | 27 |
| 3 | **性能问题** | `process_directory` 导入了 `ThreadPoolExecutor` 但未使用，顺序处理大量文件效率低 | 213-226 |
| 4 | **边界条件** | `_merge_text_boxes` 当 `line_height=0` 时设置 `gap_ratio=1.0` 可能导致错误分段 | 259-261 |
| 5 | **未处理异常** | `_process_image` 中 OCR 引擎调用无 try-except，引擎故障会导致崩溃 | 178 |
| 6 | **配置验证缺失** | `confidence_threshold` 未校验范围 (应在 0-1 之间) | 26 |
| 7 | **内存风险** | `convert_from_path` 一次性加载所有 PDF 页到内存，大 PDF 可能 OOM | 153-158 |
| 8 | **日志不完整** | 初始化时 `show_log=False` 但无其他调试输出，难以诊断 GPU 问题 | 104 |
| 9 | **线程安全** | `_stats` 字典在多线程环境下无锁保护（如果启用 ThreadPoolExecutor） | 92 |
| 10 | **未使用的导入** | `sys` 导入但未使用（仅在 main 中使用但不属于类定义） | 8 |

## 3. Root Cause

### 问题 1: ModuleNotFoundError
**根本原因**: PaddleOCR 的包名是 `paddleocr`（小写），但 pip 安装的是 `paddle-ocr`（带连字符）。Python 导入系统查找的是 `paddleocr` 模块目录。

```python
# 行 24 - 当前导入
from paddleocr import PaddleOCR
```

### 问题 2: GPU 未实际使用
**根本原因**: 
1. PaddleOCR 的 GPU 支持需要额外依赖（paddlepaddle-gpu），仅设置 `use_gpu=True` 不够
2. 无 GPU 检测逻辑，即使配置为 True 也可能回退到 CPU
3. 无日志确认 GPU 是否激活

```python
# 行 97-105 - 初始化时无 GPU 验证
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,  # 此参数可能被忽略如果 paddlepaddle-gpu 未安装
    ...
)
```

### 问题 3: 硬编码路径
**根本原因**: Unix 风格路径 `/tmp/guwen_ocr` 在 Windows 上不存在

```python
# 行 27 - 硬编码路径
tmp_dir: str = "/tmp/guwen_ocr"  # Windows 上应为 C:\Users\...\AppData\Local\Temp
```

## 4. Recommended Fix

### 修复 1: 解决导入错误并添加 GPU 检测

```python
# 修改前 (行 24)
from paddleocr import PaddleOCR

# 修改后
try:
    from paddleocr import PaddleOCR
except ImportError as e:
    raise ImportError(
        "PaddleOCR not found. Install with: pip install paddleocr paddlepaddle-gpu"
    ) from e
```

### 修复 2: 添加 GPU 检测和日志

```python
# 修改前 (行 97-105)
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=self.config.use_gpu,
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=False,
)

# 修改后
def _check_gpu_available(self) -> bool:
    """Check if GPU is actually available for PaddleOCR."""
    try:
        import paddle
        if paddle.device.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda_device_count()
            logger.info(f"GPU available: {gpu_count} device(s)")
            return gpu_count > 0
        else:
            logger.warning("PaddlePaddle not compiled with CUDA")
            return False
    except ImportError:
        logger.warning("Cannot import paddle to check GPU status")
        return False

# __init__ 中修改
actual_use_gpu = self.config.use_gpu and self._check_gpu_available()
logger.info(f"Initializing PaddleOCR with GPU={actual_use_gpu}")

self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=actual_use_gpu,
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=True,  # 启用日志便于调试
    log_file_dir=str(tmp_dir) if hasattr(self, 'tmp_dir') else None,
)
```

### 修复 3: 跨平台临时目录

```python
# 修改前 (行 27)
import tempfile

tmp_dir: str = field(default_factory=lambda: Path(tempfile.gettempdir()) / "guwen_ocr")
```

### 修复 4: 完善资源清理

```python
# 修改前 (行 168-171)
finally:
    try:
        tmp_dir.rmdir()
    except OSError:
        pass  # Directory not empty, but we ignore it

# 修改后
finally:
    import shutil
    try:
        shutil.rmtree(tmp_dir)  # 递归删除整个目录树
    except OSError as e:
        logger.warning(f"Failed to clean up temp dir {tmp_dir}: {e}")
```

### 修复 5: 启用并发处理

```python
# 修改 process_directory 方法 (行 213-226)
def process_directory(self, input_dir: str, output_dir: Optional[str] = None,
                      recursive: bool = True) -> Dict[str, List[OCRResult]]:
    # ... 前面代码不变 ...
    
    all_results = {}
    
    # 使用 ThreadPoolExecutor 并发处理
    with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
        future_to_file = {
            executor.submit(self.process_file, str(file_path)): file_path
            for file_path in files
        }
        
        for future in tqdm(as_completed(future_to_file), total=len(files), desc="OCR Processing"):
            file_path = future_to_file[future]
            try:
                results = future.result()
                all_results[str(file_path)] = results
                
                if output_dir:
                    self._save_results(file_path, results, Path(output_dir))
                    
                self._stats["processed"] += 1
            except Exception as e:
                logger.error(f"Failed to process {file_path.name}: {e}")
                self._stats["failed"] += 1
    
    return all_results
```

## 5. Steps Taken

1. **读取报错文件** - 完整阅读 `ocr_pipeline.py` 178 行代码
2. **分析导入链** - 追踪 `from paddleocr import PaddleOCR` 与 pip 包名的关系
3. **检查 GPU 配置流** - 从 config → __init__ → PaddleOCR 初始化，确认无 GPU 验证逻辑
4. **逐函数扫描** - 检查每个函数的参数校验、异常处理、资源管理、线程安全
5. **识别未使用代码** - 发现 `ThreadPoolExecutor` 导入但未使用，`sys` 导入但未使用
6. **跨平台检查** - 识别硬编码的 Unix 路径 `/tmp/guwen_ocr`
7. **搜索同类模式** - 检查所有临时文件操作，发现清理不完整问题
8. **数据流分析** - 追踪 `_stats` 的使用，发现多线程竞态风险

## 6. Tools Used

| 工具 | 用途 |
|------|------|
| `read_file` | 读取 ocr_pipeline.py 完整源码 |
| 静态分析 | 逐行检查导入、函数、异常处理、资源管理 |
| 数据流追踪 | 追踪 config → engine 初始化 → GPU 使用 |
| 模式匹配 | 搜索硬编码路径、未使用导入、缺失异常处理 |

## 7. Verification

### 验证命令

```bash
# 1. 验证 PaddleOCR 安装
pip show paddleocr
python -c "from paddleocr import PaddleOCR; print('Import OK')"

# 2. 验证 GPU 可用性
python -c "import paddle; print('CUDA compiled:', paddle.device.is_compiled_with_cuda()); print('GPU count:', paddle.device.cuda_device_count())"

# 3. 测试导入
cd D:\Projects\private-project
python -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('Import successful')"

# 4. 验证 GPU 实际使用
python -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
import logging
logging.basicConfig(level=logging.INFO)
pipeline = OCRPipeline(OCRConfig(use_gpu=True))
print('Pipeline initialized - check logs for GPU status')
"

# 5. 检查临时目录跨平台兼容
python -c "
import tempfile
from pathlib import Path
print('Default temp dir:', Path(tempfile.gettempdir()))
"
```

### 预期输出

修复后应看到：
- ✅ `Import successful` - 无 ModuleNotFoundError
- ✅ 日志显示 `GPU available: X device(s)` 或明确警告
- ✅ 临时目录自动适配操作系统
