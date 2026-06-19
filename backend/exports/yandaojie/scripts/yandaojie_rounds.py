"""Shared round reconstruction for the Yandaojie expert-audit study.

build_rounds() -> list[dict], one per defense round, with BOTH formatted text
(for display) and raw structured fields (for analysis / AI-stance coding).
Sampling (~140, thin-oversampled) and reflection-length band are deterministic,
so the packet generator and the analysis script agree on the same rounds.
"""
import json
from collections import defaultdict
from pathlib import Path

def _find_base(start):
    """Locate the yandaojie export dir (the one containing real-only/raw),
    whether this module sits at the top level or inside scripts/."""
    p = start
    for _ in range(6):
        if (p / "real-only" / "raw").is_dir():
            return p
        p = p.parent
    return start.parent  # fallback


BASE = _find_base(Path(__file__).resolve().parent)
RAW = BASE / "real-only" / "raw"
DELIVERABLES = BASE / "deliverables"
TARGET_SAMPLE = 140
BAND_QUOTA = {"薄": 0.50, "中": 0.30, "厚": 0.20}


def _load(n):
    return [json.loads(l) for l in open(RAW / f"{n}.jsonl") if l.strip()]


def _reflen(s):
    return sum(len((r.get("learned") or "").strip()) for r in (s.get("reflections") or []))


def _fmt_obj(o):
    return "\n".join(f"{i+1}) {x}" for i, x in enumerate(o)) if o else ""


def _fmt_refl(s):
    out = []
    for r in (s.get("reflections") or []):
        idx = r.get("objective_index")
        tag = f"目标{idx+1}" if isinstance(idx, int) else "目标?"
        learned = (r.get("learned") or "").strip() or "（空）"
        q = (r.get("questions") or "").strip()
        out.append(f"{tag}：学到=「{learned}」" + (f"；疑问=「{q}」" if q else ""))
    return "\n".join(out)


def _fmt_diag(d, key):
    items = (d or {}).get(key) or []
    p = "M" if key == "mastered" else "N"
    return "\n".join(f"{p}{i+1}. {x}" for i, x in enumerate(items))


def _fmt_tgt(objs, tgts):
    out = []
    for t in (tgts or []):
        idx = t.get("objective_index")
        out.append(f"目标{(idx+1) if isinstance(idx,int) else '?'}：{t.get('reason') or ''}")
    return "\n".join(out)


def build_rounds():
    sessions = _load("sessions")
    questions = _load("defense_questions")
    turns = _load("defense_turns")
    sess = {s["session_id"]: s for s in sessions}
    ans = {(t.get("session_id"), t.get("round_index")): t for t in turns}

    lens = sorted(_reflen(s) for s in sessions)
    tb1, tb2 = lens[len(lens) // 3], lens[2 * len(lens) // 3]

    def band(s):
        n = _reflen(s)
        return "薄" if n <= tb1 else ("中" if n <= tb2 else "厚")

    by_sess = defaultdict(list)
    for q in questions:
        by_sess[q.get("session_id")].append(q)
    for sid in by_sess:
        by_sess[sid].sort(key=lambda q: (q.get("round_index") if q.get("round_index") is not None else -1))

    rounds = []
    for sid, qs in by_sess.items():
        s = sess.get(sid, {})
        objs = s.get("learning_objectives") or []
        prev = None
        for q in qs:
            ri = q.get("round_index")
            a = ans.get((sid, ri))
            at = (a or {}).get("answer_text")
            diags = q.get("diagnoses") or {}
            tgts = q.get("targeted_objectives") or []
            rounds.append({
                "round_id": f"{sid[:6]}-R{(ri+1) if isinstance(ri,int) else '?'}",
                "session_id": sid, "student_id": s.get("student_id"),
                "subject": s.get("subject_label"), "topic": s.get("subject_topic"),
                "round": (ri + 1) if isinstance(ri, int) else "", "round_index": ri,
                "objectives": objs, "reflections": s.get("reflections") or [],
                "reflen": _reflen(s), "band": band(s),
                "objectives_text": _fmt_obj(objs), "reflection_text": _fmt_refl(s),
                "prev_q": (prev or {}).get("q", ""), "prev_a": (prev or {}).get("a", ""),
                "diagnoses": diags, "targeted_objectives": tgts,
                "ai_mastered_text": _fmt_diag(diags, "mastered"),
                "ai_not_mastered_text": _fmt_diag(diags, "not_mastered"),
                "ai_targets_text": _fmt_tgt(objs, tgts),
                "ai_question": q.get("question") or "", "student_answer": at or "",
                "reasoning": q.get("reasoning_content") or "",
                "stratum": f"{s.get('subject_label')}×R{(ri+1) if isinstance(ri,int) else '?'}×{band(s)}",
            })
            prev = {"q": q.get("question") or "", "a": at or ""}

    # deterministic thin-oversampled sample (~140)
    by_band = defaultdict(list)
    for i, r in enumerate(rounds):
        by_band[r["band"]].append(i)
    for b in by_band:
        by_band[b].sort(key=lambda i: (rounds[i]["stratum"], rounds[i]["round_id"]))
    sample = set()
    for b, idxs in by_band.items():
        quota = min(len(idxs), max(1, round(TARGET_SAMPLE * BAND_QUOTA.get(b, 0.2))))
        step = len(idxs) / quota
        for k in range(quota):
            sample.add(idxs[int(k * step)])
    for i, r in enumerate(rounds):
        r["sample"] = "是" if i in sample else "否"
    return rounds


def sampled_rounds():
    rs = [r for r in build_rounds() if r["sample"] == "是"]
    rs.sort(key=lambda r: (r["stratum"], r["round_id"]))  # canonical order
    return rs


if __name__ == "__main__":
    rs = build_rounds()
    sm = [r for r in rs if r["sample"] == "是"]
    print(f"rounds={len(rs)} sampled={len(sm)}")
    from collections import Counter
    print("sample by band:", dict(Counter(r["band"] for r in sm)))
    print("sample by subject:", dict(Counter(r["subject"] for r in sm)))
