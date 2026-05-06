# The Token-Level Mechanics of Tool-Use vs. Prompt-Stuffing

*Written by Lidya Dagnaw for Rahel Samson, whose agent in `agent/email_agent.py` uses "Return valid JSON" to simulate tool decisions.*

In your Conversion Engine's `composer.py`, you currently use **Prompt-Stuffing**. You provide a list of signals and rules in a raw string, and the model generates a raw string in return. When you move to **Native Tool-Use (Function Calling)**, the fundamental physics of token generation changes.

## The Load-Bearing Mechanism: Logit Masking

To understand the difference, we have to look at the **Unconstrained** vs. **Constrained** decoding processes.

### 1. Prompt-Stuffing (Unconstrained Decoding)
In your current `composer.py`, when the model reaches the point where it should "decide" a variant, it has the entire vocabulary of ~100k tokens available. The probability distribution (logits) for the next token might look like this:
- `"signal"`: 0.75
- `"exploratory"`: 0.20
- `"generic"`: 0.04
- `"I"`: 0.01

The model *prefers* to pick a valid variant because of your prompt instructions, but **nothing mechanically prevents it** from picking a token that violates your schema (like `"generic"` or beginning a sentence instead of a JSON key).

### 2. Function-Calling/JSON Mode (Constrained Decoding)
When you use `tools=[]` or `response_format={"type": "json_object"}`, the inference engine applies a technique called **Grammar-Based Decoding** or **Logit Masking**.

At every single step of generation:
1. The engine tracks where it is in your JSON schema or function definition.
2. If the schema requires a specific key (e.g., `"variant"`), the engine identifies all tokens in the vocabulary that *cannot* possibly be part of that key or the opening quote.
3. **The probabilities for all illegal tokens are set to $-\infty$.**

This means if your schema says `variant` must be `["signal_grounded", "exploratory"]`, and the model has already generated `{"variant": "`, the engine will mask out every token in the library except those starting with `s` or `e`. The model *cannot* generate a third option because that option's probability is zero at the hardware level.

## Showing the Difference

```python
# --- Prompt-Stuffing (what Rahel has) ---
messages = [{"role": "user", "content": """
  Available tools: book_calendar_slot(email, time)
  If you need to call a tool, return JSON: {"action": "...", "args": {...}}
  Otherwise return email text.
  Compose outreach for cto@novapay.io
"""}]
response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
text = response.choices[0].message.content  # raw string — you parse it yourself
# finish_reason: "stop" — model just ended a sentence
# No guarantee of valid JSON. Could output a typo like "book_calender_slot".

# --- Function-Calling (tools parameter) ---
tools = [{"type": "function", "function": {
    "name": "book_calendar_slot",
    "parameters": {"type": "object", "properties": {
        "email": {"type": "string"},
        "time":  {"type": "string"}
    }, "required": ["email", "time"]}
}}]
response = client.chat.completions.create(
    model="gpt-4o-mini", messages=messages, tools=tools, tool_choice="auto"
)
call = response.choices[0].message.tool_calls[0]
print(call.function.name)       # "book_calendar_slot" — guaranteed match
print(call.function.arguments)  # schema-valid JSON — logit masking enforced it
# finish_reason: "tool_calls" — generation stopped at schema completion, not sentence end
```

The observable proof: with function-calling, `finish_reason` is `"tool_calls"`, not `"stop"`. The model didn't end a sentence — the engine halted it because the schema was complete.

## Why P-023 (HubSpot) and P-026 (Cal.com) Fail

In Rahel's probes, she sees "model failures" where the model generates a valid-looking decision that the scaffolding then executes incorrectly.

- **Without Tool-Use:** The model is just writing a story that looks like JSON. If it generates `{"booking": "double_booked"}`, it's just following a linguistic pattern. The failure is **Attributional**—the model was never actually "calling" a tool; it was just predicting the next characters in a string.
- **With Tool-Use:** The failure shifts. If a model calls a `book_call()` tool with wrong arguments, it is a **Reasoning failure**. But if it generates a string that *looks* like a tool call but isn't in your schema, that is a **Scaffolding failure**.

## Toolformer: The "Control Token" Pattern
Native tool-use is often implemented using special **Control Tokens**. As established in Schick et al. (2023), models can be trained to emit a specific token (like `<API>`) which serves as a signal to the scaffolding to pause generation, execute a function, and feed the result back as a new input token. 

When you use prompt-stuffing, you are essentially asking the model to "act" like it's emitting a control token using regular text. This is why it's brittle.

## The Answer in One Paragraph
When a model "chooses" a tool via function-calling, it isn't just following prompt advice; it is operating under **Logit Masking**, where the inference engine mechanically sets the probability of all non-compliant tokens to zero at every step. While prompt-stuffing relies on the model's semantic preference to stay within bounds, function-calling enforces structural compliance at the hardware level, shifting failures from "syntax hallucinations" to either "reasoning errors" (wrong logic) or "scaffolding errors" (poorly defined constraints).

## What This Changes for the Conversion Engine
If you migrate `composer.py` to function-calling, you aren't just changing the API syntax—you are moving from a system that **asks** the model to be compliant to one that **forces** it to be. This eliminates the need for complex regex parsing in `qualifier.py` and ensures that every "decision" the agent makes is valid by construction.
