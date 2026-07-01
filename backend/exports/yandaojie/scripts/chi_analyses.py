"""CHI-prep analyses on EXISTING data only.

(2) Wilson + Clopper-Pearson CIs for the over-credit / RLWM numbers (vs the
    Wald CI that goes negative), plus the topic-confound framing for RQ2.
(3) Judge-INDEPENDENT over-inference signature for RQ3 (no LLM-judge labels):
    inference:evidence ratio, mastered-on-thin-reflection, DK rate.
Also exports the RLWM+hollow episodes (with transcript + revealed) for the
grounded typology (analysis 1).

Run from scripts/:  python3 chi_analyses.py
"""
import json, math, csv
from collections import Counter, defaultdict
from pathlib import Path
from yandaojie_rounds import DELIVERABLES, RAW

# ---------- CI machinery (no scipy needed) ----------
Z = 1.959963985

def wald(k, n):
    if not n: return (0.0, 0.0)
    p = k / n; e = Z * math.sqrt(p * (1 - p) / n)
    return (100 * (p - e), 100 * (p + e))

def wilson(k, n):
    if not n: return (0.0, 0.0)
    p = k / n; z2 = Z * Z
    c = (p + z2 / (2 * n)) / (1 + z2 / n)
    h = (Z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / (1 + z2 / n)
    return (100 * (c - h), 100 * (c + h))

def _binom_cdf(k, n, p):  # P(X<=k)
    from math import comb
    return sum(comb(n, i) * p**i * (1 - p)**(n - i) for i in range(0, k + 1))

def clopper_pearson(k, n, alpha=0.05):
    if not n: return (0.0, 0.0)
    lo, hi = 0.0, 1.0
    # lower: largest p with P(X>=k)=alpha/2  i.e. 1-cdf(k-1,p)=alpha/2
    if k == 0: low = 0.0
    else:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if 1 - _binom_cdf(k - 1, n, m) < alpha / 2: a = m
            else: b = m
        low = (a + b) / 2
    if k == n: up = 1.0
    else:
        a, b = 0.0, 1.0
        for _ in range(200):
            m = (a + b) / 2
            if _binom_cdf(k, n, m) < alpha / 2: b = m
            else: a = m
        up = (a + b) / 2
    return (100 * low, 100 * up)

def fmt(t): return f"[{t[0]:.0f}, {t[1]:.0f}]"
def fmt1(t): return f"[{t[0]:.1f}, {t[1]:.1f}]"

def fisher_2x2(a, b, c, d):
    from math import comb
    # two-sided Fisher exact p
    r1, r2 = a + b, c + d; c1 = a + c; n = a + b + c + d
    def pmf(x):
        return comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)
    p_obs = pmf(a); tot = 0.0
    lo = max(0, r1 - (n - c1)); hi = min(r1, c1)
    for x in range(lo, hi + 1):
        px = pmf(x)
        if px <= p_obs * 1.000001: tot += px
    return tot

# ---------- load ----------
eps = json.load(open(DELIVERABLES / "_validity_episodes.json"))
rat = json.load(open(DELIVERABLES / "_validity_ratings.json"))
by_idx_ep = {e["idx"]: e for e in eps}
DEPTH = {"sound": "sound", "label_right_mechanism_wrong": "rlwm",
         "hollow_or_guess": "hollow", "no_understanding": "none", "cant_tell": "cant_tell"}
NOT_SOUND = {"rlwm", "hollow", "none"}
recs = []
for r in rat:
    e = by_idx_ep.get(r["idx"], {})
    recs.append({"idx": r["idx"], "subject": e.get("subject", "?"),
                 "topic": e.get("topic"), "mc": r["mc_view"],
                 "depth": DEPTH.get(r["defense_depth"]), "revealed": r.get("revealed", ""),
                 "conf": r.get("confidence")})

print("=" * 72)
print("ANALYSIS (2)  —  CORRECTED INTERVALS  (LLM-judge pre-study, n=106, 1 rater)")
print("=" * 72)
print("[!] These are provisional LLM-judge labels (kappa~0.35). The point of this")
print("    table is the INTERVAL METHOD, not the validated magnitude.\n")

