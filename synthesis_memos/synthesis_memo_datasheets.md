# Synthesis Memo: Datasheets for Datasets (Gebru et al.) & Data Cards (Pushkarna et al.)

## Key Takeaways
- **Standardized Provenance Structure**: Gebru et al. propose a 7-section datasheet format (Motivation, Composition, Collection, Preprocessing, Uses, Distribution, Maintenance) intended to hold dataset creators accountable. The framework treats each section as load-bearing: omitting "Preprocessing" or "Maintenance" is not a minor gap but a documentation failure.
- **Layered Detail via Data Cards**: Pushkarna et al. extend the static Gebru model with three documentation layers — telescopic (high-level overview), periscopic (contextual narrative for practitioners), and microscopic (field-level technical detail) — acknowledging that different readers need different granularities.
- **Foreseeing Harms, Not Just Describing Contents**: Both papers argue that documentation must address not only what is in the dataset but the intent, known limitations, and foreseeable misuse patterns. A datasheet omitting downstream harms is treated as incomplete even if all factual fields are filled.
- **Creator Accountability**: Gebru et al. position the dataset creator — not the downstream user — as the responsible author. Accountability cannot be delegated to users absent during collection.

## Disagreement and Critique

Gebru et al. assume a fundamentally **static dataset with fixed, human-executed provenance**. Their "Collection" section presumes a knowable set of human decisions that can be written down from memory after the fact. Pushkarna et al.'s periscopic layer is similarly framed as **human-written contextual narrative** — a practitioner explains why certain data was included or excluded, drawing on their recollection of the process.

**This assumption breaks down for routed synthetic datasets, and neither paper offers a remedy.**

For Tenacious-Bench's 96 LLM-synthesis tasks, generation model, seed prompt template, judge model, and quality filter threshold all vary per task based on routing logic. There is no single human who observed all 96 generation decisions — the pipeline executed them programmatically. Asking a human to write the periscopic narrative "from memory" for these tasks would produce precisely the kind of retrospective rationalization that datasheets exist to prevent.

More concretely: Pushkarna et al. specify that the periscopic layer should capture "the story of the data" — why certain choices were made. For synthetic data, the only reliable source of that story is the **pipeline execution log**, not a human author. Requiring human-written narrative here introduces an ironic accountability gap in a framework designed to close accountability gaps.

**Our position**: for synthetic datasets, the periscopic layer should be **machine-generated from pipeline logs and human-verified**, not human-authored from memory. The distinction matters: machine generation from logs is auditable and reproducible; human narrative reconstruction is neither.

## Application to Tenacious-Bench

- **Datasheet-ready logging in the generation pipeline**: Each of the 96 LLM-synthesis tasks carries `metadata.generation_model` and `metadata.judge_model` fields written at generation time. The Gebru "Collection" section for these tasks is assembled programmatically from these fields, not reconstructed after the fact.
- **Strict Gebru 7-section structure for the final `datasheet.md`**: The Act II deliverable follows all seven sections, with the "Preprocessing" section explicitly documenting the n=8 gram threshold and cosine similarity < 0.85 contamination check that was run before sealing partitions.
- **Periscopic layer documents the judge rotation policy**: Following Pushkarna's layered model, the periscopic section describes the Li et al. preference leakage prevention rationale — generation and judging families are always different — so downstream users understand why the dataset is structured this way and can replicate the policy in derivative work.
