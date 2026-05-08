# Thread: When p < 0.05 Lies

1/ You trained a LoRA adapter. Benchmark score went up by +0.1046. Paired bootstrap: p=0.018. Significant! Ship it. Then it fails systematically on the hardest cases. What went wrong? 🧵

2/ A p-value only answers ONE question: "If the true difference were zero, how likely is a sample difference this large?" p=0.018 means your improvement isn't noise. But it says NOTHING about whether the improvement matters or where it came from.

3/ The hidden trap: Simpson's Paradox. Your benchmark has 80% easy cases and 20% hard cases. The adapter crushes easy cases (+15%) but REGRESSES on hard cases (−20%). The aggregate shows +8%. The p-value is significant. The model is worse where it matters.

4/ Bootstrap can't save you either. It resamples from YOUR data. If your held-out set has only 3 confidence-boundary cases, bootstrap dutifully resamples from those 3. Narrow CI from a biased sample = false confidence.

5/ The fix: stratified evaluation. Report accuracy PER difficulty tier. Define your minimum detectable effect BEFORE running the eval. Check if your benchmark distribution matches your production distribution. If it doesn't, your p-value is structurally uninformative.

6/ Takeaway: Statistical significance is necessary but not sufficient. Every time you report p<0.05, add: "This reflects aggregate accuracy and does not guarantee performance on under-sampled subgroups." Full explainer: [Link]