def rate_block(subset, label):
    n = len(subset)
    over = sum(1 for r in subset if r["mc"] == "got_it" and r["depth"] in NOT_SOUND)
    rlwm = sum(1 for r in subset if r["depth"] == "rlwm")
    gotit = sum(1 for r in subset if r["mc"] == "got_it")
    print(f"--- {label} (n={n}) ---")
    print(f"  over-credit      {over}/{n} = {100*over/n:4.0f}%   "
          f"Wald {fmt(wald(over,n))}  Wilson {fmt(wilson(over,n))}  Clopper-Pearson {fmt(clopper_pearson(over,n))}")
    print(f"  RLWM             {rlwm}/{n} = {100*rlwm/n:4.0f}%   "
          f"Wald {fmt(wald(rlwm,n))}  Wilson {fmt(wilson(rlwm,n))}  Clopper-Pearson {fmt(clopper_pearson(rlwm,n))}")
    if gotit:
        print(f"  divergence(|MC=got){over}/{gotit} = {100*over/gotit:4.0f}%   "
              f"Wilson {fmt(wilson(over,gotit))}")
    return over, n

rate_block(recs, "ALL")
print()
bysub = defaultdict(list)
for r in recs: bysub[r["subject"]].append(r)
sub_over = {}
for s in ["数学", "科学", "英语"]:
    o, n = rate_block(bysub[s], s)
    sub_over[s] = (o, n)
    print()

print("Depth distribution (LLM-judge):", dict(Counter(r["depth"] for r in recs)))
print("cant_tell used:", sum(1 for r in recs if r["depth"] == "cant_tell"),
      "(in taxonomy + gold key, never used by the judge)")

print("\n" + "-" * 72)
print("RQ2 cross-subject contrast + TOPIC CONFOUND")
print("-" * 72)
mo, mn = sub_over["数学"]; eo, en = sub_over["英语"]
print(f"  math over-credit {mo}/{mn}={100*mo/mn:.0f}%  vs  english {eo}/{en}={100*eo/en:.0f}%")
print(f"  naive 2x2 Fisher exact (math vs english), treating episodes as iid: "
      f"p = {fisher_2x2(mo, mn-mo, eo, en-eo):.4f}")
ntopics = {s: len({r['topic'] for r in rs}) for s, rs in bysub.items()}
print(f"  topics per subject: {ntopics}")
print("  => subject is PERFECTLY CONFOUNDED with topic (1 topic each):")
print("     math=《可爱的小猫》 science=《厨房里的物质变化》 english=Unit 6 Summer Vacation.")
print("     A model `over ~ subject + (1|topic)` is UNIDENTIFIABLE: topic is nested 1:1")
print("     in subject, so between-topic variance (the correct error term for a subject")
print("     contrast) has 0 df. The effective n for generalizing to 'subjects/curricula'")
print("     is 3 topics, not 106 episodes. The Fisher p above answers the WRONG question")
print("     (it generalizes to 'more episodes of THESE THREE units', not to 'subjects').")

# ---------- Analysis 3 ----------
print("\n" + "=" * 72)
print("ANALYSIS (3)  —  JUDGE-INDEPENDENT OVER-INFERENCE SIGNATURE  (no LLM-judge labels)")
print("=" * 72)
def load(n): return [json.loads(l) for l in open(RAW / f"{n}.jsonl") if l.strip()]
questions = load("defense_questions")
sessions = load("sessions")
turns = load("defense_turns")
ans = {(t.get("session_id"), t.get("round_index")): (t.get("answer_text") or "") for t in turns}

DK = {"", "不知道", "不会", "不清楚", "不知", "no", "idk", "不懂", "忘了", "不记得"}
def is_dk(a):
    a = (a or "").strip()
    return a == "" or a in DK or a.lower() in DK

def mastered_objs(q): return [str(x) for x in ((q.get("diagnoses") or {}).get("mastered") or [])]

# (a) ratio over ALL rounds, evidence = reflection + that round's answer
def ratio_dist(rounds_evidence):
    rs = sorted(rounds_evidence)
    p = lambda f: rs[min(len(rs) - 1, int(f * len(rs)))]
    return len(rs), p(0.5), sum(rs) / len(rs), p(0.9), rs[-1]

all_r, r1_r = [], []
for q in questions:
    inf = len(q.get("reasoning_content") or "") + len(q.get("question") or "")
    refl = sum(len((r.get("learned") or "").strip()) for r in (q.get("reflections") or []))
    ans_txt = ans.get((q.get("session_id"), q.get("round_index")), "")
    ev_all = refl + len(ans_txt.strip())
    if ev_all > 0 and inf > 0: all_r.append(inf / ev_all)
    if q.get("round_index") == 0 and refl > 0 and inf > 0: r1_r.append(inf / refl)  # plan's basis: reflection only

