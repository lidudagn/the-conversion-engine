# Signal Reliability Report: AI Maturity

**Date:** 2026-04-25  
**Sample Size:** 25 companies (randomly sampled from Crunchbase ODM)  
**Methodology:** Human labeling (0-3 scale) based on public web footprint compared against `AIMaturityScorer` classification.

## Executive Summary

The AI maturity scorer achieves **72.0% exact accuracy** and **96.0% within-1 accuracy**. 
It is calibrated extremely conservatively: it produces **zero false positives** for companies with no AI function (Score 0), meaning we never risk pitching an advanced ML infrastructure solution to a company without an engineering team capable of using it.

However, it suffers from a high false-negative rate at the mid-tiers (Score 1 and 2), frequently scoring them as 0.

## Precision & Recall per Tier

| Maturity Score | Label | Support (n) | Precision | Recall (Catch Rate) | False Positive Rate |
|---|---|---|---|---|---|
| **0: None** | No public AI signal | 16 | 76% | 100% | 24% |
| **1: Low** | Automation/adjacent | 7 | 100% | 14% | 0% |
| **2: Medium** | Active ML projects | 2 | 33% | 50% | 67% |
| **3: High** | Core AI function | 0 | N/A | N/A | N/A |

## Business Impact (Tenacious Funnel)

1. **Brand Protection (Strong):** Because precision for Score 1 and Score 2 is poor but false positives for Score 0 are zero, the system *errs on the side of abstention*. 16/16 companies with no AI function were correctly scored as 0. This guarantees we don't send embarrassing wrong-segment pitches to traditional businesses.
2. **Pipeline Loss (Weakness):** Because recall for Score 1 is only 14%, we are missing 86% of companies that use basic automation. These companies receive the "abstain" fallback instead of a highly targeted `signal_grounded` email.

## Recommendations for Production

To improve score-1 recall, we must lower the threshold for "Low" weight signals. Currently, basic keyword matches in job postings are required, but many companies do not mention standard ML frameworks when hiring for basic automation roles. We recommend adding "RPA", "Zapier", and "ETL" to the low-weight signal keyword list.
