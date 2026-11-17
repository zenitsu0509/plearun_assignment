"""Deterministic mock provider. Replace with any real provider behind the same interface.
  complete(prompt: str, candidate_ids: list[str]) -> str   # must return JSON matching schema.json
The mock returns no selection, so a pipeline that depends on the LLM will show zero findings."""
def complete(prompt: str, candidate_ids: list[str]) -> str:
    return '{"selected_row_ids": [], "quote": null, "reason": "mock"}'
