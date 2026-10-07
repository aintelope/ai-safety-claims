# Inspect example

A real Inspect log (`corrections-mockllm.json`, Inspect 0.3.277, JSON log format, `mockllm/model`) from
the two-episode task in `corrections_task.py`, with matching frozen cases. The tests extract
`trials.jsonl` from it with `python -m validator import-inspect`. Fictional: the mock model's output means
nothing.

Regenerate: `inspect eval corrections_task.py --model mockllm/model --log-format json`.
