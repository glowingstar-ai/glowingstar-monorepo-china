"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Search,
  UserRound,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

type SessionSummary = {
  session_id: string;
  student_id?: string | null;
  stage?: string | null;
  subject_id?: string | null;
  subject_label?: string | null;
  subject_topic?: string | null;
  learning_objectives: string[];
  reflections: { objective_index: number; learned: string; questions: string }[];
  current_round_index?: number | null;
  completed_round_count: number;
  defense_turns: { round_index: number; question: string; answer_text: string; answered_at?: string }[];
  event_count: number;
  error_count: number;
  question_count: number;
  defense_turn_count: number;
  started_at?: string | null;
  last_seen_at?: string | null;
  completed_at?: string | null;
};

type StudentSummary = {
  student_id: string;
  session_count: number;
  last_seen_at?: string | null;
  sessions: SessionSummary[];
};

type OverviewResponse = {
  persistence_enabled: boolean;
  generated_at: string;
  session_count: number;
  students: StudentSummary[];
};

type DetailResponse = {
  persistence_enabled: boolean;
  generated_at: string;
  session: SessionSummary | null;
  events: Record<string, unknown>[];
  errors: Record<string, unknown>[];
  defense_turns: Record<string, unknown>[];
  generated_questions: Record<string, unknown>[];
};

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return DATE_TIME_FORMATTER.format(date);
}

function StatCard({
  icon,
  label,
  value,
}: Readonly<{ icon: JSX.Element; label: string; value: string | number }>): JSX.Element {
  return (
    <div className="rounded-3xl border border-[#E4D8C8] bg-white p-5 shadow-[0_10px_32px_rgba(52,42,28,0.06)]">
      <div className="flex items-center gap-3 text-[#8A5E2A]">
        {icon}
        <span className="text-sm font-semibold">{label}</span>
      </div>
      <p className="mt-3 text-3xl font-bold text-[#171717]">{value}</p>
    </div>
  );
}

