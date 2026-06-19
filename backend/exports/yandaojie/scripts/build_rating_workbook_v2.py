"""Build the all-551-round Design-C reference workbook (not a teacher instrument).

Same 4-stage column layout as the packets, but every round in one sheet, reasoning
always shown, teacher/arm blank. Useful as a master reference. The actual rating
instruments are the per-teacher packets from gen_teacher_packets.py.
"""
from openpyxl import Workbook
from packet_schema import COLS, RCOLS, DV, build_sheet, build_legend
from yandaojie_rounds import build_rounds, DELIVERABLES

R_DV = {"S15": '"1,2,3,4,5"', "FAB": '"有,无"'}
OUT = str(DELIVERABLES / "teacher_rating_workbook_v2.xlsx")


def main():
    DELIVERABLES.mkdir(parents=True, exist_ok=True)
    rounds = build_rounds()  # all 551
    wb = Workbook()
    ws0 = wb.active; ws0.title = "使用说明"; build_legend(ws0)
    ws = wb.create_sheet("评分表")
    build_sheet(ws, COLS, rounds, teacher=None, arm_map=None, reasoning_mode="always", dvmap=DV)
    ws2 = wb.create_sheet("推理审计")
    build_sheet(ws2, RCOLS, rounds, reasoning_mode="always", dvmap=R_DV)
    wb.save(OUT)
    print(f"wrote {OUT}: {len(rounds)} rounds (reference master)")


if __name__ == "__main__":
    main()
