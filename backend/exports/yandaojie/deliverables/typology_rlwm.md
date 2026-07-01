# A Typology of Right-Label–Wrong-Mechanism Failures (grounded coding, n=57)

> Built from the 57 episodes the LLM-judge pre-study flagged as **rlwm** (23) or **hollow** (34).
> Method: 3 independent open-coders → reconciled codebook → 3 independent classifiers applied it.
> **Reliability: unanimous 3/3 agreement on 44/57 = 77%** (disagreements at the documented T2/T3 and T4/T5 tie-breaks).
> This typology is **robust to the κ wall**: it is validated by coder agreement on *categories*, not by a population percentage. Source: `_typology_input.json`; codebook + classifier logic in `scripts/` (rlwm-typology workflow).

## Prevalence (majority vote of 3 classifiers)

| Type | Overall | 数学 | 科学 | 英语 | Concentrates in |
|---|---|---|---|---|---|
| **T1 Recited Rule, No Warrant** | 11 | **9** | 1 | 1 | Math |
| **T2 Wrong Proxy or Mechanism** | **16** | 4 | **12** | 0 | Science |
| **T3 Self-Refuting Justification** | 4 | 0 | **4** | 0 | Science |
| **T4 Fragment Stall** | 15 | 2 | 3 | **10** | English |
| **T5 Scaffolded Answer (AI-supplied)** | 4 | 1 | 3 | 0 | Science |
| **T6 Stated Skill, Execution Collapses** | 7 | 2 | 0 | **5** | English |

**rlwm cases** (right label, broken mechanism) concentrate in **T1+T2+T3** — the fluent, correct-looking ones one-shot scoring passes. **hollow cases** concentrate in **T4+T5**. T6 straddles both. The dominant failure mode is partly a function of *what each discipline lets a child fake* — a finding in itself.

**Coder precedence (for MECE classification):** T5 → T3 → T2 → T6 → T1 → T4 (first match wins).

---

## T1 — Recited Rule, No Warrant (n=11; 9/11 math)
Child reproduces a **correct** rule as a memorized unit and may apply it, but every "why" returns the same slogan or a blank. The rule is the terminus, not a tool. Anchor (idx 21), asked three times why scaling both coordinates preserves the figure:
> "因为横纵坐标同时乘2，横轴和纵轴的点会在同一条直线上"

**Report field — `warrant_status`:** rule stated correctly, justification circular/absent. Most likely to be miscredited as mastery; prompt the teacher to demand a worked rationale.

## T2 — Wrong Proxy or Mechanism (n=16, largest; 12/16 science)
Correct label rests on a substantive **wrong** account (sensory proxy or mistaken mechanism) that is self-consistent but fails an external counterexample the child can't resolve. Anchor (idx 50), having claimed color change proves a new substance, goes silent on red-sugar water:
> R2 A: "颜色变化…" → R3 Q (红糖放进水里也变色) → A: "（空）"

**Report field — `false_indicator` + `counterexample_that_broke_it`:** name the wrong criterion and the case that collapsed it.

## T3 — Self-Refuting Justification (n=4; 4/4 science)
Label is plausible but the supplied mechanism contradicts it on the transcript's own terms — no external counterexample needed. Anchor (idx 41) calls frying an egg chemical, then justifies it with a physical-change description:
> "因为那些变化只改变了物质的大小形态"

**Report field — `internal_contradiction`:** surface the two clashing utterances side by side.

## T4 — Fragment Stall (n=15; 10/15 English)
No assemblable claim survives — truncated fragments, pinyin, gibberish, blanks, even after "use a complete sentence." Anchor (idx 102):
> R1 "no" → R2 "bayi" → R3 "no" → R4 "by car"

**Report field — `defensible_content`: none.** Route to foundational, not conceptual, remediation.

## T5 — Scaffolded Answer (n=4; 3/4 science)
Correct conclusion appears **only** after the AI spells out the key step; child oscillates until forced. The sneakiest type — a transcript skimmed at the last turn shows a correct answer. Anchor (idx 52):
> "产生" → "（空）" → "不 因为苹果变色是氧化" → "会" → "产生了"

**Report field — `answer_provenance`: AI-supplied;** point to the originating probe turn; surface the oscillation.

## T6 — Stated Skill, Execution Collapses (n=7; 5/7 English)
Child has the right pieces / names the correct skill but breaks at execution, not concept. Anchor (idx 100) states the future-tense rule yet cannot inflect:
> "应该接动词原型，I am going to vh"

**Report field — `breakdown_locus`: execution/composition, not concept.** Direct toward production practice, not re-teaching the rule.
