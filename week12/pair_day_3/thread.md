# Thread: Why LoRA Rank-16 is the "Sweet Spot"

1/ When you fine-tune an LLM, you’re making a bet on "Intrinsic Dimensionality." Why is a rank-16 matrix (tiny fraction of params) enough to turn an LLM into a specialized sales judge? 🧵

2/ Theory: Aghajanyan et al. (2020) proved that LLM fine-tuning happens in a tiny subspace. You aren't teaching "new" knowledge — you're teaching the model how to RECOMBINE what it already knows into a new decision boundary.

3/ For a binary judge trained on 200 pairs, the "intrinsic dimension" (the degrees of freedom needed) is tiny. Rank-16 is actually over-provisioned. So why not go to Rank-64? 

4/ Risks of High Rank (r=64+): With small datasets (200 pairs), high rank = memorization. The model stops learning the *rules* of segment alignment and just memorizes your training examples. Result: Catastrophic overfitting.

5/ Risks of Low Rank (r=4/8): Underfitting. The model doesn't have the "degrees of freedom" to distinguish subtle framing (Growth vs. Efficiency). The training loss plateaus, and it stays a generic, polite bot.

6/ Architecture takeaway: For domain-specific judging, r=16 is your safety net. It’s large enough to capture nuance but small enough to force the model to generalize. Own your hyperparameters. Full explainer: [Link to Blog]
