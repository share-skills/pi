# Scenario 1: OCR Pipeline Import Error
## Condition: nopua | Run: 1
## Duration: 218.64s

---

---

## 摘要

| 问题 | 严重程度 | 修复难度 |
|------|---------|---------|
| `use_gpu` 参数不兼容 | 🔴 阻塞性 | 简单 |
| GPU 未被使用（性能慢） | 🔴 阻塞性 | 中等 |
| 文本合并无空格 | 🟠 高 | 简单 |
| 临时文件泄漏 | 🟠 高 | 简单 |
| 缺少 paddle 核心依赖 | 🟡 中 | 简单 |

**建议优先修复顺序**: 
1. 先修复 `use_gpu` → `device` 参数变更
2. 安装正确的 `paddlepaddle` 依赖
3. 修复文本合并逻辑
4. 修复临时文件清理