function JsonBlock({ value }: Readonly<{ value: unknown }>): JSX.Element {
  return (
    <pre className="mt-3 max-h-72 overflow-auto rounded-2xl bg-[#171717] p-4 text-xs leading-5 text-white">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function YandaojieResearchDashboard(): JSX.Element {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DetailResponse | null>(null);
  const [query, setQuery] = useState("");
  const [isLoadingOverview, setIsLoadingOverview] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setIsLoadingOverview(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/yandaojie/research/overview?limit=500`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error("overview request failed");
      const payload = (await response.json()) as OverviewResponse;
      setOverview(payload);
      const firstSession = payload.students[0]?.sessions[0];
      setSelectedSessionId((current) => current ?? firstSession?.session_id ?? null);
    } catch (err) {
      console.error(err);
      setError("无法加载研究数据。");
    } finally {
      setIsLoadingOverview(false);
    }
  }, []);

  const loadDetail = useCallback(async (sessionId: string) => {
    setIsLoadingDetail(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/yandaojie/research/session/${sessionId}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error("detail request failed");
      setDetail((await response.json()) as DetailResponse);
    } catch (err) {
      console.error(err);
      setError("无法加载会话详情。");
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  useEffect(() => { void loadOverview(); }, [loadOverview]);
  useEffect(() => { if (selectedSessionId) void loadDetail(selectedSessionId); }, [loadDetail, selectedSessionId]);

  const allSessions = useMemo(() => {
    const list = overview?.students.flatMap((s) => s.sessions) ?? [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter((s) =>
      [s.student_id, s.session_id, s.subject_label, s.subject_topic, s.stage]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [overview, query]);

  const completedCount = allSessions.filter((s) => s.completed_at).length;
  const totalTurns = allSessions.reduce((sum, s) => sum + s.defense_turn_count, 0);
  const totalErrors = allSessions.reduce((sum, s) => sum + s.error_count, 0);

  const selectedSession = detail?.session;

  return (
    <main className="min-h-screen bg-[#F6F1E8] px-4 py-8 text-[#171717] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="rounded-[2rem] border border-[#E4D8C8] bg-white px-6 py-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)] sm:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#8A5E2A]">
                Internal Research
              </p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
                研道街 · 知识保卫数据
              </h1>
              <p className="mt-3 max-w-3xl text-base leading-7 text-[#5F5D57]">
                查看学生的学号、科目选择、反思内容、知识保卫问答记录和错误日志。
              </p>
            </div>
            <button
              onClick={() => void loadOverview()}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#171717] px-5 py-3 text-sm font-semibold text-white hover:bg-[#2A2A2A]"
            >
              <RefreshCw className="h-4 w-4" />
              刷新
            </button>
          </div>
          <p className="mt-4 text-sm text-[#6B665E]">
            生成时间：{formatDateTime(overview?.generated_at)} · 数据持久化：
            {overview?.persistence_enabled ? "已启用" : "未启用"}
          </p>
        </header>

        {error ? (
          <div className="mt-6 rounded-2xl border border-[#F3B6AE] bg-[#FCEDEC] p-4 text-sm text-[#A43D36]">
            {error}
          </div>
        ) : null}

        <section className="mt-6 grid gap-4 md:grid-cols-4">
          <StatCard icon={<UserRound className="h-5 w-5" />} label="会话数" value={overview?.session_count ?? 0} />
          <StatCard icon={<CheckCircle2 className="h-5 w-5" />} label="完成率" value={allSessions.length ? `${Math.round((completedCount / allSessions.length) * 100)}%` : "0%"} />
          <StatCard icon={<MessageSquareText className="h-5 w-5" />} label="保卫回答数" value={totalTurns} />
          <StatCard icon={<AlertTriangle className="h-5 w-5" />} label="错误数" value={totalErrors} />
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[390px_1fr]">
          <aside className="rounded-[2rem] border border-[#E4D8C8] bg-white p-5 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <div className="flex items-center gap-2 rounded-2xl border border-[#D8D2C7] px-3 py-2">
              <Search className="h-4 w-4 text-[#8A867E]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="min-h-9 flex-1 bg-transparent text-sm outline-none"
                placeholder="搜索学号、科目、会话..."
              />
            </div>

            <div className="mt-4 max-h-[680px] space-y-3 overflow-auto pr-1">
              {isLoadingOverview ? (
                <div className="flex items-center gap-2 text-sm text-[#5F5D57]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  加载中...
                </div>
              ) : null}

              {!isLoadingOverview && allSessions.length === 0 ? (
                <p className="text-sm text-[#5F5D57]">暂无匹配的会话。</p>
              ) : null}

              {(overview?.students ?? []).map((student) => (
                <section key={student.student_id} className="rounded-3xl border border-[#E4D8C8] bg-white p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8A5E2A]">学生</p>
                      <h2 className="mt-1 font-bold">{student.student_id}</h2>
                    </div>
                    <span className="rounded-full bg-[#F6F1E8] px-2.5 py-1 text-xs font-semibold text-[#6B665E]">
                      {student.session_count} 次
                    </span>
                  </div>
                  <div className="mt-3 space-y-2">
                    {student.sessions.map((session) => (
                      <button
                        key={session.session_id}
                        onClick={() => setSelectedSessionId(session.session_id)}
                        className={cn(
                          "w-full rounded-2xl border p-3 text-left transition hover:border-[#171717]",
                          selectedSessionId === session.session_id
                            ? "border-[#171717] bg-white"
                            : "border-[#E4D8C8] bg-[#FFFCF7]",
                        )}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold">{session.subject_label ?? "未选科目"} · {session.subject_topic ?? ""}</p>
                            <p className="mt-1 text-xs text-[#6B665E]">{formatDateTime(session.last_seen_at)}</p>
                          </div>
                          <ChevronRight className="h-4 w-4 text-[#8A867E]" />
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2 text-xs">
                          <span className="rounded-full bg-[#F6F1E8] px-2.5 py-1">
                            {session.completed_at ? "已完成" : session.stage ?? "未知"}
                          </span>
                          <span className="rounded-full bg-[#F6F1E8] px-2.5 py-1">
                            {session.completed_round_count}/5 轮
                          </span>
                          {session.error_count > 0 ? (
                            <span className="rounded-full bg-[#FCEDEC] px-2.5 py-1 text-[#A43D36]">
                              {session.error_count} 错误
                            </span>
                          ) : null}
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </aside>

          <section className="rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            {isLoadingDetail ? (
              <div className="flex items-center gap-2 text-sm text-[#5F5D57]">
                <Loader2 className="h-4 w-4 animate-spin" />
                加载会话详情...
              </div>
            ) : null}

            {!selectedSession ? (
              <p className="text-sm text-[#5F5D57]">选择一个会话以查看详情。</p>
            ) : (
              <div>
                <div className="flex flex-col gap-4 border-b border-[#E6E0D5] pb-5 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-[#8A5E2A]">
                      学号：{selectedSession.student_id ?? "未知"}
                    </p>
                    <h2 className="mt-1 text-2xl font-bold">
                      {selectedSession.subject_label ?? "未选科目"} · {selectedSession.subject_topic ?? ""}
                    </h2>
                    <p className="mt-2 text-xs text-[#5F5D57]">Session: {selectedSession.session_id}</p>
                  </div>
                  <div className="grid gap-2 text-sm text-[#5F5D57]">
                    <span className="inline-flex items-center gap-2">
                      <Clock3 className="h-4 w-4" />
                      开始 {formatDateTime(selectedSession.started_at)}
                    </span>
                    <span>完成 {formatDateTime(selectedSession.completed_at)}</span>
                    <span>轮次 {selectedSession.completed_round_count}/5</span>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-3xl bg-[#F6F1E8] p-5">
                    <p className="text-sm font-semibold">学生反思 - 学到了什么</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#5F5D57]">
                      {selectedSession.reflections?.[0]?.learned || "暂无数据"}
                    </p>
                  </div>
                  <div className="rounded-3xl bg-[#F6F1E8] p-5">
                    <p className="text-sm font-semibold">学生反思 - 疑问</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#5F5D57]">
                      {selectedSession.reflections?.[0]?.questions || "暂无数据"}
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <h3 className="text-lg font-bold">知识保卫问答</h3>
                  <div className="mt-3 space-y-4">
                    {(detail?.defense_turns ?? []).length === 0 ? (
                      <p className="text-sm text-[#5F5D57]">暂无保卫回答记录。</p>
                    ) : (
                      (detail?.defense_turns ?? []).map((turn, idx) => (
                        <article key={idx} className="rounded-3xl border border-[#E4D8C8] p-5">
                          <p className="font-semibold">第 {((turn as Record<string, unknown>).round_index as number ?? 0) + 1} 轮</p>
                          <p className="mt-3 font-semibold">{(turn as Record<string, unknown>).question as string}</p>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#5F5D57]">
                            {(turn as Record<string, unknown>).answer_text as string || "（未回答）"}
                          </p>
                          <p className="mt-2 text-xs text-[#6B665E]">
                            {formatDateTime((turn as Record<string, unknown>).answered_at as string)}
                          </p>
                        </article>
                      ))
                    )}
                  </div>
                </div>

                <div className="mt-6">
                  <h3 className="text-lg font-bold">生成的题目</h3>
                  <div className="mt-3 space-y-3">
                    {(detail?.generated_questions ?? []).length === 0 ? (
                      <p className="text-sm text-[#5F5D57]">暂无记录。</p>
                    ) : (
                      (detail?.generated_questions ?? []).map((q, idx) => (
                        <article key={idx} className="rounded-2xl bg-[#F6F1E8] p-4">
                          <p className="font-semibold">第 {((q.round_index as number) ?? 0) + 1} 轮</p>
                          <p className="mt-2 text-sm leading-6 text-[#5F5D57]">{q.question as string}</p>

                          {Array.isArray(q.targeted_objectives) && (q.targeted_objectives as Array<{objective_index: number; reason: string}>).length > 0 ? (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-xs font-semibold text-[#8A5E2A] hover:underline">
                                考察的教学目标
                              </summary>
                              <div className="mt-2 rounded-xl border border-[#E4D8C8] bg-white p-3">
                                <ul className="space-y-1.5">
                                  {(q.targeted_objectives as Array<{objective_index: number; reason: string}>).map((obj, oi) => (
                                    <li key={oi} className="text-xs leading-5 text-[#5F5D57]">
                                      <span className="font-semibold text-[#171717]">目标{obj.objective_index}:</span>{" "}
                                      {obj.reason}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </details>
                          ) : null}

                          {(q.diagnoses as {mastered?: string[]; not_mastered?: string[]}) && (
                            ((q.diagnoses as {mastered?: string[]; not_mastered?: string[]})?.mastered?.length ?? 0) > 0 ||
                            ((q.diagnoses as {mastered?: string[]; not_mastered?: string[]})?.not_mastered?.length ?? 0) > 0
                          ) ? (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-xs font-semibold text-[#256C42] hover:underline">
                                学生掌握情况诊断
                              </summary>
                              <div className="mt-2 rounded-xl border border-[#E4D8C8] bg-white p-3 text-xs leading-5">
                                {((q.diagnoses as {mastered?: string[]})?.mastered?.length ?? 0) > 0 ? (
                                  <div>
                                    <p className="font-semibold text-[#256C42]">已掌握:</p>
                                    <ul className="mt-1 list-disc pl-4 text-[#5F5D57]">
                                      {(q.diagnoses as {mastered: string[]}).mastered.map((item: string, i: number) => (
                                        <li key={i}>{item}</li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : null}
                                {((q.diagnoses as {not_mastered?: string[]})?.not_mastered?.length ?? 0) > 0 ? (
                                  <div className="mt-2">
                                    <p className="font-semibold text-[#A43D36]">未掌握:</p>
                                    <ul className="mt-1 list-disc pl-4 text-[#5F5D57]">
                                      {(q.diagnoses as {not_mastered: string[]}).not_mastered.map((item: string, i: number) => (
                                        <li key={i}>{item}</li>
                                      ))}
                                    </ul>
                                  </div>
                                ) : null}
                              </div>
                            </details>
                          ) : null}

                          {(q.reasoning_content as string) ? (
                            <details className="mt-3">
                              <summary className="cursor-pointer text-xs font-semibold text-[#6B665E] hover:underline">
                                查看AI思维过程
                              </summary>
                              <p className="mt-2 whitespace-pre-wrap rounded-xl bg-white p-3 text-xs leading-5 text-[#5F5D57]">
                                {q.reasoning_content as string}
                              </p>
                            </details>
                          ) : null}

                          <p className="mt-2 text-xs text-[#6B665E]">
                            {(q.model as string) ?? "unknown"} · {formatDateTime(q.generated_at as string)}
                          </p>
                        </article>
                      ))
                    )}
                  </div>
                </div>

                <div className="mt-6 grid gap-4 xl:grid-cols-2">
                  <section className="rounded-3xl border border-[#E4D8C8] p-5">
                    <h3 className="text-lg font-bold">事件</h3>
                    <div className="mt-3 space-y-3">
                      {(detail?.events ?? []).length === 0 ? (
                        <p className="text-sm text-[#5F5D57]">暂无记录。</p>
                      ) : (
                        (detail?.events ?? []).map((e, idx) => (
                          <article key={idx} className="rounded-2xl bg-[#F6F1E8] p-4">
                            <p className="font-semibold">{e.event_type as string ?? "event"}</p>
                            <p className="mt-1 text-xs text-[#6B665E]">
                              {e.stage as string ?? ""} · {formatDateTime(e.recorded_at as string)}
                            </p>
                            <JsonBlock value={e.payload} />
                          </article>
                        ))
                      )}
                    </div>
                  </section>
                  <section className="rounded-3xl border border-[#E4D8C8] p-5">
                    <h3 className="text-lg font-bold">错误</h3>
                    <div className="mt-3 space-y-3">
                      {(detail?.errors ?? []).length === 0 ? (
                        <p className="text-sm text-[#5F5D57]">暂无错误。</p>
                      ) : (
                        (detail?.errors ?? []).map((e, idx) => (
                          <article key={idx} className="rounded-2xl bg-[#F6F1E8] p-4">
                            <p className="font-semibold text-[#A43D36]">
                              {e.stage as string ?? "error"} · {e.error_scope as string ?? ""}
                            </p>
                            <p className="mt-2 text-sm leading-6 text-[#5F5D57]">{e.error_message as string}</p>
                            <JsonBlock value={e.metadata ?? {}} />
                          </article>
                        ))
                      )}
                    </div>
                  </section>
                </div>
              </div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}
