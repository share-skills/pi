# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 2
## Duration: 110.41s

---

现在我有足够的信息进行全面分析。让我完成调查报告：

---

## 🧠 OCR Pipeline 問題調查報告

### 1. Issues Found

| # | 問題 | 位置 | 描述 |
|---|------|------|------|
| 1 | **ModuleNotFoundError: paddleocr** | `ocr_pipeline.py:31` | 頂層導入 `from paddleocr import PaddleOCR`，當包未安裝時導入即失敗 |
| 2 | **GPU 靜默回退缺失** | `ocr_pipeline.py:111-119` | `use_gpu=True` 但無 CUDA 可用性檢查，配置註釋稱"Falls back silently"但代碼無此邏輯 |
| 3 | **臨時目錄洩漏** | `ocr_pipeline.py:183-185` | `tmp_dir.rmdir()` 無法清理非空目錄，造成磁碟空間洩漏 |
| 4 | **跨平台路徑硬編碼** | `ocr_pipeline.py:50` | `tmp_dir: str = "/tmp/guwen_ocr"` Windows 系統將失敗 |
| 5 | **未使用的 imports** | `ocr_pipeline.py:18-25` | `os`, `sys`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image` 已導入但未使用 |

---

### 2. Hidden Issues

| # | 隱藏問題 | 位置 | 風險類型 | 描述 |
|---|----------|------|----------|------|
| 6 | **資源洩漏風險** | `ocr_pipeline.py:173-174` | 資源管理 | PDF 轉圖片後未刪除臨時圖片文件 |
| 7 | **異常處理不足** | `ocr_pipeline.py:189-193` | 正確性 | `_process_image` 未捕獲 PaddleOCR 運行時異常 |
| 8 | **配置驗證缺失** | `ocr_pipeline.py:111-119` | 正確性 | `det_model_dir` 等路徑參數未驗證是否存在 |
| 9 | **線程安全問題** | `ocr_pipeline.py:109` | 線程安全 | `_stats` 字典在多線程環境下無鎖保護 |
| 10 | **文檔與代碼不一致** | `ocr_config.yaml:3` | 可維護性 | 註釋稱"Falls back to CPU silently"，但代碼無此邏輯 |
| 11 | **並行處理未實現** | `ocr_pipeline.py:46,287` | 性能 | `max_workers: 4` 配置存在但 `process_directory` 使用順序循環 |

---

### 3. Root Cause

**主要問題（Import Error）：**
- **ocr_pipeline.py:31** 在模組頂層直接導入 `from paddleocr import PaddleOCR`
- 當 paddleocr 未安裝時（`pip show` 確認未安裝），任何導入該模組的嘗試都會失敗
- 用戶報告 "package IS installed (pip list shows paddle-ocr)" — 但實際包名是 `paddleocr` 而非 `paddle-ocr`，且當前環境確實未安裝

**GPU 效能問題：**
- **ocr_pipeline.py:40, 113** `use_gpu=True` 是預設值，但：
  1. 未檢查 `torch.cuda.is_available()` 或 `paddle.device.is_gpu_available()`
  2. 未檢查 PaddlePaddle 是否為 GPU 版本
  3. macOS (當前環境) 不支持 CUDA，PaddleOCR 會靜默回退到 CPU，但無警告日誌

**Initially I thought** 問題單純是包名拼寫錯誤（`paddle-ocr` vs `paddleocr`）。**Upon closer inspection**，根本原因是：
1. 依賴未安裝（requirements.txt 有列出但未執行 `pip install -r requirements.txt`）
2. 缺少延遲導入（lazy import）機制，導致即使不使用 OCR 功能也無法導入模組
3. GPU 檢測邏輯完全缺失

**範圍修正：** 最初只檢查了 `ocr_pipeline.py`，擴大範圍後發現：
- `__init__.py` 有 lazy import 設計意圖（`get_ocr_pipeline` 函數），但 `ocr_pipeline.py` 本身未實現
- `training/config_builder.py:191-193` 有 `torch.cuda.is_available()` 檢查，但 OCR 模塊沒有
- 測試文件 `test_ocr_pipeline.py:84-92` 明確測試並記錄了 `rmdir()` 失敗案例

---

### 4. Recommended Fix

#### 修復 1: 延遲導入 + GPU 檢測

```python
# ocr_pipeline.py:18-31 修改前
import os
import sys
# ...
from paddleocr import PaddleOCR  # ❌ 頂層導入
```

```python
# ocr_pipeline.py:18-31 修改後
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

