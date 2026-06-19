# 研道街 (Yandaojie) — 数据、专家评分与分析

LLM「诊断→答辩」教学循环的真实课堂数据，以及面向 CHI 投稿的专家评分研究材料。

## 目录结构

```
yandaojie/
├── real-only/              # 规范数据集：140 个真实学生会话的 JSONL + CSV（raw/、csv/）
├── 20260601T1030.../       # 历史导出快照（含 dev/QA），保留备查
├── supporting-materials/   # 课程支撑材料（HTML/PDF）
├── deliverables/           # 交付物：给老师 + 投稿用
└── scripts/                # 构建与分析脚本
```

## deliverables/

| 文件 | 用途 |
|---|---|
| `teacher_audit_protocol.docx` | 教师评分手册（协议说明 + 研究依据） |
| `packets/packet_<学科>_T1/T2/T3.xlsx` | **9 份老师专属评分包**：每学科 3 位本学科老师（数学 41 / 科学 49 / 英语 50 轮）；三阶段、学科内 ±推理同条目跨教师交叉、行随机化 |
| `assignment_key.csv` | 学科 × 每轮 × 三位老师的 ±推理 条件分配（分析时回合并） |
| `teacher_rating_workbook_v2.xlsx` | 全 551 轮的三阶段主表（参考用，非老师填写件） |
| `methods_results_skeleton.docx` | 论文方法/结果章骨架（含 RQ、占位结果、列→指标映射） |

## scripts/

路径会自动定位本目录（含 `real-only/raw`），可从任意位置运行。

| 脚本 | 作用 |
|---|---|
| `yandaojie_rounds.py` | 共享模块：重建每一轮 + 确定性分层抽样（其它脚本依赖它） |
| `quality_report.py` | 数据质量统计（规模/完成度/字段完整性/错误/失败率） |
| `build_rating_workbook_v2.py` | 生成 `deliverables/teacher_rating_workbook_v2.xlsx` |
| `gen_teacher_packets.py` | 生成 9 份老师包（每学科 3 份）+ `assignment_key.csv` 到 `deliverables/packets/` |
| `analyze_ratings.py` | 读填好的老师包 → WOA / 依赖2×2 / 信心校准 / ±推理效应 / 失败链 / IRR（按学科面板 + pooled） |

## 评分→分析流程

1. 每学科 3 位本学科老师（共 9 位）先做 norming（10 条本学科共同样本对齐锚点），再各填自己的 packet。
2. 资深裁定组产出 `deliverables/gold_truth.csv`（列：`round_id,obj_index,truth`，truth ∈ 3/2/1/0）。
3. （建议）把 `analyze_ratings.py` 中的 `code_ai_stance()` 启发式换成人工/LLM 对 AI 逐目标立场的编码。
4. `cd scripts && python3 analyze_ratings.py` → 指标 + `deliverables/failure_chain.png`，照 `methods_results_skeleton.docx` 的黄色占位填数。

依赖：`python3 -m pip install openpyxl matplotlib`（IRR 用内置实现，无需额外库）。
