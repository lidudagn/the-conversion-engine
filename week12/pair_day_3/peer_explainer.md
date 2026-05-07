# What `beta=0.1` Is Actually Doing in Your DPO Trainer

You set `beta=0.1` in your DPO training config at line 187 and moved on. The model trained, the loss went down, and the judge seemed to work. But if someone asked you what that number controls mechanically — not "it balances preference learning and staying close to the base model" (that is the abstract description) but what it does to the gradient on each step. This post closes that gap.

---

## Where Beta Comes From

DPO did not invent beta. It inherited it from the RLHF objective that DPO was designed to replace. The standard RLHF setup trains a policy by maximising expected reward while penalising deviation from a reference model:

```
max_π  E[r(x, y)]  −  β · KL( π(·|x) ‖ π_ref(·|x) )
```

Beta is the Lagrange multiplier on the KL constraint. 
- Large beta → the KL penalty dominates → the policy is not allowed to move far from the reference. 
- Small beta → the reward term dominates → the policy can go wherever the reward signal points, regardless of how far that is from the base model.

DPO's key result (Rafailov et al., 2023) is that you do not need a separate reward model to solve this optimisation. The optimal policy has a closed form, and you can train directly on preference pairs. But beta survives the derivation — it appears in the DPO loss:

```
L_DPO = −E[ log σ( β·log π_θ(y_w|x)/π_ref(y_w|x)
                  − β·log π_θ(y_l|x)/π_ref(y_l|x) ) ]
```

Let `h` be the log-ratio margin — a single number that measures how well the current model already separates the chosen response from the rejected one, relative to the reference model. Concretely: if the model has moved a lot toward the chosen response and away from the rejected response compared to the reference, h is large. At the start of training, h is near zero because the model has not yet shifted from the reference at all.

```
L_DPO = −E[ log σ( β · h ) ]
```

And the gradient with respect to model parameters θ is:

```
∂L/∂θ  ∝  −β · σ(−βh) · ( ∇log π_θ(y_w) − ∇log π_θ(y_l) )
```

Beta plays two separate roles here, and it helps to read them one at a time.

**Role 1 — overall step size.** The leading `−β` is a direct multiplier on the entire gradient. Double beta, double every parameter update. This is the most obvious effect: larger beta means the model moves faster on every step.

**Role 2 — self-stopping signal.** Beta also appears inside `σ(−βh)`. The sigmoid σ outputs a value between 0 and 1, shrinking toward zero as its input grows. When h is large (pairs already well-separated), `σ(−βh)` is near zero — the gradient nearly vanishes. When h is near zero (pairs barely separated), `σ(−βh)` is near 0.5 — full gradient strength. This is the self-stopping mechanism: weaker updates on pairs the model has already learned. Beta controls how aggressively it kicks in — large beta collapses the gradient as soon as h grows modestly; small beta means the sigmoid barely moves and updates stay near-full strength regardless of separation.

---

## What This Looks Like in Practice

The gradient scale — β·σ(−βh) — is what actually multiplies your parameter update on each step. If the images below render, the right panel plots this directly for four beta values. If not, the two key facts to hold in mind are:

![DPO loss and gradient scale vs log-ratio margin](beta_gradient_scale.png)

**At h = 0 (where training begins)**, σ(0) = 0.5, so the gradient scale is β × 0.5 = β/2. For β=0.01 that is 0.005. For β=0.5 it is 0.25. Higher beta means fifty times larger gradient updates at the start of training.

**As h grows (pairs become well-separated)**, σ(−βh) shrinks toward zero. For high beta this collapse is steep — once a pair is separated by even a moderate margin, the gradient nearly vanishes. For β=0.01, the sigmoid barely moves across the entire range of h: the model keeps receiving near-full-strength updates even on pairs that are already well-separated, and has almost no self-stopping signal.

---

## The Trap in the Training Logs

When you inspect TRL's training logs, `rewards/margins` does not show raw policy drift — it shows **β × h**, with beta baked in. β=0.01 will look flat; β=0.5 will look aggressive. The table tells a different story.

![Log-ratio margin across training steps](beta_margins.png)

To see actual drift, divide by beta:

| β | Final reported margin | Actual h (policy drift) |
|---|---|---|
| 0.01 | ~0.07 | **7.0** |
| 0.1 | ~0.47 | 4.7 |
| 0.5 | ~2.23 | 4.5 |

β=0.01 drifted furthest from the reference policy. β=0.5 drifted least. The KL constraint is working — but it is invisible in the default metric unless you divide it out.

---

## The Real Risk of Low Beta

The standard warning about low beta is "the model may overfit." That framing is incomplete. The more precise risk is: **with near-zero gradients, the model has no self-stopping signal**.

At β=0.01 the gradient scale is ~0.005 everywhere — not just when h is large, but also when h is small. The model updates equally weakly whether the pairs are already well-separated or not. Over enough steps, this means the model keeps drifting from the reference with no mechanism to brake. The KL regularisation that was supposed to keep it anchored is effectively absent.

For your specific setup — a binary constraint judge trained on approximately 200 preference pairs — β=0.1 sits in a reasonable range. The gradient at h=0 is ~0.05, which is small but non-zero. The model will train slowly but will also have a mild self-stopping signal as margins grow. The risk to watch in your training logs is whether `rewards/margins / beta` (the actual h) keeps growing past step 30 without plateauing. If it does, your model is still drifting and has not converged to a stable policy.

---

## The Adjacent Concept: Reward Model Overoptimisation

Beta's role in DPO is the same mechanism behind reward model overoptimisation in full RLHF. When a policy is trained against a reward model without a sufficiently strong KL penalty, it finds high-reward responses that are out of distribution — responses the reward model was never trained to evaluate accurately. The KL term (controlled by beta) is what keeps the policy close enough to the reference that the reward model's scores remain valid. In DPO there is no explicit reward model, but the same dynamic applies: low beta lets the policy drift into regions of the response space that the preference data did not adequately cover.

---

## Sources and Tools

- Rafailov et al. (2023). *Direct Preference Optimization: Your Language Model is Secretly a Reward Model.* NeurIPS 2023. The DPO loss derivation and beta's role are in Section 3.
- Stiennon et al. (2020). *Learning to Summarize with Human Feedback.* The KL-penalised RLHF objective that beta originates from is in Section 3.1.
- Code for both visualisations (math plots and minimal TRL training): `pair_DAY_3/minimal_trl.ipynb` in this repository.
