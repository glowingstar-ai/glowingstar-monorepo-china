# Pre-Registration & Analysis Plan — Defense-Based Assessment (v3)

> Freeze this document **and** the codebook (`packets_v3/…编码手册`) **before** teachers annotate.
> Units, stimuli, and the 106 episodes are already fixed. Global `idx` (0–105) is the join key across
> teacher labels, the LLM-judge pre-study (`_validity_ratings.json`), the typology (`_typology_input.json`),
> and the 3-AI scorer outputs.

## 0. Design in one screen

- **Study 1 — Defense-depth annotation (measurement / load-bearing).** 9 in-subject teachers (3 per subject) fully cross-annotate their subject's episodes (math 31 / science 40 / English 35) using the v3 packet. Four labels across two screens:
  - **Screen 1 (blind to defense):** `L1` one-shot verdict on the round-1 answer only (已掌握/部分/未掌握) + confidence.
  - **Screen 2 (full defense):** `L2` sound? (扎实/不扎实/难判断, **the κ gate**) + confidence; `L3` failure class if not-sound (对标签错机制/空洞或猜对/完全不懂); `L3+` optional fine type (T1–T6); `L4` reteach pointer + gap type.
- **Study 2 — Mechanism-gap report (design experiment / the HCI contribution).** Within-subject; teachers judge the same 106 episodes under two representations; ground truth = Study 1 consensus labels. Two arms this plan adds are load-bearing (§6).

## 1. Confirmatory vs exploratory (declare up front)

| # | Claim | Status | Gated by (see §3) |
|---|---|---|---|
| RQ1a | Over-credit rate (one-shot passes, defense not-sound) | **Confirmatory** | Gate A + Gate B |
| RQ1b | Share that is "right-label-wrong-mechanism" (3-way) | **Confirmatory** | Gate C |
| RQ1c | Fine 6-type typology prevalence | Exploratory | none (report α) |
| RQ2 | Cross-subject **boundary** (qualitative; "defense needs defensible reasoning structure") | **Confirmatory (qualitative)** | descriptive only — **no** inferential subject contrast (§5) |
| RQ3a | Frontier LLMs cannot reliably score children's defenses; shared RLWM blind spot | **Confirmatory** | Gate A/C + §7 |
| RQ3b | Over-inference signature (judge-independent) | **Confirmatory** | none (deterministic; §7.4) |
| S2-H1 | Mechanism-gap report ↑ correct identification of not-sound students | **Confirmatory** | Gate A + §6 |
| S2-H2 | Report ↑ mechanism-targeted reteach decision | **Confirmatory** | §6 |
| S2-H3 | Gain concentrated in conceptual subjects, ≈0 in language | Exploratory | cell sizes/topic confound (§5) |
| S2-H4 | Mastery-score-only inflates confidence without accuracy (calibration) | **Confirmatory** | §6 |
| S2-H5 | Teachers over-trust the card when it is **wrong** (appropriate-reliance) | **Confirmatory** | §6 card-correctness arm |

## 2. Ground-truth construction (consensus gold)

Reliability (IRR) is computed on the **three raw teacher labels**. All downstream *rates* and all AI/Study-2 comparisons use a single **consensus gold per idx**:

1. Majority of the 3 teachers → gold, when ≥2 agree (on L1; on L2; on L3 among not-sound).
2. No majority (3-way split, or 1 "难判断" + split) → **senior adjudication pair** resolves to a single label, blind to the AI labels, following the codebook decision rules. Record which idx required adjudication.
3. `L2=难判断` is not "not-sound": episodes where the **gold** L2 is 难判断 are excluded from the over-credit denominator and reported separately (expected to matter for English; see §5).

## 3. Reliability — which κ gates which claim (the core table)

Report **Krippendorff's α** (primary; handles the 难判断 as a category and missing cells) **and** Fleiss' κ, **per subject panel** and **pooled**. Metric is nominal except L1 (ordinal). All machinery already in `analyze_validity.py`.

