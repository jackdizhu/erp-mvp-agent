# Design: tool-call-validation

## Architecture

See [proposal.md](proposal.md) for full architecture diagram and approach.

### Key Decisions

1. **Intent rules as JSON config** - Separates pattern data from code, enables runtime reload
2. **Built-in fallback rules** - System operates even if config file is missing/invalid
3. **Two-message retry pattern** - Assistant reply + system guidance, keeps token count low
4. **has_danger flag tracking** - Simple boolean in `_handle_tool_calls()` to verify approval creation

### Module Dependencies

```
agent.py
  ├── intent_detector.py (new)
  │     └── config/intent_rules.json (new)
  ├── errors.py (modified - 3 new error constructors)
  └── approval.py (existing)
```

### Testing Strategy

- Unit tests for intent detection patterns (zh/en)
- Unit tests for error constructors
- Mock-based tests for retry flow
- Integration tests via API (4.1-4.5 in tasks.md)
