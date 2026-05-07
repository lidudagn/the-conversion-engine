# Evening Call Summary — Day 3

**Date:** 2026-05-07
**Topic:** Training and Post-Training Mechanics
**Participants:** Lidya Dagnew & Martha Ketsela

## Feedback & Revisions

### Explainer for Martha:
- **Lidya's delivery:** Martha confirmed that the concept of "Information Bottleneck" was the key missing piece for her. She now understands that rank ($r$) isn't just about capacity, but about preventing the model from memorizing the specific training pairs.
- **Revision:** Added a section on the "Information Bottleneck" to clarify how rank forces generalization.

### Explainer from Martha:
- **Martha's delivery:** Her explainer on the DPO Beta parameter used gradient scale visualizations to show how $\beta$ acts as a "Trust Budget."
- **Feedback:** I requested she clarify the specific impact on a 0.5B model (Qwen), which she added. I now understand that small models require higher Beta to prevent linguistic collapse.

## Sign-off
Both partners confirmed that the day's research successfully closed the targeted knowledge gaps.