n, med, mean, p90, mx = ratio_dist(all_r)
print(f"\ninference:evidence ratio  (AI reasoning+question chars / student evidence chars)")
print(f"  [def A: all {n} rounds, evidence=reflection+answer]   median {med:.0f}x  mean {mean:.0f}x  p90 {p90:.0f}x  max {mx:.0f}x")
n, med, mean, p90, mx = ratio_dist(r1_r)
print(f"  [def B: round-1 only, evidence=reflection text only ]   median {med:.0f}x  mean {mean:.0f}x  p90 {p90:.0f}x  max {mx:.0f}x")
print("  (plan cites median 109x/mean 210x/p90 521x; def B reproduces the same regime. Either way:")
print("   JUDGE-FREE — the model emits ~50-200x more text than the child supplied as evidence.)")

# mastered-on-thin: (i) round-1 diagnosis, (ii) AI EVER asserts mastery for that objective in the session
first_round, ever_mastery = {}, defaultdict(bool)
for q in questions:
    sid = q.get("session_id")
    first_round.setdefault(sid, q)
    if len(mastered_objs(q)) > 0: ever_mastery[sid] = True
for sid, q in list(first_round.items()):
    if q.get("round_index") != 0:  # ensure earliest round
        cand = [x for x in questions if x.get("session_id") == sid]
        first_round[sid] = min(cand, key=lambda x: x.get("round_index") if x.get("round_index") is not None else 99)

refl_records = []
for sid, q in first_round.items():
    r1_mastery = len(mastered_objs(q)) > 0
    for r in (q.get("reflections") or []):
        refl_records.append({"chars": len((r.get("learned") or "").strip()),
                             "r1_mastery": r1_mastery, "ever_mastery": ever_mastery[sid]})
print("\nmastery asserted on near-empty evidence (judge-free; AI's own runtime diagnosis):")
for thr in [5, 10]:
    sub = [r for r in refl_records if r["chars"] <= thr]
    if sub:
        a = sum(1 for r in sub if r["r1_mastery"]); b = sum(1 for r in sub if r["ever_mastery"])
        print(f"  reflections <= {thr:2d} chars (n={len(sub):3d}):  round-1 mastery {100*a/len(sub):.0f}%   "
              f"ever-mastery-in-session {100*b/len(sub):.0f}%")

# DK / thinness
all_ans = [ans.get((q.get("session_id"), q.get("round_index")), "") for q in questions]
ans_nonempty = [a for a in all_ans if a.strip()]
dk = sum(1 for a in ans_nonempty if is_dk(a))
print(f"\n  student answers: n={len(ans_nonempty)} non-empty; "
      f"mean length {sum(len(a) for a in ans_nonempty)/len(ans_nonempty):.1f} chars; "
      f"DK/refusal {dk}/{len(ans_nonempty)} = {100*dk/len(ans_nonempty):.0f}%")
mastered_q = sum(1 for q in questions if len(mastered_objs(q)) > 0)
print(f"  rounds where AI lists >=1 objective 'mastered': {mastered_q}/{len(questions)} = {100*mastered_q/len(questions):.0f}%")

# ---------- export typology input ----------
def transcript(e):
    out = []
    for t in (e.get("turns") or []):
        st = (t.get("student") or "").strip() or "（空）"
        out.append(f"R{t.get('round')} Q: {t.get('ai_q','')}\n   A: {st}")
    return "\n".join(out)

typ = []
for r in recs:
    if r["depth"] in {"rlwm", "hollow"}:
        e = by_idx_ep[r["idx"]]
        typ.append({"idx": r["idx"], "subject": r["subject"], "topic": r["topic"],
                    "label": r["depth"], "objectives": e.get("objectives"),
                    "reflection": e.get("reflection"), "confidence": r["conf"],
                    "revealed": r["revealed"], "transcript": transcript(e)})
out = DELIVERABLES / "_typology_input.json"
json.dump(typ, open(out, "w"), ensure_ascii=False, indent=1)
print(f"\n[export] {len(typ)} RLWM+hollow episodes -> {out.name} "
      f"({sum(1 for t in typ if t['label']=='rlwm')} rlwm / {sum(1 for t in typ if t['label']=='hollow')} hollow)")