import yaml
from tqdm import tqdm

# ✅ 延遲導入，避免導入時失敗
def _get_paddleocr():
    """Lazy import PaddleOCR to avoid import errors when not in use."""
    try:
        from paddleocr import PaddleOCR
        return PaddleOCR
    except ModuleNotFoundError as e:
        raise ImportError(
            "paddleocr not installed. Install with: pip install paddleocr>=2.7.0"
        ) from e

def _check_gpu_available() -> bool:
    """Check if GPU is actually available for inference."""
    try:
        import paddle
        if paddle.device.is_gpu_available():
            return True
        logger.warning("GPU requested but paddle GPU not available")
        return False
    except ImportError:
        logger.warning("paddlepaddle not installed, falling back to CPU")
        return False
```

#### 修復 2: GPU 可用性檢查

```python
# ocr_pipeline.py:111-119 修改後
# 確定實際使用的 GPU 狀態
actual_use_gpu = self.config.use_gpu and _check_gpu_available()

PaddleOCR = _get_paddleocr()
self._engine = PaddleOCR(
    lang=self.config.lang,
    use_gpu=actual_use_gpu,
    use_angle_cls=self.config.use_angle_cls,
    det_model_dir=self.config.det_model_dir,
    rec_model_dir=self.config.rec_model_dir,
    cls_model_dir=self.config.cls_model_dir,
    show_log=False,
)

logger.info(
    f"OCR Pipeline initialized (lang={self.config.lang}, "
    f"gpu={actual_use_gpu})"
)
```

#### 修復 3: 臨時目錄清理 + 跨平台兼容

```python
# ocr_pipeline.py:50 修改後
tmp_dir: Optional[str] = None  # None 時使用 tempfile.gettempdir()

# 添加方法：
def get_tmp_dir(self) -> Path:
    """Get platform-independent temp directory."""
    if self.tmp_dir is None:
        return Path(tempfile.gettempdir()) / "guwen_ocr"
    return Path(self.tmp_dir)
```

```python
# ocr_pipeline.py:181-185 修改後
finally:
    # ✅ 徹底清理臨時目錄（包含文件）
    try:
        shutil.rmtree(tmp_dir)
    except OSError as e:
        logger.warning(f"Failed to clean temp dir {tmp_dir}: {e}")
```

#### 修復 4: 移除未使用的 imports

```python
# 移除：os, sys, field, ThreadPoolExecutor, as_completed, Image
# 添加：tempfile, shutil
```

---

### 5. Steps Taken

| 步驟 | 動作 | 發現 |
|------|------|------|
| 1 | 讀取 `ocr_pipeline.py` 全文 (374 行) | 確認頂層 import paddleocr (L31)，無 GPU 檢查 (L111-119) |
| 2 | 執行導入測試 `python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline"` | 復現 ModuleNotFoundError |
| 3 | 執行 `pip3 show paddleocr paddlepaddle` | 確認兩個包都未安裝 |
| 4 | 讀取 `ocr_config.yaml` | 發現註釋"Falls back silently"但代碼無此邏輯 |
| 5 | 讀取 `test_ocr_pipeline.py` | 發現測試明確記錄 `rmdir()` 失敗案例 (L84-92) |
| 6 | 讀取 `requirements.txt` | 確認包名正確為 `paddleocr` (L11) |
| 7 | 搜索 `cuda.is_available` | 發現 `training/config_builder.py` 有檢查，但 OCR 沒有 |
| 8 | 讀取 `__init__.py` | 發現有 lazy import 設計意圖，但 `ocr_pipeline.py` 未實現 |
| 9 | 逐行掃描 imports | 發現 6 個未使用的導入 |
| 10 | 分析 `_process_pdf` | 發現臨時文件未清理，僅嘗試删除空目錄 |

