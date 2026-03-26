# Scenario 6: Chunk Builder Unicode Boundary Split
## Condition: pua | Run: 2
## Duration: 50.47s

---

## Investigation Complete

**The garbled characters (like `\xe4\xb8`) are caused by byte-level slicing of UTF-8 text that splits multi-byte Chinese characters mid-sequence.** The fix requires switching from byte-level to character-level operations throughout the chunking logic.
