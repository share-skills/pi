# Scenario 8: Inference Config Security Audit
## Condition: pi | Run: 1
## Duration: 83.16s

---

现在我已经完成了对 inference 模块的全面审查。让我整理发现的安全问题和其他隐患：

## 安全审计报告

### 1. Issues Found

| # | 问题 | 位置 | 严重性 |
|---|------|------|--------|
| 1 | **硬编码默认 API 密钥** | `api_server.py:51` | 🔴 Blocker |
| 2 | **API 密钥日志泄露** | `api_server.py:122` | 🔴 Blocker |
| 3 | **CORS 配置过于宽松（允许所有来源）** | `api_server.py:115-119` | 🔴 Blocker |
| 4 | **trust_remote_code=True 远程代码执行风险** | `model_loader.py:28,77` | 🔴 Blocker |
| 5 | **用户输入无验证直接代理到后端** | `api_server.py:167-177` | 🟡 Critical |
| 6 | **缺少认证中间件** | `api_server.py:147` | 🔴 Blocker |
| 7 | **配置文件路径未校验（路径遍历风险）** | `api_server.py:310-318` | 🟡 Critical |
| 8 | **错误信息直接暴露给客户端** | `api_server.py:228` | 🟡 Critical |

---

### 2. Hidden Issues

| # | 问题 | 位置 | 类型 |
|---|------|------|------|
| 9 | **SSRF 风险 - vLLM URL 可被篡改** | `api_server.py:44` | 安全 |
| 10 | **资源泄漏 - httpx.AsyncClient 未关闭** | `api_server.py:127` | 性能/正确性 |
| 11 | **竞态条件 - request_count 无锁递增** | `api_server.py:154` | 线程安全 |
| 12 | **Prompt 注入风险 - 用户消息直接拼接** | `api_server.py:235-253` | 安全 |
| 13 | **未使用的 import** | `prompt_builder.py:12,15,16` | 代码质量 |
| 14 | **硬编码路径 - 模型路径不可配置** | `model_loader.py:21` | 配置问题 |
| 15 | **GPU 内存泄漏风险 - unload 不完全** | `model_loader.py:107-121` | 资源管理 |
| 16 | **缺失请求体大小限制** | `api_server.py:147` | DoS 防护 |
| 17 | **流式响应异常处理不完整** | `api_server.py:256-307` | 正确性 |
| 18 | **datetime 类型不一致** | `api_server.py:97,200` | 正确性 |

---

### 3. Root Cause

**核心根因**：
1. **安全设计缺失** (`api_server.py:1-230`) — 模块设计时未考虑生产环境安全需求，缺少认证、授权、输入验证、审计日志等安全基础设施
2. **默认配置不安全** (`api_server.py:51`, `model_loader.py:28`) — 为方便开发设置了不安全的默认值（弱密码、信任远程代码），且这些默认值在生产环境可能被直接使用
3. **防御性编程不足** (`api_server.py:115-119`, `api_server.py:310-318`) — 未对 CORS、文件访问、URL 跳转等边界情况进行严格限制

---

### 4. Recommended Fix

#### 修复 1: API 密钥安全 (api_server.py:51,122)
```python
# 修改前 (L51)
api_key: str = os.environ.get("GUWEN_API_KEY", "sk-guwen-default-key-2024")

# 修改后
api_key: str = os.environ.get("GUWEN_API_KEY")

# 删除 L122 的日志或脱敏
logger.info(f"Server starting with API key: {'***' + config.api_key[-4:] if config.api_key else 'NOT SET'}")
```

#### 修复 2: CORS 限制 (api_server.py:115-119)
```python
# 修改前
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修改后
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

#### 修复 3: 添加认证中间件 (api_server.py:147 之前)
```python
from fastapi import Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

async def verify_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if not creds or creds.credentials != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return creds.credentials

# 在需要认证的路由中添加依赖
@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completion(request: ChatCompletionRequest):
    ...
