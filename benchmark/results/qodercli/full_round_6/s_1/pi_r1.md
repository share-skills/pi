# Scenario 1: OCR Pipeline Import Error
## Condition: pi | Run: 1
## Duration: 94.78s

---

Now I have completed my investigation. Let me provide the structured summary:

---

## 🧠 OCR Pipeline 問題調查報告

### 1. Issues Found

| # | 問題 | 位置 | 描述 |
|---|------|------|------|
| 1 | **ModuleNotFoundError: paddleocr** | `ocr_pipeline.py:31` | 頂層 import `from paddleocr import PaddleOCR` 導致模組無法載入，因 paddleocr 未安裝 |
| 2 | **GPU 靜默回退缺失** | `ocr_pipeline.py:111-119` | PaddleOCR 初始化時 `use_gpu=True`，但未檢查 CUDA 可用性，導致無 GPU 時可能崩潰或效能下降 |
| 3 | **臨時目錄洩漏** | `ocr_pipeline.py:183-185` | PDF 處理後的臨時目錄僅嘗試 `rmdir()`，非空時不處理，造成磁碟空間洩漏 |
| 4 | **跨平台路徑問題** | `ocr_pipeline.py:50` | 硬編碼 `/tmp/guwen_ocr`，Windows 系統將失敗 |
| 5 | **未使用的 imports** | `ocr_pipeline.py:18-25` | `os`, `sys`, `field`, `ThreadPoolExecutor`, `as_completed`, `Image` 已導入但未使用 |

---

### 2. Hidden Issues

| # | 隱藏問題 | 位置 | 風險類型 | 描述 |
|---|----------|------|----------|------|
| 6 | **資源洩漏風險** | `ocr_pipeline.py:173-174` | 資源管理 | PDF 轉圖片後未刪除臨時圖片文件，僅删除空目錄 |
| 7 | **異常處理不足** | `ocr_pipeline.py:189-193` | 正確性 | `_process_image` 未捕獲 PaddleOCR 可能的運行時異常 |
| 8 | **配置驗證缺失** | `ocr_pipeline.py:111-119` | 正確性 | `det_model_dir` 等路徑參數未驗證是否存在 |
| 9 | **線程安全問題** | `ocr_pipeline.py:109` | 線程安全 | `_stats` 字典在多线程環境下無鎖保護 |
| 10 | **邊界條件未處理** | `ocr_pipeline.py:208` | 正確性 | `confidences` 為空時 `sum()/len()` 會除零錯誤（雖有條件判斷但邏輯可優化） |
| 11 | **文檔與代碼不一致** | `ocr_config.yaml:3` | 可維護性 | 註釋稱"Falls back to CPU silently"，但代碼無此邏輯 |

---

### 3. Root Cause

**主要問題（Import Error）：**
- **ocr_pipeline.py:31** 在模組頂層直接導入 `from paddleocr import PaddleOCR`
- 當 paddleocr 未安裝時（`pip list` 確認未安裝），任何導入該模組的嘗試都會失敗
- 用戶報告 "package IS installed (pip list shows paddle-ocr)" — 但實際包名是 `paddleocr` 而非 `paddle-ocr`

**GPU 效能問題：**
- **ocr_pipeline.py:40, 113** `use_gpu=True` 是預設值，但：
  1. 未檢查 `torch.cuda.is_available()`
  2. 未檢查 PaddlePaddle 是否為 GPU 版本
  3. macOS (當前環境) 不支持 CUDA，PaddleOCR 會靜默回退到 CPU，但無警告日誌

**Initially I thought** 問題單純是包名拼寫錯誤（`paddle-ocr` vs `paddleocr`）。**Upon closer inspection**，根本原因是：
1. 依賴未安裝（requirements.txt 有列出但未執行 `pip install -r requirements.txt`）
2. 缺少延遲導入（lazy import）機制，導致即使不使用 OCR 功能也無法導入模組
3. GPU 檢測邏輯完全缺失

---

### 4. Recommended Fix

#### 修復 1: 延遲導入 + GPU 檢測

```python
# ocr_pipeline.py:18-31 修改前
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from PIL import Image
from tqdm import tqdm

from paddleocr import PaddleOCR  # ❌ 頂層導入
```

```python
# ocr_pipeline.py:18-31 修改後
import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
from PIL import Image
from tqdm import tqdm

# ✅ 延遲導入，避免導入時失敗
PaddleOCR = None  # placeholder

def _get_paddleocr():
    """Lazy import PaddleOCR to avoid import errors when not in use."""
    global PaddleOCR
    if PaddleOCR is None:
        try:
            from paddleocr import PaddleOCR as _PaddleOCR
            PaddleOCR = _PaddleOCR
        except ModuleNotFoundError as e:
            raise ImportError(
                "paddleocr not installed. Install with: pip install paddleocr>=2.7.0"
            ) from e
    return PaddleOCR
```

