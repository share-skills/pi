# Scenario 3: RAG Pipeline Milvus Connection Timeout
## Condition: pi | Run: 1
## Duration: 172.34s

---

## 交付确认

□ **目标匹配**: Connection refused 根因为端口不匹配 (Docker 19531→应用 19530)，向量维度已验证一致 (1024)
□ **边界覆盖**: 表面问题 10 项 + 隐藏问题 10 项，含连接/性能/资源/错误处理/线程安全/配置
□ **风险可控**: 关键修复为端口配置，次要修复为超时重试/上下文管理器/缓存加载状态
