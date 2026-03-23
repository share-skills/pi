# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 283.26s

---

---

## 结构化总结报告

### 1. 发现的问题 (Issues Found)

| # | 问题 | 位置 | 严重程度 |
|---|------|------|----------|
| 1 | **ModuleNotFoundError for paddleocr** - 非真实问题 | 第 31 行导入 | 误报 |
| 2 | **`use_gpu` 参数已失效** | 第 113 行 | 严重 |
| 3 | **`show_log` 参数已失效** | 第 118 行 | 严重 |
| 4 | **`cls` 参数在 ocr() 调用中已废弃** | 第 189 行 | 高 |
| 5 | **GPU 未启用 - 回退到 CPU** | 第 111-119 行 | 严重 |

**问题详情：**

1. **ModuleNotFoundError**: 包已正确安装为 `paddleocr` (版本 3.4.0)。导入语句正确。错误发生是因为 PaddleOCR 初始化失败（见问题 2-4），导致级联失败，看起来像导入错误。

2. **`use_gpu` 参数被移除**: PaddleOCR 3.x 完全移除了 `use_gpu` 参数。新 API 使用 `device='gpu'` 或 `device='cpu'`。传递 `use_gpu=True` 会导致 `ValueError: Unknown argument: use_gpu`。

3. **`show_log` 参数被移除**: PaddleOCR.__init__ 不再接受此参数。导致 `ValueError: Unknown argument: show_log`。

4. **`cls` 参数已废弃**: `ocr()` 方法现在期望 `use_textline_orientation=<bool>` 而不是 `cls=<bool>`。

5. **GPU 未激活**: 因为 `use_gpu=True` 参数无效，PaddleOCR 要么初始化失败，要么回退到 CPU 模式，这解释了用户报告的慢速性能问题。

---

### 2. 发现的隐藏问题 (Hidden Issues)

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **缺少 `paddlepaddle` 依赖** | requirements.txt 第 12 行 | GPU 支持损坏 |
| 2 | **临时目录清理不完整** | 第 181-185 行 | 磁盘空间泄漏 |
| 3 | **废弃的 API 方法 `ocr()`** | 第 189 行 | 未来兼容性风险 |
| 4 | **无设备自动检测回退** | 第 111-119 行 | 在无 GPU 系统上崩溃 |
| 5 | **未使用的导入** | 第 25-26 行、28 行 | 代码卫生问题 |

**隐藏问题详情：**

1. **PaddlePaddle 未安装**: 虚拟环境中只有 `paddleocr` 和 `paddlex`，但没有 `paddlepaddle` 本身。尝试使用 GPU 时，PaddleOCR 失败并显示 `ModuleNotFoundError: No module named 'paddle'`。GPU 加速需要 `paddlepaddle` 包。

2. **临时目录泄漏**: 第 181-185 行的清理代码只尝试 rmdir 空目录。如果 OCR 成功，会创建图像文件，目录无法删除。随时间推移会泄漏磁盘空间。

3. **废弃的 `ocr()` 方法**: `ocr()` 方法在 PaddleOCR 3.x 中被标记为 `@deprecated("Please use `predict` instead.")`。使用它有未来破坏的风险。

4. **无优雅降级**: 代码假设 GPU 可用（`use_gpu=True` 默认）。没有 try/catch 或回退到 CPU 的逻辑。

5. **未使用的导入**: 
   - 第 25 行：`ThreadPoolExecutor, as_completed` - 从未使用
   - 第 28 行：`Image` from PIL - 从未使用（pdf2image 处理转换）

---

### 3. 根本原因 (Root Cause)

**主要原因**: 代码是为 PaddleOCR 2.x API 编写的，但环境安装的是 PaddleOCR 3.4.0。主版本升级引入了破坏性变更：

