# Evaluation Rubric — 100 points

| Category | Points | Full-credit evidence |
| --- | ---: | --- |
| Identity and MongoDB access | 25 | Backend token lookup, own-customer queries, read-only role, cross-user tests |
| Grounded model explanation | 25 | Stored score and true model-path reasons, clear associations, no invented or causal claims |
| Limit and data integrity | 20 | 36-month mean, tier, rounding/cap, missing and contradictory records handled safely |
| Agent, API, supplied UI, and Docker | 15 | Bounded tool choice, follow-up, fixed routes, persona switching, safe failures, plus 5 points for one working API/UI image launched through Compose |
| Evaluation and communication | 15 | ≥12 cases, tests, architecture, production limits, 5–7 minute demo |
| **Total** | **100** | |

**Hard gates:** The milestone does not pass if a user can obtain another customer's data;
the agent invents a score, reason, or limit; stored prompt-injection text controls a tool
or answer; the service writes customer assessments; or no working API connects to the
supplied UI. Training or modifying the provided model earns no points and is outside
the participant task.

Docker packaging is worth 5 of the 15 points in its category. A failed container build
or launch loses those points, but is not by itself a hard gate if the same API and UI
work through the documented local Python setup.

Partial credit requires reproducible evidence. A feature that works only in a scripted
demo without tests receives at most half of its category points.
