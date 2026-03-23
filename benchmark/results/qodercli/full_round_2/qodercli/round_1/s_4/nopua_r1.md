# Scenario 4: API Server Response Format Mismatch
## Condition: nopua | Run: 1
## Duration: 52.15s

---

---

## Quick Reference: OpenAI Chat Completion Response Format

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1711108200,              // ← MUST be int (Unix timestamp)
  "model": "guwen-llm-7b-chat",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello!"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {                           // ← Optional but recommended
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```