#### 修復 2: GPU 可用性檢查

```python
# ocr_pipeline.py:97-124 修改後 __init__ 方法
def __init__(self, config: Union[OCRConfig, str, Dict] = None,
             model_cache_dir: Optional[str] = None):
    if config is None:
        config = OCRConfig()
    elif isinstance(config, str):
        config = self._load_config(config)
    elif isinstance(config, dict):
        config = OCRConfig(**config)

    self.config = config
    self.model_cache_dir = model_cache_dir
    self._engine = None
    self._stats = {"processed": 0, "failed": 0, "total_pages": 0}

    # ✅ 檢查 GPU 可用性
    use_gpu = config.use_gpu
    if config.use_gpu:
        try:
            import torch
            if not torch.cuda.is_available():
                logger.warning(
                    "GPU requested but CUDA not available. Falling back to CPU."
                )
                use_gpu = False
        except ImportError:
            logger.warning("torch not installed, falling back to CPU")
            use_gpu = False

    PaddleOCRClass = _get_paddleocr()
    self._engine = PaddleOCRClass(
        lang=self.config.lang,
        use_gpu=use_gpu,
        use_angle_cls=self.config.use_angle_cls,
        det_model_dir=self.config.det_model_dir,
        rec_model_dir=self.config.rec_model_dir,
        cls_model_dir=self.config.cls_model_dir,
        show_log=False,
    )

    logger.info(
        f"OCR Pipeline initialized (lang={self.config.lang}, "
        f"gpu={use_gpu})"
    )
```

#### 修復 3: 臨時目錄清理 + 跨平台兼容

```python
# ocr_pipeline.py:36-53 修改後 OCRConfig
@dataclass
class OCRConfig:
    """Configuration for the OCR pipeline."""
    lang: str = "ch"
    use_gpu: bool = True
    det_model_dir: Optional[str] = None
    rec_model_dir: Optional[str] = None
    cls_model_dir: Optional[str] = None
    use_angle_cls: bool = True
    output_format: str = "txt"
    max_workers: int = 4
    dpi: int = 300
    confidence_threshold: float = 0.6
    page_separator: str = "\n---PAGE_BREAK---\n"
    tmp_dir: Optional[str] = None  # ✅ None 時使用 tempfile.gettempdir()
    enable_table_detection: bool = False
    merge_boxes: bool = True
    box_merge_threshold: float = 0.5

    def get_tmp_dir(self) -> Path:
        """Get platform-independent temp directory."""
        if self.tmp_dir is None:
            return Path(tempfile.gettempdir()) / "guwen_ocr"
        return Path(self.tmp_dir)
```

```python
# ocr_pipeline.py:154-185 修改後 _process_pdf
def _process_pdf(self, pdf_path: Path) -> List[OCRResult]:
    """Convert PDF to images and process each page."""
    from pdf2image import convert_from_path
    import shutil

    tmp_dir = self.config.get_tmp_dir() / pdf_path.stem
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=self.config.dpi,
            output_folder=str(tmp_dir),
            fmt="png",
        )

        results = []
        for i, img in enumerate(images):
            img_path = tmp_dir / f"page_{i+1:04d}.png"
            img.save(str(img_path))
            result = self._process_image(img_path, page_num=i + 1)
            results.append(result)
            self._stats["total_pages"] += 1

        self._stats["processed"] += 1
        return results

    finally:
        # ✅ 徹底清理臨時目錄（包含文件）
        try:
            shutil.rmtree(tmp_dir)
        except OSError as e:
            logger.warning(f"Failed to clean temp dir {tmp_dir}: {e}")
```

#### 修復 4: 移除未使用的 imports

```python
# ocr_pipeline.py:18-25 修改後
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass

import yaml
from PIL import Image
from tqdm import tqdm

# 移除了：os, sys, field, ThreadPoolExecutor, as_completed
```

---

### 5. Steps Taken

