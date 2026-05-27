"use client";

import {
  CheckCircle2,
  Loader2,
  SendHorizonal,
  Timer,
} from "lucide-react";
import {
  type ButtonHTMLAttributes,
  type ChangeEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import { cn } from "@/lib/utils";
import type { YandaojieSubject } from "@/lib/yandaojie";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEFENSE_ROUNDS_PER_OBJECTIVE = 5;
const ROUND_SECONDS = 60;

type Stage = "student-id" | "reflection" | "defense" | "complete";

type DefenseTurn = {
  roundIndex: number;
  question: string;
  answerText: string;
  answeredAt: string;
};

type QuestionResponse = {
  model: string;
  round_index: number;
  question: string;
  generated_at: string;
  persistence_enabled: boolean;
};

type SessionStartResponse = {
  session_id: string;
  started_at: string;
  persistence_enabled: boolean;
};

type SnapshotResponse = {
  saved_at: string;
  persistence_enabled: boolean;
};

type TurnResponse = {
  saved_at: string;
  persistence_enabled: boolean;
  completed_round_count: number;
};

type Props = {
  subject: YandaojieSubject | null;
  subjects: YandaojieSubject[];
};

function PrimaryButton({
  children,
  className,
  ...props
}: Readonly<ButtonHTMLAttributes<HTMLButtonElement>>): JSX.Element {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#171717] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#2A2A2A] disabled:cursor-not-allowed disabled:bg-[#D8D2C7] disabled:text-[#7B766D]",
        className,
      )}
    >
      {children}
    </button>
  );
}

function SecondaryButton({
  children,
  className,
  ...props
}: Readonly<ButtonHTMLAttributes<HTMLButtonElement>>): JSX.Element {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-[#D8D2C7] bg-white px-5 py-3 text-sm font-semibold text-[#171717] transition-colors hover:border-[#171717] hover:bg-[#FBF8F2] disabled:cursor-not-allowed disabled:border-[#E6E0D5] disabled:text-[#9A968D]",
        className,
      )}
    >
      {children}
    </button>
  );
}

function StepPill({
  active,
  complete,
  label,
}: Readonly<{ active: boolean; complete: boolean; label: string }>): JSX.Element {
  return (
    <span
      className={cn(
        "rounded-full border px-3 py-1 text-xs font-semibold",
        active && "border-[#171717] bg-[#171717] text-white",
        complete && !active && "border-[#B8DEC5] bg-[#E8F5EC] text-[#256C42]",
        !active && !complete && "border-[#E1DBD0] bg-white text-[#6E675D]",
      )}
    >
      {label}
    </span>
  );
}

function formatSeconds(seconds: number): string {
  return `00:${String(Math.max(seconds, 0)).padStart(2, "0")}`;
}

