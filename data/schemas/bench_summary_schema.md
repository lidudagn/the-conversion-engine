# Schema Definition: `bench_summary.json`

The `bench_summary.json` file is a required input for `PolicyEngine`. It informs the engine of the available developer capacity at Tenacious so that outreach emails do not overcommit resources that the business cannot fulfill.

## Schema Structure

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "role": {
        "type": "string",
        "description": "The standardized title of the offshore talent (e.g., 'React Developer', 'ML Engineer')",
        "examples": ["Full Stack Engineer", "DevOps Specialist"]
      },
      "level": {
        "type": "string",
        "enum": ["Junior", "Mid", "Senior", "Lead"],
        "description": "The seniority level of the talent"
      },
      "count": {
        "type": "integer",
        "minimum": 0,
        "description": "Number of currently benched personnel available for immediate deployment"
      },
      "utilization_projected": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "description": "Projected utilization percentage over the next 30 days"
      }
    },
    "required": ["role", "level", "count"]
  }
}
```

## Example File

```json
[
  {
    "role": "React Native Developer",
    "level": "Senior",
    "count": 5,
    "utilization_projected": 0.8
  },
  {
    "role": "Data Engineer",
    "level": "Mid",
    "count": 2,
    "utilization_projected": 0.95
  },
  {
    "role": "Solutions Architect",
    "level": "Lead",
    "count": 1,
    "utilization_projected": 1.0
  }
]
```

## Consumption by Downstream Modules

1. **`pipeline.py` (Enrichment):** Reads this schema and passes it into the policy rules engine.
2. **`qualifier.py`:** Parses raw open job descriptions from a prospect to identify `required_roles`. It compares those roles against the `bench_summary.json` counts. If `count` > 0 for a matching role/level, it flags `bench_match=True`.
3. **`policy_engine.py`:** Uses the `bench_match` boolean to decide whether to authorize hard commitment language in the outreach email (e.g., "We have team members ready today"). If `bench_match=False`, it forces exploratory language only.
