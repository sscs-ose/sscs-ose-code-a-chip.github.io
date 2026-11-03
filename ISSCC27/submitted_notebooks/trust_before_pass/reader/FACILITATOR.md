# Facilitator protocol and answer rubric

**Contains challenge guidance. Keep separate from the participant's initial work.**
No participants have been recruited or evaluated. This document is a plan, not
evidence of educational efficacy. At least one nondeveloper's actual trial and
feedback-driven revision are mandatory before educational acceptance.

## Conduct

Obtain agreement to the trial and explain what will be recorded. Avoid collecting
names or unrelated personal information. Assign a participant code. Record prior
Python/SPICE/analog familiarity and environment. Have the participant extract the package and open the standalone HTML controls; no Python setup is expected for the novice route. Record browser/version and whether they used standalone, embedded or static mode. Let the participant attempt setup;
record independent success, assisted success or failure separately. If they switch to STATIC_WORKBOOK.html, retain interpretation results but do not count a dynamic-controls success. The standalone INVESTIGATION_DESK.html is the primary interactive route, not a fallback failure. Do not silently fix their environment or reveal the key.

Use the six tasks in TRIAL_GUIDE.html / FEEDBACK_FORM.txt. Give only the compact reader pack. Keep this answer key separate. Use OBSERVER_FORM.txt if JSON is unfamiliar. Record English-language/terminology help separately from engineering hints. Capture the first answer before hints,
then record the hint verbatim and the revised answer. A prompt to look at a named
signal is a hint. Do not replace wrong predictions with the final correct answer.
For missing artifacts record missing data, not a zero duration or successful task.

## Rubric (0–2 per task; retain raw reasoning)

0 = not demonstrated; 1 = partial or achieved only after substantive guidance;
2 = independently correct with an evidence-based explanation. Report scores as
descriptions of this small sample, not standardized or validated learning measures.

| Task | Expected evidence of mastery |
|---|---|
| 1 | POR rising asserts reset; startup and full reset duration differ; 4 ms cannot validate 50 ms pulse |
| 2 | Old record: selected delay INVALID at both cutoffs; T1 insufficient at 2.5 ms, FAIL at 4 ms because trigger ≈1.818 ms and deadline ≈3.818 ms; original execution remains COMPLETE |
| 3 | Matched HVL change supports dependency explanation; removing DC alone not sufficient; corrected nonlinear result means resistor simplification not necessary; credits known upstream fix |
| 4 | Corrected trace remains VALID; upper scalar limit 1 ms makes scalar FAIL while unchanged T1 stays PASS |
| 5 | At 4.4 ms no required response yet: delay INVALID, T1 insufficient; supply trigger ≈3.636 ms, deadline ≈5.636 ms. More observation is needed. Full record has POR ≈4.552 ms and T1 PASS. Learner proposes coverage-aware check |
| 6 | Button-to-lamp transfer example: explicit press/illumination events, a stated source for an allowed delay (or acknowledge no known spec), and insufficient history or duration requiring abstention; do not invent a pass limit. Other well-defined delay examples are acceptable |

These answers concern declared teaching T1, not proof of violation of the original
design specification. A participant who questions T1's suitability has identified
a legitimate limitation, not necessarily made an error. Accept well-supported
alternative contracts if they clearly distinguish them from the exercise rule.

## Report and revise

Record setup completion, task completion (attempted/completed independently/with
hint), durations when actually measured, initial versus final reasoning, common
errors, confusing labels and direct comments. Do not report percentages without
the denominator; with one reader, describe that individual's observations.

Copy SESSION_TEMPLATE for each real session. Use REVISION_LOG to connect observed
problems to exact content/code changes and a subsequent recheck. Retain feedback
that contradicts the expected benefit. Do not count an agent review, unit test or
author self-test as an independent reader. No invitation is sent automatically.

The browser download is a local attempt journal, not proof of independent human participation. Verify provenance of a real session. Automated UI test records are explicitly labeled and must be excluded.
