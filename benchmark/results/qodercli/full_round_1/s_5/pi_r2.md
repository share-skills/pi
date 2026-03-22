# Scenario 5: Training Data Synthesizer Silent Failure
## Condition: pi | Run: 2
## Duration: 129.33s

---

---

## 總結

### 根本原因

**合成器產生 0 樣本的核心原因：**

1. **配置中 API 密鑰爲空** (`api_key: ""`) → API 認證立即失敗
2. **靜默失敗模式** - 代碼第 229-232 行捕獲 `httpx.HTTPError`，記錄日誌但返回 `[]`，異常不傳播
3. **空結果仍寫入文件** - 第 306-315 行將空列表寫入輸出文件，創建了一個看似"成功但 0 樣本"的空文件

### 驗證證據

```
API key empty: True <- PRIMARY CAUSE OF FAILURE
Max retries: 0 <- No retry on transient failures
Source dir exists: False <- Secondary issue
```

### 修復建議（按優先級）

| 優先級 | 修復 | 影響 |
|--------|------|------|
| P0 | 添加 API key 驗證，為空時拋出異常 | 防止無聲認證失敗 |
| P0 | `generate()` 返回空時拋出異常 | 阻止空結果被當作成功 |
| P1 | 實現重試機制（`max_retries >= 3`） | 處理瞬態網絡/API 故障 |
| P1 | 記錄驗證拒絕的樣本及原因 | 便於調試質量問題 |
| P2 | HTTP client 使用上下文管理器 | 防止資源泄漏 |
| P2 | `import re` 移至模塊頂部 | 代碼規範 |

### 隱藏問題總覽

- **安全**: Prompt 注入風險（用戶文本直接插入提示）
- **可靠性**: 無超時控制、無指數退避、固定延遲不符合 API 限流
- **性能**: 批量大小配置未使用
- **兼容性**: 硬編碼 OpenAI 端點
- **健壮性**: 假設 LLM 總是返回有效 JSON