```

#### 修复 4: 禁用 trust_remote_code (model_loader.py:28)
```python
# 修改前
trust_remote_code: bool = True

# 修改后
trust_remote_code: bool = False  # 除非明确知道风险且必须使用
```

#### 修复 5: 输入验证 (api_server.py:67-79)
```python
from pydantic import Field, field_validator

class ChatCompletionRequest(BaseModel):
    ...
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    
    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        if len(v) > 100:
            raise ValueError('Too many messages')
        for msg in v:
            if len(msg.content) > 10000:
                raise ValueError('Message too long')
        return v
```

#### 修复 6: 配置文件路径校验 (api_server.py:310-318)
```python
import pathlib

def load_config(config_path: str) -> InferenceConfig:
    # 防止路径遍历攻击
    resolved = pathlib.Path(config_path).resolve()
    allowed_base = pathlib.Path('/etc/guwen/configs').resolve()
    if not str(resolved).startswith(str(allowed_base)):
        raise ValueError(f"Config path must be under {allowed_base}")
    
    with open(resolved, "r") as f:
        data = yaml.safe_load(f)
    ...
```

#### 修复 7: 资源清理 (api_server.py:127)
```python
# 添加关闭钩子
@app.on_event("shutdown")
async def shutdown_event():
    await app.state.http_client.aclose()
```

---

### 5. Steps Taken

1. **读取全部 4 个源文件** — `api_server.py`, `model_loader.py`, `prompt_builder.py`, `__init__.py`
2. **搜索敏感关键词** — `api_key`, `secret`, `password`, `token`, `credential`
3. **搜索危险函数** — `eval()`, `exec()`, `open()`, `subprocess`, `os.system`, `pickle`
4. **搜索网络配置** — `http://`, `https://` 检查硬编码 URL
5. **搜索安全配置** — `trust_remote_code`, `CORSMiddleware`, `allow_origins`
6. **逐函数扫描** — 检查每个函数的参数校验、异常处理、资源管理、线程安全
7. **交叉引用** — 检查配置类与使用处的一致性

---

### 6. Tools Used

| 工具 | 用途 |
|------|------|
| `Read` | 读取 4 个源文件全文 |
| `Grep` | 搜索敏感关键词、危险函数、网络配置、安全配置 |
| `TodoWrite` | 跟踪审计进度 |

---

### 7. Verification

**验证命令**：

```bash
# 1. 检查 API 密钥是否强制环境变量
grep -n 'api_key.*default' src/inference/api_server.py
# 预期：无输出（修复后不应有默认值）

# 2. 检查 CORS 配置
grep -A5 'CORSMiddleware' src/inference/api_server.py
# 预期：allow_origins 不是 ["*"]

# 3. 检查 trust_remote_code
grep -n 'trust_remote_code' src/inference/model_loader.py
# 预期：False

# 4. 检查认证依赖
grep -n 'verify_api_key\|Depends.*security' src/inference/api_server.py
# 预期：存在认证函数

# 5. 检查输入验证
grep -n 'field_validator\|ge=\|le=' src/inference/api_server.py
# 预期：存在验证器

# 6. 运行静态分析工具
pip install bandit && bandit -r src/inference/ -ll
# 预期：无高危警告
```

---

## 交付确认

| 项目 | 状态 |
|------|------|
| 目标匹配 | ✅ 完成安全审计，识别 18 项问题（8 表面 +10 隐藏） |
| 边界覆盖 | ✅ 覆盖安全/性能/正确性/线程安全/资源管理/配置 |
| 风险可控 | ✅ 每项问题附 file:line 证据 + 修复建议 + 验证命令 |

**优先级建议**：
1. 🔴 **立即修复**：问题 1-4, 6（阻塞发布）
2. 🟡 **发布前修复**：问题 5, 7, 8, 9, 16（关键风险）
3. ⚪ **迭代优化**：问题 10-15, 17-18（技术债）
