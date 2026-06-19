"""Compute data-quality metrics for the Yandaojie real-only export.

Run: python3 quality_report.py
Prints a series of markdown-ready tables to stdout.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from yandaojie_rounds import RAW  # robust base resolution (works from scripts/)


def load(name: str) -> list[dict]:
    out = []
    with (RAW / f"{name}.jsonl").open() as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


sessions = load("sessions")
questions = load("defense_questions")
turns = load("defense_turns")
events = load("events")
errors = load("errors")


def nonempty(v) -> bool:
    return bool(v) and bool(str(v).strip())


def pct(n, d) -> str:
    return f"{100*n/d:.0f}%" if d else "—"


print("\n############ 1. SAMPLE / PARTICIPANTS ############")
students = {s.get("student_id") for s in sessions}
subj = Counter(s.get("subject_label") for s in sessions)
topics = Counter(s.get("subject_topic") for s in sessions)
print(f"sessions={len(sessions)}  distinct_students={len(students)}  "
      f"subjects={len(subj)}  topics={len(topics)}")
print("by subject:", dict(subj))
print("by topic:")
for t, c in topics.most_common():
    print(f"   {c:>3}  {t}")

# sessions per student (repeat usage)
per_student = Counter(s.get("student_id") for s in sessions)
print("sessions/student distribution:",
      dict(Counter(per_student.values())))

print("\n############ 2. FUNNEL / STAGE REACHED ############")
stage_c = Counter(s.get("stage") for s in sessions)
for st, c in stage_c.most_common():
    print(f"   {c:>3} ({pct(c,len(sessions))})  stage={st}")
completed = [s for s in sessions if nonempty(s.get("completed_at"))]
print(f"completed_at set: {len(completed)} ({pct(len(completed),len(sessions))})")
crc = Counter(s.get("completed_round_count") for s in sessions)
print("completed_round_count dist:", dict(sorted(crc.items(), key=lambda x:(x[0] is None,x[0]))))
cri = Counter(s.get("current_round_index") for s in sessions)
print("current_round_index dist:", dict(sorted(cri.items(), key=lambda x:(x[0] is None,x[0]))))

print("\n############ 3. LEARNING OBJECTIVES + REFLECTIONS ############")
obj_counts = [len(s.get("learning_objectives") or []) for s in sessions]
has_obj = sum(1 for n in obj_counts if n > 0)
print(f"sessions with >=1 objective: {has_obj} ({pct(has_obj,len(sessions))})")
print(f"objectives/session: mean={statistics.mean(obj_counts):.2f} "
      f"median={statistics.median(obj_counts)} max={max(obj_counts)}")

# reflection fill quality
refl_total = refl_learned = refl_questions = refl_both = refl_any = 0
sess_with_any_refl = 0
for s in sessions:
    refls = s.get("reflections") or []
    any_here = False
    for r in refls:
        refl_total += 1
        l = nonempty(r.get("learned"))
        q = nonempty(r.get("questions"))
        refl_learned += l
        refl_questions += q
        refl_both += (l and q)
        refl_any += (l or q)
        any_here |= (l or q)
    if any_here:
        sess_with_any_refl += 1
print(f"reflection slots total={refl_total}")
print(f"  with 'learned' text:   {refl_learned} ({pct(refl_learned,refl_total)})")
print(f"  with 'questions' text: {refl_questions} ({pct(refl_questions,refl_total)})")
print(f"  with either:           {refl_any} ({pct(refl_any,refl_total)})")
print(f"sessions with >=1 filled reflection: {sess_with_any_refl} ({pct(sess_with_any_refl,len(sessions))})")

print("\n############ 4. DEFENSE QUESTIONS (AI-generated) ############")
print(f"total questions={len(questions)}")
qsess = {q.get("session_id") for q in questions}
print(f"distinct sessions with >=1 question: {len(qsess)} ({pct(len(qsess),len(sessions))})")
models = Counter(q.get("model") for q in questions)
print("models:", dict(models))
q_has_reason = sum(1 for q in questions if nonempty(q.get("reasoning_content")))
q_has_qtext = sum(1 for q in questions if nonempty(q.get("question")))
q_has_target = sum(1 for q in questions if (q.get("targeted_objectives") or []))
diag_mast = sum(1 for q in questions if (q.get("diagnoses") or {}).get("mastered"))
diag_notm = sum(1 for q in questions if (q.get("diagnoses") or {}).get("not_mastered"))
diag_any = sum(1 for q in questions if ((q.get("diagnoses") or {}).get("mastered") or (q.get("diagnoses") or {}).get("not_mastered")))
print(f"  question text present: {q_has_qtext} ({pct(q_has_qtext,len(questions))})")
print(f"  reasoning_content present: {q_has_reason} ({pct(q_has_reason,len(questions))})")
print(f"  targeted_objectives present: {q_has_target} ({pct(q_has_target,len(questions))})")
print(f"  diagnosis (mastered): {diag_mast} ({pct(diag_mast,len(questions))})")
print(f"  diagnosis (not_mastered): {diag_notm} ({pct(diag_notm,len(questions))})")
print(f"  diagnosis (any): {diag_any} ({pct(diag_any,len(questions))})")
qlen = [len(q.get("question") or "") for q in questions if nonempty(q.get("question"))]
if qlen:
    print(f"  question length chars: mean={statistics.mean(qlen):.0f} median={statistics.median(qlen)} min={min(qlen)} max={max(qlen)}")
rounds = Counter(q.get("round_index") for q in questions)
print("  questions by round_index:", dict(sorted(rounds.items(), key=lambda x:(x[0] is None,x[0]))))

print("\n############ 5. DEFENSE TURNS (student answers) ############")
print(f"total turns={len(turns)}")
tsess = {t.get("session_id") for t in turns}
print(f"distinct sessions with >=1 answer: {len(tsess)} ({pct(len(tsess),len(sessions))})")
ans_nonempty = [t for t in turns if nonempty(t.get("answer_text"))]
print(f"  non-empty answers: {len(ans_nonempty)} ({pct(len(ans_nonempty),len(turns))})")
alen = [len(t.get("answer_text") or "") for t in ans_nonempty]
if alen:
    print(f"  answer length chars: mean={statistics.mean(alen):.0f} median={statistics.median(alen)} min={min(alen)} max={max(alen)}")
    buckets = Counter()
    for n in alen:
        if n <= 2: buckets["1-2 (trivial)"] += 1
        elif n <= 10: buckets["3-10"] += 1
        elif n <= 30: buckets["11-30"] += 1
        elif n <= 80: buckets["31-80"] += 1
        else: buckets[">80"] += 1
    print("  answer length buckets:", dict(buckets))
# answered vs generated
print(f"  answered/generated ratio: {len(turns)}/{len(questions)} = {pct(len(turns),len(questions))}")

print("\n############ 6. ERRORS ############")
print(f"total errors={len(errors)}")
escope = Counter(e.get("error_scope") for e in errors)
estage = Counter(e.get("stage") for e in errors)
esess = {e.get("session_id") for e in errors if e.get("session_id")}
print("by scope:", dict(escope.most_common()))
print("by stage:", dict(estage.most_common()))
print(f"sessions touched by >=1 error: {len(esess)} ({pct(len(esess),len(sessions))})")
emsg = Counter((e.get("error_message") or "")[:60] for e in errors)
print("top error messages:")
for m, c in emsg.most_common(8):
    print(f"   {c:>3}  {m}")

print("\n############ 7. EVENTS ############")
print(f"total events={len(events)}")
etype = Counter(e.get("event_type") for e in events)
print("by type:", dict(etype.most_common()))

print("\n############ 8. REFERENTIAL INTEGRITY ############")
sess_ids = {s.get("session_id") for s in sessions}
orphan_q = sum(1 for q in questions if q.get("session_id") not in sess_ids)
orphan_t = sum(1 for t in turns if t.get("session_id") not in sess_ids)
orphan_e = sum(1 for e in errors if e.get("session_id") and e.get("session_id") not in sess_ids)
print(f"questions with no matching session: {orphan_q}")
print(f"turns with no matching session: {orphan_t}")
print(f"errors with no matching session: {orphan_e}")
# sessions with questions but no answers
q_by_sess = defaultdict(int)
for q in questions: q_by_sess[q.get("session_id")] += 1
t_by_sess = defaultdict(int)
for t in turns: t_by_sess[t.get("session_id")] += 1
gen_no_ans = sum(1 for sid in q_by_sess if t_by_sess.get(sid,0)==0)
print(f"sessions that got questions but submitted 0 answers: {gen_no_ans}")