| 步驟 | 動作 | 發現 |
|------|------|------|
| 1 | 讀取 `ocr_pipeline.py` 全文 | 確認頂層 import paddleocr (L31) |
| 2 | 執行 `python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline"` | 復現 ModuleNotFoundError |
| 3 | 執行 `pip3 show paddleocr paddlepaddle` | 確認兩個包都未安裝 |
| 4 | 搜索 `use_gpu` 相關代碼 | 發現無 GPU 可用性檢查 (L113) |
| 5 | 檢查臨時目錄處理邏輯 | 發現 `rmdir()` 無法清理非空目錄 (L183-185) |
| 6 | 檢查 `tmp_dir` 預設值 | 發現硬編碼 `/tmp/guwen_ocr` (L50)，Windows 不相容 |
| 7 | 搜索同項目其他 GPU 相關代碼 | 發現 `training/trainer.py` 有 `torch.cuda.is_available()` 檢查，但 OCR 沒有 |
| 8 | 檢查 `__init__.py` | 發現有 lazy import 設計意圖（get_ocr_pipeline 函數），但 `ocr_pipeline.py` 本身未實現 |
| 9 | 檢查配置文件 `ocr_config.yaml` | 發現註釋稱"Falls back to CPU silently"，但代碼無此邏輯 |
| 10 | 分析 imports | 發現 6 個未使用的導入（os, sys, field, ThreadPoolExecutor, as_completed, Image） |

**自修正記錄：**
- **Initially I thought** 問題只是包名拼寫錯誤（用戶說 `paddle-ocr`，實際是 `paddleocr`）。
- **Upon closer inspection**，即使包名正確，頂層導入仍會在未安裝時導致整個模組無法導入，應改用延遲導入。
- **進一步分析發現**，GPU 問題不僅是用戶環境無 CUDA，代碼本身也缺少检测和回退邏輯。

---

### 6. Tools Used

| 工具 | 用途 |
|------|------|
| `Read` | 讀取 `ocr_pipeline.py`, `requirements.txt`, `test_ocr_pipeline.py`, `ocr_config.yaml`, `__init__.py` |
| `Grep` | 搜索 `paddleocr`, `use_gpu`, `gpu`, `tmp_dir` 等關鍵詞 |
| `Bash` | 執行導入測試、檢查包安裝狀態、Python 版本確認 |
| `Glob` | 查找 OCR 相關文件 |

---

### 7. Verification

#### 驗證命令

```bash
# 1. 安裝依賴後測試導入
cd /Users/hepin/IdeaProjects/pi/nopua/benchmark/test-project
pip install paddleocr>=2.7.0 paddlepaddle>=2.5.0

# 2. 測試導入（修復後應成功）
python3 -c "from src.data_processing.ocr_pipeline import OCRPipeline; print('Import OK')"

# 3. 測試 GPU 回退（無 CUDA 環境應顯示 warning 並繼續）
python3 -c "
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
import logging
logging.basicConfig(level=logging.WARNING)
pipeline = OCRPipeline(OCRConfig(use_gpu=True))
print(f'GPU enabled: {pipeline.config.use_gpu}')
"

# 4. 測試 PDF 處理後臨時文件清理
python3 -c "
from pathlib import Path
from src.data_processing.ocr_pipeline import OCRPipeline, OCRConfig
import tempfile
import os

# 檢查修復前後的臨時目錄行為
config = OCRConfig()
print(f'Temp dir: {config.get_tmp_dir()}')
"
```

#### 預期輸出（修復後）

```
# 導入測試
Import OK

# GPU 回退測試（無 CUDA 環境）
WARNING:src.data_processing.ocr_pipeline:GPU requested but CUDA not available. Falling back to CPU.
GPU enabled: True  # 配置保持 True，但實際使用 CPU

# 臨時目錄測試
Temp dir: /var/folders/.../guwen_ocr  # macOS 使用 tempfile.gettempdir()
```

---

### 交付確認

| 檢查項 | 狀態 |
|--------|------|
| ✅ Import Error 根因定位 | 頂層導入 + 依賴未安裝 |
| ✅ GPU 效能問題根因定位 | 缺少 CUDA 可用性檢查 |
| ✅ 隱藏問題發現 | 7 項（資源洩漏、跨平台、異常處理等） |
| ✅ 修復方案具體可執行 | 提供 4 項修復的代碼對比 |
| ✅ 驗證命令可直接運行 | 提供 4 組驗證命令 |

**建議優先級：**
1. 🔴 **P0**: 延遲導入（修復 1）— 解決無法導入的問題
2. 🔴 **P0**: GPU 檢測（修復 2）— 解決效能問題和潛在崩潰
3. 🟡 **P1**: 臨時目錄清理（修復 3）— 防止磁碟空間洩漏
4. 🟡 **P1**: 跨平台路徑（修復 3）— Windows 兼容性
5. ⚪ **P2**: 移除未使用 imports（修復 4）— 代碼清潔
