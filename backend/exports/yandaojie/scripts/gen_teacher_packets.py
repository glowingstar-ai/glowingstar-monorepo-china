"""Generate 9 per-subject teacher packets for Design C (staged disclosure).

* Each subject (数学/科学/英语) gets its own 3 teachers; every round in a subject
  is rated by all 3 of that subject's teachers (full crossing -> IRR).
* Every teacher does the 4-stage ladder on every round:
    P1 盲评 -> P2a 看AI结论后重评 -> P2b 再评 -> P3 评AI质量.
* The P2b step depends on the round's ARM (within-teacher, balanced 50/50):
    推理臂 -> sees AI reasoning at P2b;  控制臂 -> no new info (re-rate baseline).
  Arms are assigned by a 6-row balanced rotation so each teacher is ~50/50 and
  each round appears in both arms across the 3 teachers (item不混淆).
* Each packet is presented in a teacher-specific randomized row order.

Outputs: deliverables/packets/packet_<subject>_T{1,2,3}.xlsx, assignment_key.csv
"""
import csv
import hashlib
from openpyxl import Workbook
from packet_schema import COLS, RCOLS, DV, build_sheet, build_legend
from yandaojie_rounds import sampled_rounds, DELIVERABLES

TEACHERS = ["T1", "T2", "T3"]
SUBJECTS = ["数学", "科学", "英语"]
# 6-row balanced rotation of (T1,T2,T3) arms; R=推理臂, C=控制臂
ROT = [
    ("推理臂", "推理臂", "控制臂"),
    ("推理臂", "控制臂", "推理臂"),
    ("控制臂", "推理臂", "推理臂"),
    ("控制臂", "控制臂", "推理臂"),
    ("控制臂", "推理臂", "控制臂"),
    ("推理臂", "控制臂", "控制臂"),
]
R_DV = {"S15": '"1,2,3,4,5"', "FAB": '"有,无"'}


def order_for(seed, rounds):
    return sorted(rounds, key=lambda r: hashlib.md5(f"{r['round_id']}|{seed}".encode()).hexdigest())


def main():
    packdir = DELIVERABLES / "packets"
    packdir.mkdir(parents=True, exist_ok=True)
    sample = sampled_rounds()
    key_rows = []

    for subj in SUBJECTS:
        srs = [r for r in sample if r["subject"] == subj]
        arm = {t: {} for t in TEACHERS}
        for i, r in enumerate(srs):
            pat = ROT[i % len(ROT)]
            for t, a in zip(TEACHERS, pat):
                arm[t][r["round_id"]] = a

        for t in TEACHERS:
            wb = Workbook()
            ws0 = wb.active; ws0.title = "使用说明"; build_legend(ws0)
            ws = wb.create_sheet("评分表")
            ordered = order_for(f"{subj}|{t}", srs)
            build_sheet(ws, COLS, ordered, teacher=t, arm_map=arm[t], reasoning_mode="by_arm", dvmap=DV)
            ws2 = wb.create_sheet("推理审计")
            plus = [r for r in ordered if arm[t][r["round_id"]] == "推理臂"]
            build_sheet(ws2, RCOLS, plus, teacher=t, arm_map=arm[t], reasoning_mode="always", dvmap=R_DV)
            wb.save(str(packdir / f"packet_{subj}_{t}.xlsx"))
            n = sum(1 for v in arm[t].values() if v == "推理臂")
            print(f"{subj} {t}: 推理臂 {n}/{len(srs)}  控制臂 {len(srs)-n}")

        mix = sum(1 for r in srs if len({arm[t][r['round_id']] for t in TEACHERS}) == 2)
        print(f"  {subj}: rounds seen in BOTH arms across teachers: {mix}/{len(srs)}")
        for i, r in enumerate(srs):
            key_rows.append([subj, i, r["round_id"], r["band"], r["stratum"],
                             arm["T1"][r["round_id"]], arm["T2"][r["round_id"]], arm["T3"][r["round_id"]]])

    with open(DELIVERABLES / "assignment_key.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["subject", "idx_in_subject", "round_id", "band", "stratum",
                    "T1_arm", "T2_arm", "T3_arm"])
        w.writerows(key_rows)
    print(f"wrote {len(SUBJECTS) * len(TEACHERS)} packets to deliverables/packets/ + assignment_key.csv")


if __name__ == "__main__":
    main()
