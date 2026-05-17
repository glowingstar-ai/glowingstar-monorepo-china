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

type UsfResearchSessionSummary = {
  session_id: string;
  student_id?: string | null;
  stage?: string | null;
  module_id?: string | null;
  module_number?: number | null;
  module_topic?: string | null;
  module_week?: string | null;
  learning_objectives: string[];
  learned_response?: string | null;
  remaining_questions_response?: string | null;
  current_round_index?: number | null;
  completed_round_count: number;
  defense_turns: DefenseTurn[];
  question_count: number;
  transcript_count: number;
  defense_turn_count: number;
  event_count: number;
  error_count: number;
  started_at?: string | null;
  last_seen_at?: string | null;
  completed_at?: string | null;
};

type DefenseTurn = {
  round_index: number;
  question: string;
  answer_text: string;
  audio_transcript?: string | null;
  self_rating?: number | null;
  answered_at?: string | null;
};

type UsfResearchStudentSummary = {
  student_id: string;
  session_count: number;
  last_seen_at?: string | null;
  sessions: UsfResearchSessionSummary[];
};

type UsfResearchOverviewResponse = {
  persistence_enabled: boolean;
  generated_at: string;
  session_count: number;
  students: UsfResearchStudentSummary[];
};

type UsfResearchArtifactRecord = {
  item_key: string;
  item_type: string;
  student_id?: string | null;
  module_id?: string | null;
  module_number?: number | null;
  module_topic?: string | null;
  round_index?: number | null;
  question?: string | null;
  answer_text?: string | null;
  audio_transcript?: string | null;
  self_rating?: number | null;
  transcript?: string | null;
  audio_mime_type?: string | null;
  audio_bucket?: string | null;
  audio_key?: string | null;
  audio_url?: string | null;
  audio_content_type?: string | null;
  audio_size_bytes?: number | null;
  model?: string | null;
  prompt?: string | null;
  learning_objectives: string[];
  learned_response?: string | null;
  remaining_questions_response?: string | null;
  previous_turns: Record<string, unknown>[];
  answered_at?: string | null;
  created_at?: string | null;
};

type UsfResearchEventRecord = {
  item_key: string;
  event_id?: string | null;
  student_id?: string | null;
  event_type?: string | null;
  stage?: string | null;
  round_index?: number | null;
  client_timestamp?: string | null;
  recorded_at?: string | null;
  payload: Record<string, unknown>;
};

type UsfResearchErrorRecord = {
  item_key: string;
  error_id?: string | null;
  student_id?: string | null;
  stage?: string | null;
  error_scope?: string | null;
  error_message?: string | null;
  raw_error?: string | null;
  round_index?: number | null;
  request_id?: string | null;
  metadata: Record<string, unknown>;
  recorded_at?: string | null;
};

type UsfResearchSessionDetailResponse = {
  persistence_enabled: boolean;
  generated_at: string;
  session?: UsfResearchSessionSummary | null;
  generated_questions: UsfResearchArtifactRecord[];
  transcripts: UsfResearchArtifactRecord[];
  defense_turns: UsfResearchArtifactRecord[];
  events: UsfResearchEventRecord[];
  errors: UsfResearchErrorRecord[];
};

const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function formatDateTime(value?: string | null): string {
  if (!value) return "No timestamp";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return DATE_TIME_FORMATTER.format(date);
}

function formatPercent(value: number, total: number): string {
  if (total === 0) return "0%";
  return `${Math.round((value / total) * 100)}%`;
}

