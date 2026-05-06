# Day 2 Question — Agent and Tool-Use Internals

## Question

In my Conversion Engine's `composer.py` (line 253), I call `chat.completions.create()` with a plain text prompt — no `tools` parameter, no function-calling. **When a model "chooses" a tool via function-calling, what is actually happening at the token level, and how does the `tools` parameter mechanically change the model's generation behavior compared to my current prompt-stuffing approach?**

## Artifact Connections

- [`agent/composer.py:217-271`](../agent/composer.py) — LLM call using raw strings for tool-like logic.
- [`agent/server.py:173-300`](../agent/server.py) — Hardcoded 9-step hierarchical orchestration pipeline.

## Why It Matters

My current architecture is a deterministic pipeline that treats an LLM as a text generator inside a single hardcoded step. I cannot defend *why* I chose this over a native function-calling or a ReAct-style agent loop because I don't understand what function-calling actually does at the token level. Knowing the mechanical difference would allow me to add a defensible "Architecture Decision" section to my repo and decide if migrating to native tool-use would improve signal-contract enforcement or just add latency.
