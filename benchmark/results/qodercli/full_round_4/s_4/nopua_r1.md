# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 1
## Duration: 148.23s

---

---

**Evidence from OpenAI Python SDK source:**

```python
# https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion.py
class ChatCompletion(BaseModel):
    id: str
    choices: List[Choice]
    created: int  # ← MUST be integer Unix timestamp
    model: str
    object: Literal["chat.completion"]

# https://github.com/openai/openai-python/blob/main/src/openai/types/chat/chat_completion_chunk.py  
class ChatCompletionChunk(BaseModel):
    id: str
    choices: List[Choice]
    created: int  # ← MUST be integer Unix timestamp
    model: str
    object: Literal["chat.completion.chunk"]
```