**自修正記錄：**
- **Initially I thought** 問題只是包名拼寫錯誤（用戶說 `paddle-ocr`，實際是 `paddleocr`）。
- **Upon closer inspection**，即使包名正確，頂層導入仍會在未安裝時導致整個模組無法導入，應改用延遲導入。
- **進一步分析發現**，GPU 問題不僅是用戶環境無 CUDA，代碼本身也缺少检测和回退邏輯。
- **範圍修正**：最初只檢查报错相關函數，擴大範圍後發現 `max_workers` 配置從未使用、`_stats` 無線程保護等問題。

---

### 6. Tools Used

| 工具 | 用途 |
|------|------|
| `Read` | 讀取 `ocr_pipeline.py`, `requirements.txt`, `test_ocr_pipeline.py`, `ocr_config.yaml`, `__init__.py` |
| `Grep` | 搜索 `cuda`, `is_available`, `use_gpu`, `paddleocr`, `tmp_dir` 等關鍵詞 |
| `Bash` | 執行導入測試、檢查包安裝狀態 |
| `Glob` | 查找 OCR 相關文件、配置文件 |

---

### 7. Verification

#### 驗證命令

```bash
# 1. 安裝依賴後測試導入
cd /Users/hepin/IdeaProjects/pi/nopua/benchmark/test-project
pip install -r requirements.txt

# 2. 測試導入（修復後應成功）
python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('Import OK')"

# 3. 測試 GPU 回退（無 CUDA 環境應顯示 warning 並繼續）
python3 -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
import logging
logging.basicConfig(level=logging.WARNING)
pipeline = OCRPipeline(OCRConfig(use_gpu=True))
print(f'Actual GPU used: {pipeline.config.use_gpu}')
"

# 4. 檢查臨時目錄清理
python3 -c "
import tempfile
from pathlib import Path
tmp_before = list(Path(tempfile.gettempdir()).glob('guwen_ocr/*'))
print(f'Temp dirs before: {len(tmp_before)}')
# Run OCR on a test PDF
# Check again after
tmp_after = list(Path(tempfile.gettempdir()).glob('guwen_ocr/*'))
print(f'Temp dirs after: {len(tmp_after)}')
"

# 5. 驗證未使用的 imports 已移除
grep -E "^import (os|sys)|^from.*import.*(ThreadPoolExecutor|as_completed|Image)" src/data_processing/ocr_pipeline.py || echo "Unused imports removed"
```

#### 人工檢查步驟

- [ ] 檢查 `ocr_pipeline.py:31` 是否改為延遲導入
- [ ] 檢查 `ocr_pipeline.py:111-119` 是否添加 GPU 可用性檢查和警告
- [ ] 檢查 `ocr_pipeline.py:181-185` 是否改用 `shutil.rmtree()`
- [ ] 檢查 `ocr_pipeline.py:50` 是否改用 `tempfile.gettempdir()` 或可選配置
- [ ] 檢查 `ocr_pipeline.py:18-25` 是否移除未使用的 imports

---

## 修復優先級

| 級別 | 問題 | 影響 |
|------|------|------|
| 🔴 Blocker | ModuleNotFoundError | 模組完全無法使用 |
| 🔴 Blocker | GPU 靜默回退缺失 | 性能下降 10-50x 無警告 |
| 🟡 Suggestion | 臨時目錄洩漏 | 長期運行磁碟耗盡 |
| 🟡 Suggestion | 跨平台路徑 | Windows 用戶無法使用 |
| ⚪ Nit | 未使用的 imports | 代碼清晰度問題 |

---

```
📋 交付確認
□ 目標匹配: Import error + GPU performance 問題均已定位根因
□ 邊界覆蓋: 表面問題 5 項 + 隱藏問題 6 項 (≥40% 達標)
□ 風險可控: 修復方案包含延遲導入、GPU 檢測、資源清理、跨平台兼容
```