export default function YandaojieDefenseExperience({
  subject,
  subjects,
}: Readonly<Props>): JSX.Element {
  const [stage, setStage] = useState<Stage>("student-id");
  const [studentIdDraft, setStudentIdDraft] = useState("");
  const [studentId, setStudentId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [reflectionLearned, setReflectionLearned] = useState("");
  const [reflectionQuestions, setReflectionQuestions] = useState("");
  const [currentRoundIndex, setCurrentRoundIndex] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [answerDraft, setAnswerDraft] = useState("");
  const [turns, setTurns] = useState<DefenseTurn[]>([]);
  const [secondsRemaining, setSecondsRemaining] = useState(ROUND_SECONDS);
  const [isStartingSession, setIsStartingSession] = useState(false);
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [isGeneratingQuestion, setIsGeneratingQuestion] = useState(false);
  const [isSavingTurn, setIsSavingTurn] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [defenseError, setDefenseError] = useState<string | null>(null);
  const [completedAt, setCompletedAt] = useState<string | null>(null);
  const [persistenceEnabled, setPersistenceEnabled] = useState<boolean | null>(
    null,
  );
  const timedOutRoundRef = useRef<string | null>(null);

  const activeSubject = subject ?? subjects[0] ?? null;

  const trimmedStudentId = studentIdDraft.trim();
  const isRoundTimedOut =
    stage === "defense" && currentQuestion.length > 0 && secondsRemaining === 0;
  const canSubmitReflection =
    activeSubject !== null && reflectionLearned.trim().length > 0;
  const canSubmitTurn =
    currentQuestion.length > 0 &&
    answerDraft.trim().length > 0 &&
    !isGeneratingQuestion &&
    !isSavingTurn;

  useEffect(() => {
    if (stage !== "defense" || !currentQuestion) return;
    setSecondsRemaining(ROUND_SECONDS);
    const interval = window.setInterval(() => {
      setSecondsRemaining((v) => {
        if (v <= 1) {
          window.clearInterval(interval);
          return 0;
        }
        return v - 1;
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [currentQuestion, currentRoundIndex, stage]);

  useEffect(() => {
    if (!isRoundTimedOut) return;
    const roundKey = `${currentRoundIndex}:${currentQuestion}`;
    if (timedOutRoundRef.current === roundKey) return;
    timedOutRoundRef.current = roundKey;
    void saveTurn({ allowEmptyAnswer: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRoundTimedOut, currentQuestion, currentRoundIndex]);

  useEffect(() => {
    if (!sessionId || !studentId) return;
    const timeout = window.setTimeout(() => {
      void saveSnapshot(stage);
    }, 400);
    return () => window.clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    completedAt,
    currentRoundIndex,
    reflections,
    sessionId,
    stage,
    studentId,
    turns,
  ]);

  const postEvent = async (
    eventType: string,
    payload: Record<string, unknown> = {},
  ): Promise<void> => {
    if (!sessionId || !studentId) return;
    try {
      await fetch(`${API_BASE}/yandaojie/session/event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          event_type: eventType,
          stage,
          round_index: currentRoundIndex,
          client_timestamp: new Date().toISOString(),
          payload,
        }),
      });
    } catch (error) {
      console.error("Unable to persist yandaojie event", error);
    }
  };

  const saveSnapshot = async (nextStage: Stage): Promise<void> => {
    if (!sessionId || !studentId || !activeSubject) return;
    setIsSavingSnapshot(true);
    try {
      const response = await fetch(`${API_BASE}/yandaojie/session/snapshot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          stage: nextStage,
          subject_id: activeSubject.id,
          subject_label: activeSubject.label,
          subject_topic: activeSubject.topic,
          learning_objectives: activeSubject.learningObjectives,
          reflections: [{
            objective_index: 0,
            learned: reflectionLearned,
            questions: reflectionQuestions,
          }],
          current_round_index: currentRoundIndex,
          completed_round_count: turns.length,
          defense_turns: turns.map((t) => ({
            round_index: t.roundIndex,
            question: t.question,
            answer_text: t.answerText,
            answered_at: t.answeredAt,
          })),
          completed_at: completedAt,
        }),
      });
      if (!response.ok) throw new Error("snapshot failed");
      const data = (await response.json()) as SnapshotResponse;
      setPersistenceEnabled(data.persistence_enabled);
    } catch (error) {
      console.error("Unable to persist yandaojie snapshot", error);
    } finally {
      setIsSavingSnapshot(false);
    }
  };

  const startSession = async (): Promise<void> => {
    if (!trimmedStudentId) {
      setSessionError("请输入学号。");
      return;
    }
    setSessionError(null);
    setIsStartingSession(true);
    try {
      const response = await fetch(`${API_BASE}/yandaojie/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: trimmedStudentId }),
      });
      if (!response.ok) throw new Error("start failed");
      const data = (await response.json()) as SessionStartResponse;
      setPersistenceEnabled(data.persistence_enabled);
      setStudentId(trimmedStudentId);
      setSessionId(data.session_id);
      setStage("reflection");
    } catch (error) {
      console.error(error);
      setSessionError("无法开始会话，请重试。");
    } finally {
      setIsStartingSession(false);
    }
  };

  const generateQuestion = async (
    roundIndex: number,
    turnContext: DefenseTurn[] = turns,
  ): Promise<void> => {
    if (!activeSubject || !sessionId || !studentId) return;
    setDefenseError(null);
    setIsGeneratingQuestion(true);
    setCurrentQuestion("");
    setAnswerDraft("");
    try {
      const response = await fetch(`${API_BASE}/yandaojie/defense/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          round_index: roundIndex,
          subject_id: activeSubject.id,
          subject_label: activeSubject.label,
          subject_topic: activeSubject.topic,
          learning_objectives: activeSubject.learningObjectives,
          reflections: [{
            objective_index: 0,
            learned: reflectionLearned,
            questions: reflectionQuestions,
          }],
          previous_turns: turnContext.map((t) => ({
            round_index: t.roundIndex,
            question: t.question,
            answer_text: t.answerText,
            answered_at: t.answeredAt,
          })),
        }),
      });
      if (!response.ok) throw new Error("question generation failed");
      const data = (await response.json()) as QuestionResponse;
      setPersistenceEnabled(data.persistence_enabled);
      setCurrentRoundIndex(data.round_index);
      setCurrentQuestion(data.question);
      await postEvent("defense_question_generated", {
        round_index: data.round_index,
        model: data.model,
      });
    } catch (error) {
      console.error(error);
      setDefenseError("无法生成下一道保卫题目。");
    } finally {
      setIsGeneratingQuestion(false);
    }
  };

  const submitReflection = async (): Promise<void> => {
    if (!canSubmitReflection) {
      setDefenseError("请至少填写「你学到了什么」。");
      return;
    }
    setStage("defense");
    setCurrentRoundIndex(0);
    setTurns([]);
    await saveSnapshot("defense");
    await postEvent("reflection_submitted", {});
    await generateQuestion(0, []);
  };

  const handleAnswerChange = (event: ChangeEvent<HTMLTextAreaElement>): void => {
    setAnswerDraft(event.target.value);
  };

  const saveTurn = async (
    options: { allowEmptyAnswer?: boolean } = {},
  ): Promise<void> => {
    const answerText = answerDraft.trim();
    if (
      !activeSubject ||
      !currentQuestion ||
      isSavingTurn ||
      (!options.allowEmptyAnswer && !answerText)
    )
      return;

    const answeredAt = new Date().toISOString();
    setIsSavingTurn(true);
    setDefenseError(null);
    try {
      const response = await fetch(`${API_BASE}/yandaojie/defense/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          round_index: currentRoundIndex,
          subject_id: activeSubject.id,
          question: currentQuestion,
          answer_text: answerText,
          answered_at: answeredAt,
        }),
      });
      if (!response.ok) throw new Error("turn save failed");
      const data = (await response.json()) as TurnResponse;
      setPersistenceEnabled(data.persistence_enabled);
      const nextTurns: DefenseTurn[] = [
        ...turns,
        { roundIndex: currentRoundIndex, question: currentQuestion, answerText, answeredAt },
      ];
      setTurns(nextTurns);
      await postEvent("defense_turn_submitted", {
        round_index: currentRoundIndex,
        answer_length: answerText.length,
      });

      if (nextTurns.length >= DEFENSE_ROUNDS_PER_OBJECTIVE) {
        const finishedAt = new Date().toISOString();
        setCompletedAt(finishedAt);
        setStage("complete");
        setCurrentQuestion("");
        return;
      }
      await generateQuestion(currentRoundIndex + 1, nextTurns);
    } catch (error) {
      console.error(error);
      setDefenseError("无法保存你的回答。");
    } finally {
      setIsSavingTurn(false);
    }
  };

  if (!activeSubject) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#F6F1E8] px-4 text-[#171717]">
        <div className="rounded-[2rem] border border-[#E4D8C8] bg-white p-8 text-center shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
          <h1 className="text-2xl font-bold">链接无效</h1>
          <p className="mt-3 text-[#5F5D57]">
            请联系老师获取正确的知识保卫链接。
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#F6F1E8] px-4 py-8 text-[#171717] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="rounded-[2rem] border border-[#E4D8C8] bg-white px-6 py-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)] sm:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                知识保卫
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-[#5F5D57]">
                针对每个教学目标进行反思和知识保卫，每个目标五轮60秒。
              </p>
              <p className="mt-1 text-sm text-[#8A5E2A]">
                {activeSubject.label} · {activeSubject.topic} · 小学六年级 · 试点版本
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StepPill active={stage === "student-id"} complete={Boolean(studentId)} label="学号" />
              <StepPill
                active={stage === "reflection"}
                complete={stage === "defense" || stage === "complete"}
                label="反思"
              />
              <StepPill active={stage === "defense"} complete={stage === "complete"} label="知识保卫" />
              <StepPill active={stage === "complete"} complete={stage === "complete"} label="完成" />
            </div>
          </div>
          {studentId ? (
            <p className="mt-4 text-sm text-[#6B665E]">
              学号：<span className="font-semibold text-[#171717]">{studentId}</span>
              {persistenceEnabled === false ? (
                <span className="font-semibold text-[#B42318]">
                  {" "}· 数据暂无法保存
                </span>
              ) : isSavingSnapshot ? (
                " · 保存中..."
              ) : persistenceEnabled ? (
                " · 已自动保存"
              ) : (
                " · 检查保存状态..."
              )}
            </p>
          ) : null}
        </header>

        {stage === "student-id" ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <label className="text-sm font-semibold text-[#3A332A]" htmlFor="student-id">
              请输入你的学号
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                id="student-id"
                value={studentIdDraft}
                onChange={(e) => setStudentIdDraft(e.target.value)}
                className="min-h-12 flex-1 rounded-2xl border border-[#D8D2C7] bg-white px-4 text-base text-[#171717] outline-none placeholder:text-[#8A8178] focus:border-[#171717]"
                placeholder="请输入学号"
              />
              <PrimaryButton disabled={isStartingSession} onClick={() => void startSession()}>
                {isStartingSession ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                继续
              </PrimaryButton>
            </div>
            {sessionError ? <p className="mt-3 text-sm text-[#B42318]">{sessionError}</p> : null}
          </section>
        ) : null}

        {stage === "reflection" && activeSubject ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <h2 className="text-2xl font-bold">知识保卫前的反思</h2>
            <p className="mt-2 text-sm text-[#5F5D57]">
              教学目标 {currentObjectiveIndex + 1} / {activeSubject.learningObjectives.length}
            </p>

            <div className="mt-6">
              <div className="rounded-2xl border border-[#E4D8C8] bg-[#FDFBF7] p-5">
                <p className="text-sm font-semibold text-[#8A5E2A]">
                  教学目标 {currentObjectiveIndex + 1}
                </p>
                <p className="mt-1 text-sm leading-6 text-[#3A332A]">
                  {activeSubject.learningObjectives[currentObjectiveIndex]}
                </p>
                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <label className="block">
                    <span className="text-sm font-semibold">
                      你学到了什么？
                    </span>
                    <textarea
                      value={reflections[currentObjectiveIndex]?.learned ?? ""}
                      onChange={(e) => {
                        const next = [...reflections];
                        next[currentObjectiveIndex] = {
                          ...next[currentObjectiveIndex],
                          learned: e.target.value,
                        };
                        setReflections(next);
                      }}
                      className="mt-2 min-h-28 w-full rounded-2xl border border-[#D8D2C7] bg-white p-4 text-[#171717] outline-none placeholder:text-[#8A8178] focus:border-[#171717]"
                      placeholder="简要总结你对这个目标的理解..."
                    />
                  </label>
                  <label className="block">
                    <span className="text-sm font-semibold">
                      还有什么疑问？
                    </span>
                    <textarea
                      value={reflections[currentObjectiveIndex]?.questions ?? ""}
                      onChange={(e) => {
                        const next = [...reflections];
                        next[currentObjectiveIndex] = {
                          ...next[currentObjectiveIndex],
                          questions: e.target.value,
                        };
                        setReflections(next);
                      }}
                      className="mt-2 min-h-28 w-full rounded-2xl border border-[#D8D2C7] bg-white p-4 text-[#171717] outline-none placeholder:text-[#8A8178] focus:border-[#171717]"
                      placeholder="写下你仍然困惑的地方（选填）..."
                    />
                  </label>
                </div>
              </div>
            </div>

            {defenseError ? (
              <p className="mt-4 text-sm text-[#B42318]">{defenseError}</p>
            ) : null}
            <div className="mt-6 flex flex-wrap gap-3">
              {currentObjectiveIndex === 0 ? (
                <SecondaryButton onClick={() => setStage("student-id")}>
                  返回
                </SecondaryButton>
              ) : null}
              <PrimaryButton
                disabled={!canSubmitReflection || isGeneratingQuestion}
                onClick={() => void submitReflection()}
              >
                {isGeneratingQuestion ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <SendHorizonal className="h-4 w-4" />
                )}
                开始知识保卫
              </PrimaryButton>
            </div>
          </section>
        ) : null}

        {stage === "defense" && activeSubject ? (
          <section className="mt-6">
            <div className="rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-[#8A5E2A]">
                    教学目标 {currentObjectiveIndex + 1} · 第 {currentRoundIndex + 1} 轮 / 共 {DEFENSE_ROUNDS_PER_OBJECTIVE} 轮
                  </p>
                  <h2 className="mt-1 text-2xl font-bold">知识保卫题目</h2>
                </div>
                <div
                  className={cn(
                    "inline-flex items-center gap-3 rounded-3xl border-2 px-6 py-4 text-2xl font-bold tabular-nums shadow-[0_10px_28px_rgba(52,42,28,0.12)]",
                    secondsRemaining === 0
                      ? "border-[#E5483F] bg-[#FCEDEC] text-[#A43D36]"
                      : secondsRemaining <= 10
                        ? "border-[#D97706] bg-[#FFF4DE] text-[#92400E]"
                        : "border-[#171717] bg-[#171717] text-white",
                  )}
                >
                  <Timer className="h-6 w-6" />
                  {formatSeconds(secondsRemaining)}
                </div>
              </div>

              <div className="mt-6 rounded-3xl bg-[#F6F1E8] p-5">
                {isGeneratingQuestion ? (
                  <div className="flex items-center gap-3 text-[#5F5D57]">
                    <Loader2 className="h-5 w-5 animate-spin" />
                    正在生成知识保卫题目...
                  </div>
                ) : (
                  <p className="text-lg font-semibold leading-8">
                    {currentQuestion}
                  </p>
                )}
              </div>

              <label className="mt-6 block">
                <span className="text-sm font-semibold">你的回答</span>
                <textarea
                  value={answerDraft}
                  onChange={handleAnswerChange}
                  disabled={isRoundTimedOut || isGeneratingQuestion}
                  className="mt-2 min-h-40 w-full rounded-2xl border border-[#D8D2C7] bg-white p-4 text-[#171717] outline-none placeholder:text-[#8A8178] focus:border-[#171717] disabled:cursor-not-allowed disabled:bg-white disabled:text-[#171717]"
                  placeholder="在此输入你的回答..."
                />
              </label>

              {isRoundTimedOut ? (
                <p className="mt-2 text-sm leading-6 text-[#8A5E2A]" aria-live="polite">
                  {isSavingTurn || isGeneratingQuestion
                    ? "时间到！正在进入下一轮..."
                    : "时间到！自动进入下一轮。"}
                </p>
              ) : null}

              {defenseError ? (
                <p className="mt-4 text-sm text-[#B42318]">{defenseError}</p>
              ) : null}

              <div className="mt-6 flex flex-wrap justify-end gap-3">
                <PrimaryButton
                  disabled={!canSubmitTurn}
                  onClick={() => void saveTurn()}
                >
                  {isSavingTurn ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4" />
                  )}
                  提交本轮回答
                </PrimaryButton>
              </div>
            </div>
          </section>
        ) : null}

        {stage === "complete" && activeSubject ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <p className="text-sm font-semibold text-[#256C42]">已完成</p>
            <h2 className="mt-2 text-3xl font-bold">恭喜你！</h2>
            <p className="mt-3 text-[#5F5D57]">
              你已完成「{activeSubject.label} · {activeSubject.topic}」的知识保卫。
              {persistenceEnabled === false
                ? "但数据暂时无法保存。"
                : "你的答辩记录已保存。"}
            </p>
          </section>
        ) : null}
      </div>
    </main>
  );
}