function JsonBlock({ value }: Readonly<{ value: unknown }>): JSX.Element {
  return (
    <pre className="mt-3 max-h-72 overflow-auto rounded-2xl bg-[#171717] p-4 text-xs leading-5 text-white">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
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

export default function UsfResearchDashboard(): JSX.Element {
  const [overview, setOverview] = useState<UsfResearchOverviewResponse | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [detail, setDetail] = useState<UsfResearchSessionDetailResponse | null>(null);
  const [query, setQuery] = useState("");
  const [isLoadingOverview, setIsLoadingOverview] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setIsLoadingOverview(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/usf/research/overview?limit=500`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("USF research overview request failed");
      }
      const payload = (await response.json()) as UsfResearchOverviewResponse;
      setOverview(payload);
      const firstSession = payload.students[0]?.sessions[0];
      setSelectedSessionId((current) => current ?? firstSession?.session_id ?? null);
    } catch (requestError) {
      console.error(requestError);
      setError("Unable to load USF research overview.");
    } finally {
      setIsLoadingOverview(false);
    }
  }, []);

  const loadDetail = useCallback(async (sessionId: string) => {
    setIsLoadingDetail(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/usf/research/session/${sessionId}`, {
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("USF research session request failed");
      }
      setDetail((await response.json()) as UsfResearchSessionDetailResponse);
    } catch (requestError) {
      console.error(requestError);
      setError("Unable to load the selected USF session.");
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (!selectedSessionId) return;
    void loadDetail(selectedSessionId);
  }, [loadDetail, selectedSessionId]);

  const sessions = useMemo(() => {
    const allSessions = overview?.students.flatMap((student) => student.sessions) ?? [];
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return allSessions;
    return allSessions.filter((session) => {
      const searchable = [
        session.student_id,
        session.session_id,
        session.module_topic,
        session.stage,
        session.module_id,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return searchable.includes(normalizedQuery);
    });
  }, [overview, query]);

  const groupedStudents = useMemo(() => {
    type ModuleGroup = {
      moduleKey: string;
      moduleNumber?: number | null;
      moduleTopic: string;
      completedAttemptCount: number;
      sessions: UsfResearchSessionSummary[];
    };
    type StudentGroup = {
      studentId: string;
      lastSeenAt?: string | null;
      modules: ModuleGroup[];
    };

    const studentsById = new Map<
      string,
      {
        studentId: string;
        lastSeenAt?: string | null;
        modulesByKey: Map<string, ModuleGroup>;
      }
    >();

    for (const session of sessions) {
      const studentId = session.student_id ?? "Unknown student";
      const student = studentsById.get(studentId) ?? {
        studentId,
        lastSeenAt: null,
        modulesByKey: new Map<string, ModuleGroup>(),
      };
      const lastSeenAt = session.last_seen_at ?? session.started_at;
      if (lastSeenAt && (!student.lastSeenAt || lastSeenAt > student.lastSeenAt)) {
        student.lastSeenAt = lastSeenAt;
      }

      const moduleKey = session.module_id ?? session.module_topic ?? "unknown-module";
      const moduleGroup = student.modulesByKey.get(moduleKey) ?? {
        moduleKey,
        moduleNumber: session.module_number,
        moduleTopic: session.module_topic ?? "No module selected",
        completedAttemptCount: 0,
        sessions: [],
      };
      moduleGroup.sessions.push(session);
      if (session.completed_at) {
        moduleGroup.completedAttemptCount += 1;
      }
      student.modulesByKey.set(moduleKey, moduleGroup);
      studentsById.set(studentId, student);
    }

    return Array.from(studentsById.values())
      .map<StudentGroup>((student) => ({
        studentId: student.studentId,
        lastSeenAt: student.lastSeenAt,
        modules: Array.from(student.modulesByKey.values())
          .map((moduleGroup) => ({
            ...moduleGroup,
            sessions: moduleGroup.sessions.sort(
              (first, second) =>
                (second.last_seen_at ?? second.started_at ?? "").localeCompare(
                  first.last_seen_at ?? first.started_at ?? "",
                ),
            ),
          }))
          .sort((first, second) => {
            const firstNumber = first.moduleNumber ?? Number.MAX_SAFE_INTEGER;
            const secondNumber = second.moduleNumber ?? Number.MAX_SAFE_INTEGER;
            if (firstNumber !== secondNumber) return firstNumber - secondNumber;
            return first.moduleTopic.localeCompare(second.moduleTopic);
          }),
      }))
      .sort((first, second) => (second.lastSeenAt ?? "").localeCompare(first.lastSeenAt ?? ""));
  }, [sessions]);

  const selectedSession = detail?.session;
  const completedSessions = sessions.filter((session) => session.completed_at).length;
  const totalErrors = sessions.reduce((sum, session) => sum + session.error_count, 0);
  const totalTurns = sessions.reduce((sum, session) => sum + session.defense_turn_count, 0);

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
                USF Defense Data
              </h1>
              <p className="mt-3 max-w-3xl text-base leading-7 text-[#5F5D57]">
                Review collected student IDs, module choices, reflections, generated defense
                questions, answers, events, and errors.
              </p>
            </div>
            <button
              onClick={() => void loadOverview()}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#171717] px-5 py-3 text-sm font-semibold text-white hover:bg-[#2A2A2A]"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
          <p className="mt-4 text-sm text-[#6B665E]">
            Generated: {formatDateTime(overview?.generated_at)} · Persistence:{" "}
            {overview?.persistence_enabled ? "enabled" : "disabled or unavailable"}
          </p>
        </header>

        {error ? (
          <div className="mt-6 rounded-2xl border border-[#F3B6AE] bg-[#FCEDEC] p-4 text-sm text-[#A43D36]">
            {error}
          </div>
        ) : null}

        <section className="mt-6 grid gap-4 md:grid-cols-4">
          <StatCard
            icon={<UserRound className="h-5 w-5" />}
            label="Sessions"
            value={overview?.session_count ?? 0}
          />
          <StatCard
            icon={<CheckCircle2 className="h-5 w-5" />}
            label="Completion"
            value={formatPercent(completedSessions, sessions.length)}
          />
          <StatCard
            icon={<MessageSquareText className="h-5 w-5" />}
            label="Defense Answers"
            value={totalTurns}
          />
          <StatCard
            icon={<AlertTriangle className="h-5 w-5" />}
            label="Errors"
            value={totalErrors}
          />
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[390px_1fr]">
          <aside className="rounded-[2rem] border border-[#E4D8C8] bg-white p-5 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <div className="flex items-center gap-2 rounded-2xl border border-[#D8D2C7] px-3 py-2">
              <Search className="h-4 w-4 text-[#8A867E]" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="min-h-9 flex-1 bg-transparent text-sm outline-none"
                placeholder="Search student, module, session..."
              />
            </div>

            <div className="mt-4 max-h-[680px] space-y-3 overflow-auto pr-1">
              {isLoadingOverview ? (
                <div className="flex items-center gap-2 text-sm text-[#5F5D57]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading sessions...
                </div>
              ) : null}

              {!isLoadingOverview && sessions.length === 0 ? (
                <p className="text-sm text-[#5F5D57]">No sessions match this search.</p>
              ) : null}

              {groupedStudents.map((student) => (
                <section
                  key={student.studentId}
                  className="rounded-3xl border border-[#E4D8C8] bg-white p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#8A5E2A]">
                        Student
                      </p>
                      <h2 className="mt-1 font-bold">{student.studentId}</h2>
                    </div>
                    <span className="rounded-full bg-[#F6F1E8] px-2.5 py-1 text-xs font-semibold text-[#6B665E]">
                      {student.modules.length} modules
                    </span>
                  </div>

                  <div className="mt-4 space-y-4">
                    {student.modules.map((moduleGroup) => (
                      <section key={moduleGroup.moduleKey} className="rounded-2xl bg-[#FBF8F2] p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs font-semibold text-[#8A5E2A]">
                              {moduleGroup.moduleNumber
                                ? `Module ${moduleGroup.moduleNumber}`
                                : "Module"}
                            </p>
                            <h3 className="mt-1 text-sm font-bold">{moduleGroup.moduleTopic}</h3>
                          </div>
                          <span className="shrink-0 rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-[#6B665E]">
                            {moduleGroup.completedAttemptCount}/{moduleGroup.sessions.length} complete
                          </span>
                        </div>

                        <div className="mt-3 space-y-2">
                          {moduleGroup.sessions.map((session, index) => (
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
                                  <p className="text-sm font-semibold">
                                    Attempt {moduleGroup.sessions.length - index}
                                  </p>
                                  <p className="mt-1 text-xs text-[#6B665E]">
                                    Last seen {formatDateTime(session.last_seen_at)}
                                  </p>
                                </div>
                                <ChevronRight className="h-4 w-4 text-[#8A867E]" />
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                                <span className="rounded-full bg-[#F6F1E8] px-2.5 py-1">
                                  {session.completed_at ? "complete" : session.stage ?? "unknown"}
                                </span>
                                <span className="rounded-full bg-[#F6F1E8] px-2.5 py-1">
                                  {session.completed_round_count}/5 rounds
                                </span>
                                {session.error_count > 0 ? (
                                  <span className="rounded-full bg-[#FCEDEC] px-2.5 py-1 text-[#A43D36]">
                                    {session.error_count} errors
                                  </span>
                                ) : null}
                              </div>
                            </button>
                          ))}
                        </div>
                      </section>
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
                Loading session detail...
              </div>
            ) : null}

            {!selectedSession ? (
              <p className="text-sm text-[#5F5D57]">Select a session to inspect collected data.</p>
            ) : (
              <div>
                <div className="flex flex-col gap-4 border-b border-[#E6E0D5] pb-5 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-[#8A5E2A]">
                      {selectedSession.student_id ?? "Unknown student"}
                    </p>
                    <h2 className="mt-1 text-2xl font-bold">
                      {selectedSession.module_topic ?? "No module selected"}
                    </h2>
                    <p className="mt-2 text-sm text-[#5F5D57]">
                      Session {selectedSession.session_id}
                    </p>
                  </div>
                  <div className="grid gap-2 text-sm text-[#5F5D57] sm:grid-cols-2">
                    <span className="inline-flex items-center gap-2">
                      <Clock3 className="h-4 w-4" />
                      Started {formatDateTime(selectedSession.started_at)}
                    </span>
                    <span>Completed {formatDateTime(selectedSession.completed_at)}</span>
                    <span>Rounds {selectedSession.completed_round_count}/5</span>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 lg:grid-cols-2">
                  <div className="rounded-3xl bg-[#F6F1E8] p-5">
                    <p className="text-sm font-semibold">What they learned</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#5F5D57]">
                      {selectedSession.learned_response || "No response saved."}
                    </p>
                  </div>
                  <div className="rounded-3xl bg-[#F6F1E8] p-5">
                    <p className="text-sm font-semibold">Remaining questions</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#5F5D57]">
                      {selectedSession.remaining_questions_response || "No response saved."}
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <h3 className="text-lg font-bold">Defense Answers</h3>
                  <div className="mt-3 space-y-4">
                    {(detail?.defense_turns ?? []).length === 0 ? (
                      <p className="text-sm text-[#5F5D57]">No defense answers saved yet.</p>
                    ) : (
                      detail?.defense_turns.map((turn) => (
                        <article key={turn.item_key} className="rounded-3xl border border-[#E4D8C8] p-5">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="font-semibold">Round {(turn.round_index ?? 0) + 1}</p>
                          </div>
                          <p className="mt-3 font-semibold">{turn.question}</p>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#5F5D57]">
                            {turn.answer_text}
                          </p>
                        </article>
                      ))
                    )}
                  </div>
                </div>

                <div className="mt-6">
                  <DetailList
                    title="Generated Questions"
                    items={detail?.generated_questions ?? []}
                    render={(item) => (
                      <>
                        <p className="font-semibold">Round {(item.round_index ?? 0) + 1}</p>
                        <p className="mt-2 text-sm leading-6 text-[#5F5D57]">{item.question}</p>
                        <p className="mt-2 text-xs text-[#6B665E]">
                          {item.model ?? "unknown model"} · {formatDateTime(item.created_at)}
                        </p>
                      </>
                    )}
                  />
                </div>

                <div className="mt-6 grid gap-4 xl:grid-cols-2">
                  <DetailList
                    title="Events"
                    items={detail?.events ?? []}
                    render={(item) => (
                      <>
                        <p className="font-semibold">{item.event_type ?? "event"}</p>
                        <p className="mt-1 text-xs text-[#6B665E]">
                          {item.stage ?? "unknown stage"} · {formatDateTime(item.recorded_at)}
                        </p>
                        <JsonBlock value={item.payload} />
                      </>
                    )}
                  />
                  <DetailList
                    title="Errors"
                    items={detail?.errors ?? []}
                    render={(item) => (
                      <>
                        <p className="font-semibold text-[#A43D36]">
                          {item.stage ?? "error"} · {item.error_scope ?? "unknown"}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-[#5F5D57]">
                          {item.error_message}
                        </p>
                        <JsonBlock value={item.metadata} />
                      </>
                    )}
                  />
                </div>
              </div>
            )}
          </section>
        </section>
      </div>
    </main>
  );
}

function DetailList<T extends { item_key: string }>({
  items,
  render,
  title,
}: Readonly<{
  items: T[];
  render: (item: T) => JSX.Element;
  title: string;
}>): JSX.Element {
  return (
    <section className="rounded-3xl border border-[#E4D8C8] p-5">
      <h3 className="text-lg font-bold">{title}</h3>
      <div className="mt-3 space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-[#5F5D57]">No records.</p>
        ) : (
          items.map((item) => (
            <article key={item.item_key} className="rounded-2xl bg-[#F6F1E8] p-4">
              {render(item)}
            </article>
          ))
        )}
      </div>
    </section>
  );
}