| PaddleOCR 2.x | PaddleOCR 3.x |
|---------------|---------------|
| `use_gpu=True/False` | `device='gpu'/'cpu'` |
| `show_log=False` | 不支持（已移除） |
| `ocr(img, cls=...)` | `predict(img, use_textline_orientation=...)` |
| `det_model_dir` | `text_detection_model_dir` |
| `rec_model_dir` | `text_recognition_model_dir` |
| `use_angle_cls` | `use_textline_orientation` |

**次要原因**: `paddlepaddle` 后端包未安装，所以即使参数正确，GPU 加速也无法工作。

---

### 4. 推荐修复方案 (Recommended Fix)

#### 步骤 1: 更新 OCRConfig dataclass

```python
@dataclass
class OCRConfig:
    lang: str = "ch"
    device: str = "auto"  # 'auto', 'cpu', 'gpu', 'gpu:0' 等
    text_detection_model_dir: Optional[str] = None
    text_recognition_model_dir: Optional[str] = None
    textline_orientation_model_dir: Optional[str] = None
    use_textline_orientation: bool = True
    # ... 其余不变，移除旧字段名
```

#### 步骤 2: 修复 PaddleOCR 初始化

替换第 111-119 行，使用新的参数名称和 `device` 参数。

#### 步骤 3: 添加设备解析辅助方法

实现 `_resolve_device()` 方法，支持自动检测 GPU 并回退到 CPU。

#### 步骤 4: 修复 ocr() 调用

将第 189 行改为：
```python
result = self._engine.predict(
    str(image_path),
    use_textline_orientation=self.config.use_textline_orientation
)
```

#### 步骤 5: 修复临时目录清理

```python
finally:
    import shutil
    shutil.rmtree(tmp_dir)  # 删除目录及所有内容
```

#### 步骤 6: 安装 paddlepaddle

```bash
# 添加到 requirements.txt:
paddlepaddle>=3.0.0
```

#### 步骤 7: 移除未使用的导入

删除 `ThreadPoolExecutor` 和 `Image` 导入。

---

### 5. 调查步骤 (Steps Taken)

1. 读取源文件 `ocr_pipeline.py`（完整文件）
2. 验证包安装 - 确认 `paddleocr 3.4.0` 已安装
3. 测试导入 - 确认 `from paddleocr import PaddleOCR` 可工作
4. 调查 PaddleOCR API - 使用子代理阅读源代码
5. 测试 GPU 初始化 - 尝试 `PaddleOCR(device='gpu')`，因缺少 `paddle` 模块而失败
6. 检查方法签名 - 检查 `__init__`、`ocr()` 和 `predict()` 方法
7. 搜索废弃参数 - grep 查找 `use_gpu`、`show_log`、`cls` 使用情况
8. 审查测试文件 - 查看 `test_ocr_pipeline.py` 获取上下文

---

### 6. 使用的工具 (Tools Used)

| 工具 | 用途 |
|------|------|
| `Read` | 读取源文件 |
| `Glob` | 定位项目中的 Python 文件 |
| `Grep` | 搜索参数使用模式 |
| `Bash` | 测试导入、包检查、API 验证 |
| `Task (subagent)` | 深入调查 PaddleOCR 源代码 |
| `inspect` 模块 | 动态获取方法签名 |

---

### 7. 验证 (Verification)

**已验证的内容：**

✅ **paddleocr 包已安装**: `pip show paddleocr` 确认版本 3.4.0

✅ **导入语句正确**: `from paddleocr import PaddleOCR` 可工作

✅ **`use_gpu` 参数无效**: 测试确认 `ValueError: Unknown argument: use_gpu`

✅ **`show_log` 参数无效**: 测试确认 `ValueError: Unknown argument: show_log`

✅ **`cls` 参数已废弃**: 源代码显示 `@deprecated("Please use `predict` instead")`

✅ **GPU 需要 paddlepaddle**: 错误追踪显示尝试 GPU 时 `ModuleNotFoundError: No module named 'paddle'`

✅ **新 API 签名已确认**: `device='gpu'` 和 `use_textline_orientation=` 是正确的参数
