# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 2
## Duration: 435.82s

---

Now let me provide the final structured summary:

---

## 结构化调查报告

### 1. 已发现的问题 (Issues Found)

| # | 问题 | 严重程度 | 位置 |
|---|------|----------|------|
| 1 | **`paddlepaddle` 未安装** - requirements.txt 中声明但未实际安装 | 🔴 致命 | `requirements.txt:12` |
| 2 | **`use_gpu` 参数已废弃** - PaddleOCR 3.x 不再支持此参数，抛出 `ValueError: Unknown argument: use_gpu` | 🔴 致命 | `ocr_pipeline.py:113` |
| 3 | **`show_log` 参数无效** - PaddleOCR 3.x 不支持此参数，抛出 `ValueError: Unknown argument: show_log` | 🔴 致命 | `ocr_pipeline.py:118` |
| 4 | **结果解析格式不兼容** - PaddleOCR 3.x 返回 `OCRResult` 对象（dict-like），而非旧版的 `[(bbox, (text, conf)), ...]` 格式 | 🔴 致命 | `ocr_pipeline.py:200-205` |
| 5 | **GPU 无法使用** - 由于 `paddlepaddle` 未安装，即使配置 `use_gpu: true` 也无法使用 GPU 加速 | 🟠 高 | `ocr_config.yaml:3` |

### 2. 隐藏问题 (Hidden Issues)

| # | 问题 | 影响 | 位置 |
|---|------|------|------|
| 1 | **未使用的导入** - `ThreadPoolExecutor`, `as_completed`, `os`, `sys`, `field`, `Image` 导入但从未使用 | 代码整洁度 | `ocr_pipeline.py:18-29` |
| 2 | **硬编码 Unix 路径** - `tmp_dir: "/tmp/guwen_ocr"` 在 Windows 上会失败 | 跨平台兼容性 | `ocr_pipeline.py:50` |
| 3 | **临时文件清理不完整** - `rmdir()` 静默失败，留下孤儿文件 | 磁盘泄漏 | `ocr_pipeline.py:182-185` |
| 4 | **内存效率问题** - `convert_from_path` 一次性加载所有 PDF 页面到内存 | 大文件 OOM | `ocr_pipeline.py:163-168` |
| 5 | **缺少配置验证** - `confidence_threshold`, `dpi`, `box_merge_threshold` 无范围检查 | 配置错误风险 | `ocr_pipeline.py:37-53` |
| 6 | **线程安全问题** - `self._stats` 修改无锁保护 | 并行处理时竞态条件 | `ocr_pipeline.py:109` |
| 7 | **测试覆盖不足** - 无实际 OCR 处理、结果解析、GPU 回退测试 | 质量保障 | `test_ocr_pipeline.py` |
| 8 | **依赖缺失** - `pdf2image` 在 requirements.txt 中但未安装 | PDF 处理失败 | `requirements.txt:14` |

### 3. 根本原因 (Root Cause)

**主要原因**: 代码是为 **PaddleOCR 2.x** 编写的，但环境安装的是 **PaddleOCR 3.4.0**。这是一个重大版本升级，API 完全改变：

```
PaddleOCR 2.x → 3.x 破坏性变更:
├─ use_gpu 参数 → 移除 (改用 paddle.device.is_compiled_with_cuda() 自动检测)
├─ show_log 参数 → 移除
├─ ocr() 方法 → 废弃 (改用 predict())
└─ 返回格式 → 从 List[List[tuple]] 变为 List[OCRResult] (dict subclass)
```

**次要原因**: `paddlepaddle` 包未在虚拟环境中安装，导致：
- 无法进行 GPU 加速
- 甚至 CPU 推理也无法执行（因为 PaddleX 需要 `paddle` 模块来检测设备）

### 4. 推荐修复方案 (Recommended Fix)

#### 紧急修复 (使代码能运行):

```python
# 1. 安装缺失的依赖
pip install paddlepaddle paddleocr>=3.0.0 pdf2image

# 2. 修改 OCRPipeline.__init__ (行 111-119)
self._engine = PaddleOCR(
    lang=self.config.lang,
    # use_gpu 参数已移除 - PaddleOCR 3.x 自动检测
    # show_log 参数已移除
)

# 3. 修改 _process_image 方法 (行 189)
# 旧代码: result = self._engine.ocr(str(image_path), cls=self.config.use_angle_cls)
# 新代码:
result = self._engine.predict(str(image_path))

# 4. 修改结果解析逻辑 (行 200-205)
# 旧代码:
# for line_result in result[0]:
#     bbox, (text, conf) = line_result
# 
# 新代码:
for idx, text in enumerate(result[0]["rec_texts"]):
    conf = result[0]["rec_scores"][idx]
    bbox = result[0]["rec_polys"][idx]
    if conf >= self.config.confidence_threshold:
        lines.append(text)
        confidences.append(conf)
        bboxes.append(bbox)
```

#### 长期改进:

1. 添加配置值验证
2. 修复临时文件清理（使用 `shutil.rmtree`）
3. 流式处理大 PDF（逐页转换而非一次性加载）
4. 删除未使用的导入
5. 使用 `pathlib` 处理跨平台路径
6. 添加完整的单元测试

### 5. 调查步骤 (Steps Taken)

1. ✅ 读取源代码文件 (`ocr_pipeline.py`, `ocr_config.yaml`, `requirements.txt`)
2. ✅ 检查虚拟环境中实际安装的包 (`pip list`)
3. ✅ 验证模块导入行为
4. ✅ 检查 PaddleOCR 3.x API 签名和返回值格式
5. ✅ 分析 `paddlex` 设备检测机制
6. ✅ 验证 `use_gpu` 和 `show_log` 参数会导致 `ValueError`
7. ✅ 对比 PaddleOCR 2.x vs 3.x 返回格式差异
8. ✅ 识别代码中的隐藏问题（未使用导入、资源泄漏等）
9. ✅ 运行验证测试确认问题

### 6. 使用的工具 (Tools Used)

| 工具 | 用途 |
|------|------|
| `Read` | 读取源代码文件 |
| `Grep` | 搜索特定模式 |
| `Glob` | 查找相关文件 |
| `Bash` | 执行 Python 诊断脚本、检查包状态 |
| `pip list` | 验证已安装的包 |

### 7. 验证证据 (Verification Evidence)

```bash
# 测试 1: 模块导入成功（因为 PaddleOCR 只在实例化时才加载）
$ python -c "from src.data_processing.ocr_pipeline import OCRPipeline"
→ PASS (无错误)

# 测试 2: 实例化失败 - use_gpu 参数无效
$ python -c "OCRPipeline(OCRConfig(use_gpu=True))"
→ ValueError: Unknown argument: use_gpu

# 测试 3: 实例化失败 - show_log 参数无效  
$ python -c "OCRPipeline(OCRConfig())"
→ ValueError: Unknown argument: show_log

# 测试 4: paddlepaddle 未安装
$ pip list | grep paddlepaddle
→ (无输出)

# 测试 5: PaddleOCR 3.x 返回格式
>>> result = engine.predict(image)
>>> type(result[0])
<class 'paddlex.inference.pipelines.ocr.result.OCRResult'>
>>> result[0].keys()
dict_keys(['rec_texts', 'rec_polys', 'rec_scores', ...])
```

---

**总结**: 主要问题是 **PaddleOCR 主版本升级导致的 API 不兼容**，加上 **关键依赖 `paddlepaddle` 未安装**。修复需要更新代码以适配 PaddleOCR 3.x API，并安装缺失的依赖包。
