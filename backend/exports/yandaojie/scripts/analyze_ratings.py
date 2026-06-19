"""Analysis skeleton for the Yandaojie three-phase expert audit.

Reads the FILLED teacher packets (packet_T1/T2/T3.xlsx) and computes the
influence / reliance metrics. Runs end-to-end on EMPTY packets too: it reports
how many ratings are present and skips metrics that have no data yet, so you can
wire it up now and re-run as ratings come in.

Metrics:
  1. AI influence on expert diagnosis: switch rate, movement-toward-AI, WOA
  2. Confidence: ΔConf and confidence calibration (needs gold)
  3. Reliance 2x2: appropriate / over / under / self  (needs gold)
  4. ±reasoning effect: all of the above split by condition
  5. Failure chain: hallucination / off-target / disengage / WOA by reflection band
  6. Inter-rater reliability: Fleiss' kappa (nominal) + Krippendorff alpha (ordinal)

Gold standard: optional gold_truth.csv with columns round_id,obj_index,truth(3/2/1/0).
AI per-objective stance: code_ai_stance() is a HEURISTIC stub — replace with a
human/LLM coding pass for publication-grade WOA / reliance numbers.
"""
import csv
import re
from collections import defaultdict, Counter
from pathlib import Path

import openpyxl
from yandaojie_rounds import build_rounds, DELIVERABLES

HERE = DELIVERABLES  # packets (in packets/), gold_truth.csv, and outputs live here
ROUNDS = {r["round_id"]: r for r in build_rounds()}

# ---- column headers (must match gen_teacher_packets.py) ----
H = {
    "p1_diag": "【P1】盲诊_掌握度(3/2/1/0)", "p1_conf": "【P1】信心",
    "p2_diag": "【P2】重评_掌握度(3/2/1/0)", "p2_conf": "【P2】信心",
    "gnd": "【Q】诊断groundedness", "consist": "【Q】与盲诊(P1)一致性",
    "useful": "【Q】诊断有用性", "relevance": "【Q】追问相关性", "ontarget": "【Q】对准薄弱点",
    "elicit": "【Q】引出力", "fit": "【Q】适切", "attitude": "【Q】作答态度",
    "icap": "【Q】ICAP", "depth": "【Q】深度", "advance": "【Q】整轮推进",
    "teacher": "评分老师", "cond": "条件", "subject": "学科",
}


def packet_files():
    """The 9 per-subject packets in deliverables/packets/ (fallback to flat layout)."""
    pdir = HERE / "packets"
    if pdir.is_dir():
        files = sorted(pdir.glob("packet_*.xlsx"))
        if files:
            return files
    return [HERE / f"packet_{t}.xlsx" for t in ("T1", "T2", "T3")]


def parse_diag(text):
    """'目标1=2; 目标2=0' / '1:2,2:0' -> {0:2, 1:0}  (objective index 0-based)."""
    if not text:
        return {}
    out = {}
    for m in re.finditer(r"(?:目标)?\s*(\d+)\s*[=:：]\s*([0-3])", str(text)):
        out[int(m.group(1)) - 1] = int(m.group(2))
    return out


def to_int(v):
    try:
        return int(str(v).strip())
    except (ValueError, TypeError):
        return None


def load_records():
    recs = []
    for p in packet_files():
        if not p.exists():
            continue
        ws = openpyxl.load_workbook(p, data_only=True)["评分表"]
        hdr = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
        for r in range(2, ws.max_row + 1):
            def g(key):
                c = hdr.get(H[key])
                return ws.cell(r, c).value if c else None
            recs.append({
                "round_id": ws.cell(r, hdr["round_id"]).value,
                "subject": g("subject"), "teacher": g("teacher"), "cond": g("cond"),
                "p1": parse_diag(g("p1_diag")), "p2": parse_diag(g("p2_diag")),
                "p1_conf": to_int(g("p1_conf")), "p2_conf": to_int(g("p2_conf")),
                "gnd": g("gnd"), "consist": g("consist"), "useful": to_int(g("useful")),
                "relevance": to_int(g("relevance")), "ontarget": to_int(g("ontarget")),
                "elicit": g("elicit"), "fit": to_int(g("fit")), "attitude": g("attitude"),
                "icap": g("icap"), "depth": to_int(g("depth")), "advance": to_int(g("advance")),
            })
    return recs


def code_ai_stance(round_id):
    """HEURISTIC AI per-objective stance on the teacher's 3/2/1/0 scale.
    targeted objective -> probed gap -> 1; else if AI listed any mastery -> 3; else 0.
    TODO: replace with a human/LLM coding pass for publication-grade WOA."""
    r = ROUNDS.get(round_id)
    if not r:
        return {}
    stance = {}
    n_obj = len(r["objectives"])
    targeted = {t.get("objective_index") for t in (r["targeted_objectives"] or [])
                if isinstance(t.get("objective_index"), int)}
    has_mastery = bool((r["diagnoses"] or {}).get("mastered"))
    for i in range(n_obj):
        stance[i] = 1 if i in targeted else (3 if has_mastery else 0)
    return stance