| Gate | Label / contrast | Metric | Threshold | If it clears → | If it misses → |
|---|---|---|---|---|---|
| **A (primary)** | **L2 binary: 扎实 vs 不扎实** (drop 难判断) | nominal α | **≥ 0.60** | over-credit, RQ3, Study-2 ground truth are interpretable | **Do not submit the rate claims.** Re-norm one round, re-annotate the contested batch. If still <0.6, the thesis is not measurable — pivot to the typology + over-inference signature only. |
| **B** | **Over-credit derived-binary** (L1=已掌握 ∧ L2=不扎实) | Fleiss κ | ≥ 0.60 | headline 25%-type rate is defensible | report rate with a wide measurement-error interval, not a Wald CI |
| **C** | **L3 3-way** (对标签错机制/空洞/完全不懂), among not-sound | nominal α | ≥ 0.60 | RLWM-share claim (RQ1b) is confirmatory | collapse to binary "gave-wrong-mechanism vs gave-no-mechanism"; if still <0.6, report only "not-sound-with-correct-label" and drop the RLWM/hollow split |
| **D** | **L1 one-shot** (ordinal) | ordinal α | ≥ 0.60 | the MC-view counterfactual is reliable | report L1 descriptively; lean on Screen-1 blindness for validity |
| — | **L3+ 6-type** (T1–T6) | nominal α | report only | typology validation (exploratory) | present typology as AI-derived, teacher-corroborated at the 3-way level |

**Do not gate on pooled κ alone.** The load-bearing distinction is **对标签错机制 vs 空洞** (Gate C) — pooled depth κ can clear 0.6 while this specific contrast sits at chance. Gate C is reported and gated **separately**.

## 4. Over-credit — exact algorithm

Let each episode `i` have gold `L1_i ∈ {已掌握, 部分, 未掌握}` and `L2_i ∈ {扎实, 不扎实, 难判断}`.

- **Analysis set** `V` = episodes with gold `L2_i ≠ 难判断` (report |V| and the excluded count).
- **Over-credit indicator** `O_i = 1` iff `L1_i = 已掌握` **and** `L2_i = 不扎实`.
- **Over-credit rate** = `Σ O_i / |V|` — the **whole-sample** rate. Report with a **Wilson (or Clopper–Pearson) interval** (never Wald — it goes negative at the English rate; verified `[-2,13]`→Wilson `[2,19]`).
- **Divergence rate** = `Σ O_i / |{i : L1_i = 已掌握}|` — the **conditional** rate among one-shot-pass episodes. **Report side by side with the whole-sample rate; never swap the denominator.**
- **RLWM share** = `|{i : O_i=1 ∧ L3_i = 对标签错机制}| / |V|`, Wilson CI.
- **Clustering:** episodes are nested in students; the `_validity_episodes.json` file lacks a stable student id, so **first map idx→student_id** (via `sid`→`sessions`) and compute a **cluster (student) bootstrap** interval alongside the closed-form one. Report the design effect.
- **"Miskill" check:** `|{i : L1_i∈{部分,未掌握} ∧ L2_i=扎实}|` (defense wrongly withholds credit) — expected ~0; report to show the gain is one-directional.

## 5. RQ2 cross-subject — pre-registered as descriptive, with the confound stated

Each subject = **exactly one topic** (verified: math《可爱的小猫》/ science《厨房里的物质变化》/ English Unit 6). Therefore:

- **We will not run an inferential subject contrast** (a `over ~ subject + (1|topic)` model is unidentifiable — topic nested 1:1 in subject, between-topic df = 0). Any two-proportion/Fisher test would generalize to "more episodes of these three units," not to "subjects," and is **excluded** from confirmatory claims.
- We report **per-subject over-credit with Wilson CIs** descriptively, plus the **qualitative boundary claim**: defense-based assessment requires answers containing an independent, defensible reasoning structure; in language production (English) the mechanism signal largely vanishes (reasoning-marker density and the 难判断/gap=无 rate as evidence). Framed as a **within-deployment observation + boundary condition**, not a map.
- **Attrition caveat (report as a limitation, CONSORT-style):** completion is lopsided (math 10/60 vs English 35/35); the surviving math episodes are a completion-selected subset on the same engagement axis being measured. Report over-credit conditional on completion and note the survivorship.

## 6. Study 2 — design experiment (the two arms that matter)

