# Supplied Model Card — Synthetic CART v2

**Purpose:** Classroom demonstration of a customer-facing explanation agent. This model
and its limit policy are not suitable for real lending.

## Input, target, and output

- Six numeric inputs: 36-month average balance, balance volatility, on-time payment rate,
  late-payment count, overdraft count, and inflow stability. The feature window is
  January 2023 through December 2025.
- Synthetic target: whether the customer has a simulated missed-payment event in the
  following 12 months. It is never a model input.
- Output: calibrated missed-payment probability. The published policy maps it to a
  300–850 score, then combines the score tier with the 36-month average balance to set a
  synthetic IDR card limit.

## Algorithm and training

The organizer trained a portable numeric CART-style tree with Gini splits, maximum depth
5, and at least 60 training customers per leaf. Candidate thresholds come from feature
quantiles. A disjoint calibration set fits a monotone sigmoid; a separate held-out set
is used only for evaluation. The seed and customer-level split are fixed. `model.json`
contains the trained tree and calibration coefficients. `training_source/` contains the
read-only source used to create it; participants do not train or modify it.

## Held-out results on fictional data

| Metric | Result |
| --- | ---: |
| Train / calibration / test customers | 1,439 / 480 / 481 |
| Test event rate | 0.3576 |
| ROC-AUC | 0.6987 |
| Brier score | 0.2013 |
| Constant-rate baseline Brier | 0.2297 |

The generator deliberately creates relationships between the inputs and simulated
outcome. These results verify the classroom artifact and do not establish real-world
accuracy, fairness, or causal effects.

## Explanation evidence

Each assessment stores up to three splits from that customer's actual model path that
increased the training-set event rate. If none increased it, favorable splits are stored.
The record includes the feature, observed value, threshold, direction, and path change.
The agent may describe these as **model associations**. It must not claim a split caused
the score or promise that changing a value will change a future decision. Missing or
inconsistent evidence calls for abstention and record review.

## Published limit policy

| Score | Multiple of 36-month mean closing balance |
| --- | ---: |
| 300–549 | 0.5× |
| 550–649 | 1.0× |
| 650–749 | 1.5× |
| 750–850 | 2.0× |

Round down to the nearest IDR 100,000 and cap at IDR 100 million. A complete 36-month
history is required. The model version is `synthetic-cart-v2`; stale or contradictory
records must not be silently repaired by the agent.