def load_gold():
    p = HERE / "gold_truth.csv"
    if not p.exists():
        return None
    gold = defaultdict(dict)
    with open(p, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            gold[row["round_id"]][int(row["obj_index"])] = int(row["truth"])
    return gold


# ---------- reliability ----------
def fleiss_kappa(item_ratings):
    """item_ratings: list of lists of categorical labels (one list per item)."""
    cats = sorted({c for it in item_ratings for c in it if c is not None})
    items = [[c for c in it if c is not None] for it in item_ratings]
    items = [it for it in items if len(it) >= 2]
    if not items or not cats:
        return None
    n = len(items)
    pj = {c: 0 for c in cats}
    Pi = []
    for it in items:
        m = len(it); cnt = Counter(it)
        for c in cats:
            pj[c] += cnt[c]
        Pi.append((sum(v * v for v in cnt.values()) - m) / (m * (m - 1)))
    total = sum(len(it) for it in items)
    for c in cats:
        pj[c] /= total
    Pbar = sum(Pi) / n
    Pe = sum(v * v for v in pj.values())
    return (Pbar - Pe) / (1 - Pe) if (1 - Pe) else None


def krippendorff_alpha(units, metric="interval"):
    """units: list of lists of numeric ratings per item (missing dropped)."""
    def delta(a, b):
        return (a - b) ** 2 if metric == "interval" else (0 if a == b else 1)
    units = [[v for v in u if v is not None] for u in units]
    units = [u for u in units if len(u) >= 2]
    if not units:
        return None
    coinc = defaultdict(float)
    marg = defaultdict(float)
    n = 0
    for u in units:
        m = len(u)
        for i in range(m):
            for j in range(m):
                if i != j:
                    coinc[(u[i], u[j])] += 1.0 / (m - 1)
        for v in u:
            marg[v] += 1
            n += 1
    if n < 2:
        return None
    vals = sorted(marg)
    Do = sum(coinc[(a, b)] * delta(a, b) for a in vals for b in vals)
    De = sum(marg[a] * marg[b] * delta(a, b) for a in vals for b in vals) / (n - 1)
    return 1 - Do / De if De else None


# ---------- main ----------
def main():
    recs = load_records()
    filled = [r for r in recs if r["p1"] and r["p2"]]
    print(f"records loaded: {len(recs)} | with P1&P2 diagnosis filled: {len(filled)}")
    if not filled:
        print("\n>>> No ratings yet. Skeleton OK — fill packets and re-run.")
        print(">>> Optional: add gold_truth.csv (round_id,obj_index,truth) for 2x2 & calibration.")
        return

    gold = load_gold()

    # ---- per-objective influence rows ----
    inf = []  # one row per (record, objective) where both P1 & P2 present
    for r in filled:
        ai = code_ai_stance(r["round_id"])
        for oi in set(r["p1"]) & set(r["p2"]):
            p1, p2, a = r["p1"][oi], r["p2"][oi], ai.get(oi)
            inf.append({"rid": r["round_id"], "subject": r["subject"],
                        "teacher": r["teacher"], "cond": r["cond"],
                        "oi": oi, "p1": p1, "p2": p2, "ai": a,
                        "band": ROUNDS.get(r["round_id"], {}).get("band"),
                        "truth": (gold or {}).get(r["round_id"], {}).get(oi)})

    def block(rows, label):
        if not rows:
            return
        changed = [x for x in rows if x["p2"] != x["p1"]]
        switch = len(changed) / len(rows)
        tow = [x for x in changed if x["ai"] is not None and
               (x["p2"] - x["p1"]) * (x["ai"] - x["p1"]) > 0]
        woa = []
        for x in rows:
            if x["ai"] is not None and x["ai"] != x["p1"]:
                woa.append((x["p2"] - x["p1"]) / (x["ai"] - x["p1"]))
        dconf = [r["p2_conf"] - r["p1_conf"] for r in filled
                 if r["p1_conf"] is not None and r["p2_conf"] is not None]
        print(f"\n[{label}]  n_obj={len(rows)}")
        print(f"  改判率 switch rate:        {switch:.1%}")
        print(f"  向AI移动(改判中):          {len(tow)}/{len(changed)}"
              + (f" = {len(tow)/len(changed):.0%}" if changed else ""))
        print(f"  WOA mean:                  {sum(woa)/len(woa):.2f}" if woa else "  WOA: (no AI≠P1 cases)")
        if dconf and label == "ALL":
            print(f"  ΔConf mean (P2-P1):        {sum(dconf)/len(dconf):+.2f}")

    block(inf, "ALL")

    # ---- per-subject (each subject = its own 3 teachers) ----
    print("\n=== 按学科 (各学科独立的3位老师) ===")
    for subj in sorted({x["subject"] for x in inf if x["subject"]}):
        block([x for x in inf if x["subject"] == subj], subj)

    # ---- ±reasoning effect (pooled across subjects; each subject internally balanced) ----
    print("\n=== ±推理 effect (pooled) ===")
    for cond in ("+推理", "仅结论"):
        block([x for x in inf if x["cond"] == cond], cond)

    # ---- reliance 2x2 (needs gold) ----
    print("\n=== 依赖 2x2 ===")
    if not gold:
        print("  (skipped — provide gold_truth.csv)")
    else:
        cell = Counter()
        for x in inf:
            if x["truth"] is None or x["ai"] is None:
                continue
            moved = (x["p2"] - x["p1"]) * (x["ai"] - x["p1"]) > 0 and x["p2"] != x["p1"]
            ai_ok = x["ai"] == x["truth"]
            cell[("AI对" if ai_ok else "AI错", "改向AI" if moved else "未改向")] += 1
        for k in [("AI对", "改向AI"), ("AI对", "未改向"), ("AI错", "改向AI"), ("AI错", "未改向")]:
            tag = {("AI对", "改向AI"): "恰当依赖", ("AI对", "未改向"): "算法厌恶",
                   ("AI错", "改向AI"): "过度依赖(有害)", ("AI错", "未改向"): "恰当自信"}[k]
            print(f"  {k[0]} × {k[1]}: {cell[k]:>4}  [{tag}]")

    # ---- failure chain by reflection band ----
    print("\n=== 失败链 by 反思厚度 ===")
    byband = defaultdict(lambda: {"n": 0, "halluc": 0, "offtgt": [], "diseng": 0, "woa": []})
    for r in filled:
        b = ROUNDS.get(r["round_id"], {}).get("band")
        d = byband[b]; d["n"] += 1
        if r["gnd"] in ("个别臆造", "多数臆造"):
            d["halluc"] += 1
        if r["relevance"] is not None:
            d["offtgt"].append(r["relevance"])
        if r["attitude"] in ("空答或乱码", "敷衍"):
            d["diseng"] += 1
    for x in inf:
        if x["ai"] is not None and x["ai"] != x["p1"]:
            byband[x["band"]]["woa"].append((x["p2"] - x["p1"]) / (x["ai"] - x["p1"]))
    for b in ["薄", "中", "厚"]:
        d = byband.get(b)
        if not d or not d["n"]:
            continue
        rel = sum(d["offtgt"]) / len(d["offtgt"]) if d["offtgt"] else float("nan")
        woa = sum(d["woa"]) / len(d["woa"]) if d["woa"] else float("nan")
        print(f"  {b}: n={d['n']:>3} 臆造率={d['halluc']/d['n']:.0%} "
              f"追问相关均分={rel:.2f} 脱离率={d['diseng']/d['n']:.0%} WOA={woa:.2f}")
    _plot_failure_chain(byband)

    # ---- IRR within each subject panel (each round rated by its subject's 3 teachers) ----
    print("\n=== 评分员信度 (IRR) — 各学科独立面板 ===")
    def by_round(rows, field):
        m = defaultdict(list)
        for r in rows:
            m[r["round_id"]].append(r[field])
        return [v for v in m.values() if len([x for x in v if x is not None]) >= 2]

    def irr(rows, label):
        if not rows:
            return
        icap_k = fleiss_kappa(by_round(rows, "icap"))
        gnd_k = fleiss_kappa(by_round(rows, "gnd"))
        rel_a = krippendorff_alpha([[to_int(x) for x in v] for v in by_round(rows, "relevance")])
        fmt = lambda v: f"{v:.2f}" if isinstance(v, float) else str(v)
        print(f"  [{label:>4}] ICAP κ={fmt(icap_k)}  groundedness κ={fmt(gnd_k)}  追问相关 α={fmt(rel_a)}")

    for subj in sorted({r["subject"] for r in filled if r["subject"]}):
        irr([r for r in filled if r["subject"] == subj], subj)
    irr(filled, "pooled")


def _plot_failure_chain(byband):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("  (matplotlib not available — skipped figure)")
        return
    bands = [b for b in ["薄", "中", "厚"] if byband.get(b, {}).get("n")]
    if not bands:
        return
    hall = [byband[b]["halluc"] / byband[b]["n"] for b in bands]
    woa = [sum(byband[b]["woa"]) / len(byband[b]["woa"]) if byband[b]["woa"] else 0 for b in bands]
    xlabels = {"薄": "thin", "中": "mid", "厚": "thick"}
    xs = [xlabels[b] for b in bands]
    fig, ax1 = plt.subplots(figsize=(5, 3.2))
    ax1.plot(xs, hall, "o-", color="#C0392B", label="hallucination rate")
    ax1.set_ylabel("AI hallucination rate", color="#C0392B")
    ax2 = ax1.twinx()
    ax2.plot(xs, woa, "s--", color="#2E5496", label="WOA")
    ax2.set_ylabel("WOA (expert persuaded)", color="#2E5496")
    ax1.set_xlabel("student reflection thickness")
    fig.suptitle("Double jeopardy: thinner reflection -> more hallucination & more persuasion")
    fig.tight_layout()
    fig.savefig(HERE / "failure_chain.png", dpi=130)
    print("  -> saved failure_chain.png")


if __name__ == "__main__":
    main()