- **Stimuli:** the 106 episodes (no redeployment). **Participants:** over-recruit in-subject teachers beyond the 9 to power the within-subject test.
- **Conditions (within-subject, order counterbalanced):**
  1. **Baseline+ (information-matched control):** raw defense transcript + a *generic* AI summary, **without** the named mechanism or the reteach line. *(This is the arm the current plan lacks; without it a positive result is uninterpretable "more info helps.")*
  2. **Mechanism-Gap Report:** correct conclusion + the **named** exposed mechanism (from the L3/T-type + `revealed`) + the child's verbatim words + a one-line "reteach this."
  3. **Card-correctness manipulation:** a pre-registered fraction of Treatment cards are **known-wrong** (auto-generated by an LLM scorer that passed a gold-RLWM episode; verified against the gold). Measures over-trust (S2-H5).
- **Primary DV:** teacher's decision — (a) identify not-sound (accuracy vs gold), (b) reteach choice coded generic-vs-mechanism-targeted, (c) confidence.
- **Model:** GLMM with **crossed random effects for teacher and episode**; condition (and card-correctness) as fixed effects; report effect sizes + CIs. S2-H3 (subject moderation) is **exploratory** given cell sizes and the topic confound.
- **Ground truth:** consensus L2 (not-sound = who's "really" hollow), L3/L4 for the mechanism-targeting code and the human "gold card" the auto card is scored against.

## 7. The 3-AI × teacher comparison (de-circularizes RQ3)

**Goal:** replace "one LLM judge says the tutor mislabeled" (circular, κ≈0.35) with "**no** frontier LLM, across families, can score children's defenses — and they share the RLWM blind spot."

- **Scorers:** 3 LLMs from **different families** (e.g., Claude / GPT / DeepSeek or Gemini). Each independently produces `L1, L2, L3` on all 106 episodes using the **same codebook prompt** the teachers get. (Also archive the tutor's own runtime mastery verdict as a 4th "in-loop" scorer.)
- **Reference:** the teacher **consensus gold** (§2).

**7.1 Agreement matrix.** Compute α/κ for every pair and report as a matrix:

|  | Teacher gold | AI-1 | AI-2 | AI-3 |
|---|---|---|---|---|
| **Teacher–Teacher** (IRR) | α_TT | — | — | — |
| **AI vs gold** | — | α_1 | α_2 | α_3 |
| **AI vs AI** | — | \ | α_12 | α_13/α_23 |

Interpretation rule (pre-registered): if **α(AI–AI) ≫ α(AI–gold)**, the models share a systematic bias → evidence the human is not a convenience but a corrective (supports the human-in-loop thesis).

**7.2 The blind-spot test (primary RQ3a metric).** For each AI, on the **gold not-sound** set: **pass-rate** = P(AI says L2=扎实 | gold=不扎实), reported **overall and split by gold L3** (对标签错机制 / 空洞 / 完全不懂). Pre-registered prediction: pass-rate is **high on 对标签错机制, low on 完全不懂**, for **all three** models → the shared RLWM blind spot. Report per-AI sensitivity/specificity + a confusion table over the 6 T-types.

**7.3 Convergence with the tutor.** Cross the AIs' L2 against the tutor's runtime "mastered" verdict to show the failure is not specific to the deployment model.

**7.4 Judge-independent corroboration (no labels at all).** Report the over-inference signature (`scripts/chi_analyses.py`): inference:evidence ratio (median ≈87×, mean ≈174×), mastery asserted on ≤10-char reflections (96–97%), 87% of rounds assert ≥1 objective mastered, mean answer 13.8 chars. This stands even if every κ target failed.

## 8. Statistical conventions

- Proportions: **Wilson** point interval + **student-cluster bootstrap** (10k resamples). Never Wald.
- IRR: Krippendorff α (primary) + Fleiss κ; per-subject panel **and** pooled; bootstrap CIs on α.
- Multiplicity: the confirmatory claims in §1 are the pre-registered family; control FDR (Benjamini–Hochberg) across them. Exploratory results labeled as such.
- Everything re-run from consensus gold; LLM-judge numbers appear **only** as the "baseline to beat."

## 9. Frozen before unblinding
Codebook (`packets_v3`), this plan, the norming gold key (`norming_goldkey_v3.md`), the gold-adjudication protocol (§2), the AI scorer prompt, and the Study-2 card templates + card-correctness fraction. Deviations logged.
