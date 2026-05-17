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

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const DEFENSE_ROUNDS = 5;
const ROUND_SECONDS = 60;

export type UsfModule = {
  id: string;
  moduleNumber: number;
  title: string;
  week: string;
  available: boolean;
  learningObjectives: string[];
  assessments: string[];
  notes?: string;
};

type UsfDefenseExperienceProps = {
  modules: UsfModule[];
};

type Stage = "student-id" | "module" | "reflection" | "defense" | "complete";

const requiresReflection = (moduleItem: UsfModule): boolean =>
  moduleItem.learningObjectives.length > 0;

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

export default function UsfDefenseExperience({
  modules,
}: Readonly<UsfDefenseExperienceProps>): JSX.Element {
  const [stage, setStage] = useState<Stage>("student-id");
  const [studentIdDraft, setStudentIdDraft] = useState("");
  const [studentId, setStudentId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [selectedModuleId, setSelectedModuleId] = useState("");
  const [learnedResponse, setLearnedResponse] = useState("");
  const [remainingQuestionsResponse, setRemainingQuestionsResponse] = useState("");
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
  const [persistenceEnabled, setPersistenceEnabled] = useState<boolean | null>(null);
  const answerDraftRef = useRef("");
  const timedOutRoundRef = useRef<string | null>(null);

  const selectedModule =
    modules.find((moduleItem) => moduleItem.id === selectedModuleId) ?? null;
  const trimmedStudentId = studentIdDraft.trim();
  const isRoundTimedOut =
    stage === "defense" && currentQuestion.length > 0 && secondsRemaining === 0;
  const canSubmitReflection =
    Boolean(selectedModule) &&
    learnedResponse.trim().length > 0 &&
    remainingQuestionsResponse.trim().length > 0;
  const canSubmitTurn =
    currentQuestion.length > 0 &&
    answerDraft.trim().length > 0 &&
    !isGeneratingQuestion &&
    !isSavingTurn;

  useEffect(() => {
    answerDraftRef.current = answerDraft;
  }, [answerDraft]);

  useEffect(() => {
    if (stage !== "defense" || !currentQuestion) {
      return;
    }

    setSecondsRemaining(ROUND_SECONDS);
    const interval = window.setInterval(() => {
      setSecondsRemaining((value) => {
        if (value <= 1) {
          window.clearInterval(interval);
          return 0;
        }

        return value - 1;
      });
    }, 1000);

    return () => window.clearInterval(interval);
  }, [currentQuestion, currentRoundIndex, stage]);

  useEffect(() => {
    if (!isRoundTimedOut) {
      return;
    }

    const roundKey = `${currentRoundIndex}:${currentQuestion}`;
    if (timedOutRoundRef.current === roundKey) {
      return;
    }

    timedOutRoundRef.current = roundKey;

    void saveTurn({
      allowEmptyAnswer: true,
      submitReason: "timer_expired",
    });
    // postEvent is intentionally omitted to keep this effect keyed
    // to the timeout moment for a single round.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [answerDraft, currentQuestion, currentRoundIndex, isRoundTimedOut]);

  useEffect(() => {
    if (!sessionId || !studentId) {
      return;
    }

    const timeout = window.setTimeout(() => {
      void saveSnapshot(stage);
    }, 400);

    return () => window.clearTimeout(timeout);
    // saveSnapshot is intentionally omitted to keep the debounce keyed to state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    completedAt,
    currentRoundIndex,
    learnedResponse,
    remainingQuestionsResponse,
    selectedModuleId,
    sessionId,
    stage,
    studentId,
    turns,
  ]);

  const postEvent = async (
    eventType: string,
    payload: Record<string, unknown> = {},
  ): Promise<void> => {
    if (!sessionId || !studentId) {
      return;
    }

    try {
      await fetch(`${API_BASE}/usf/session/event`, {
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
      console.error("Unable to persist USF event", error);
    }
  };

  const saveSnapshot = async (
    nextStage: Stage,
    moduleContext: UsfModule | null = selectedModule,
    overrides: {
      completedAt?: string | null;
      turnContext?: DefenseTurn[];
    } = {},
  ): Promise<void> => {
    if (!sessionId || !studentId) {
      return;
    }

    const snapshotTurns = overrides.turnContext ?? turns;
    const snapshotCompletedAt =
      Object.prototype.hasOwnProperty.call(overrides, "completedAt")
        ? overrides.completedAt
        : completedAt;

    setIsSavingSnapshot(true);
    try {
      const response = await fetch(`${API_BASE}/usf/session/snapshot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          stage: nextStage,
          module_id: moduleContext?.id ?? null,
          module_number: moduleContext?.moduleNumber ?? null,
          module_topic: moduleContext?.title ?? null,
          module_week: moduleContext?.week ?? null,
          learning_objectives: moduleContext?.learningObjectives ?? [],
          learned_response: learnedResponse,
          remaining_questions_response: remainingQuestionsResponse,
          current_round_index: currentRoundIndex,
          completed_round_count: snapshotTurns.length,
          defense_turns: snapshotTurns.map((turn) => ({
            round_index: turn.roundIndex,
            question: turn.question,
            answer_text: turn.answerText,
            audio_transcript: null,
            answered_at: turn.answeredAt,
          })),
          completed_at: snapshotCompletedAt,
        }),
      });

      if (!response.ok) {
        throw new Error("USF snapshot request failed");
      }

      const payload = (await response.json()) as SnapshotResponse;
      setPersistenceEnabled(payload.persistence_enabled);
    } catch (error) {
      console.error("Unable to persist USF snapshot", error);
    } finally {
      setIsSavingSnapshot(false);
    }
  };

  const startSession = async (): Promise<void> => {
    if (!trimmedStudentId) {
      setSessionError("Please enter your USF ID (U#).");
      return;
    }

    setSessionError(null);
    setIsStartingSession(true);
    try {
      const response = await fetch(`${API_BASE}/usf/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: trimmedStudentId }),
      });

      if (!response.ok) {
        throw new Error("Unable to start USF session");
      }

      const payload = (await response.json()) as SessionStartResponse;
      setPersistenceEnabled(payload.persistence_enabled);
      setStudentId(trimmedStudentId);
      setSessionId(payload.session_id);
      setStage("module");
    } catch (error) {
      console.error(error);
      setSessionError("We could not start your session. Please try again.");
    } finally {
      setIsStartingSession(false);
    }
  };

  const selectModule = async (moduleId: string): Promise<void> => {
    const moduleItem = modules.find((item) => item.id === moduleId);
    if (!moduleItem?.available) {
      return;
    }

    setSelectedModuleId(moduleId);
    await postEvent("module_selected", {
      module_id: moduleItem.id,
      module_number: moduleItem.moduleNumber,
      module_topic: moduleItem.title,
    });

    if (requiresReflection(moduleItem)) {
      setStage("reflection");
      return;
    }

    setStage("defense");
    await saveSnapshot("defense", moduleItem);
    await postEvent("reflection_skipped", {
      reason: "no_learning_objectives",
    });
    await generateQuestion(0, [], moduleItem);
  };

  const generateQuestion = async (
    roundIndex: number,
    turnContext: DefenseTurn[] = turns,
    moduleContext: UsfModule | null = selectedModule,
  ): Promise<void> => {
    if (!moduleContext || !sessionId || !studentId) {
      return;
    }

    setDefenseError(null);
    setIsGeneratingQuestion(true);
    setCurrentQuestion("");
    setAnswerDraft("");
    answerDraftRef.current = "";
    try {
      const response = await fetch(`${API_BASE}/usf/defense/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          round_index: roundIndex,
          module_id: moduleContext.id,
          module_number: moduleContext.moduleNumber,
          module_topic: moduleContext.title,
          module_week: moduleContext.week,
          learning_objectives: moduleContext.learningObjectives,
          learned_response: learnedResponse,
          remaining_questions_response: remainingQuestionsResponse,
          previous_turns: turnContext.map((turn) => ({
            round_index: turn.roundIndex,
            question: turn.question,
            answer_text: turn.answerText,
            audio_transcript: null,
            answered_at: turn.answeredAt,
          })),
        }),
      });

      if (!response.ok) {
        throw new Error("Defense question request failed");
      }

      const payload = (await response.json()) as QuestionResponse;
      setPersistenceEnabled(payload.persistence_enabled);
      setCurrentRoundIndex(payload.round_index);
      setCurrentQuestion(payload.question);
      await postEvent("defense_question_generated", {
        round_index: payload.round_index,
        model: payload.model,
      });
    } catch (error) {
      console.error(error);
      setDefenseError("We could not generate the next defense question.");
    } finally {
      setIsGeneratingQuestion(false);
    }
  };

  const submitReflection = async (): Promise<void> => {
    if (!canSubmitReflection) {
      setDefenseError("Please answer both reflection questions before continuing.");
      return;
    }

    setStage("defense");
    await saveSnapshot("defense");
    await postEvent("reflection_submitted", {
      learned_response_length: learnedResponse.trim().length,
      remaining_questions_response_length: remainingQuestionsResponse.trim().length,
    });
    await generateQuestion(0);
  };

  const handleAnswerChange = (event: ChangeEvent<HTMLTextAreaElement>): void => {
    setAnswerDraft(event.target.value);
  };

  const saveTurn = async (
    options: {
      allowEmptyAnswer?: boolean;
      answerTextOverride?: string;
      submitReason?: string;
    } = {},
  ): Promise<void> => {
    const answerText = options.answerTextOverride ?? answerDraft.trim();
    if (
      !selectedModule ||
      !currentQuestion ||
      isSavingTurn ||
      (!options.allowEmptyAnswer && !answerText.trim())
    ) {
      return;
    }

    const answeredAt = new Date().toISOString();
    setIsSavingTurn(true);
    setDefenseError(null);
    try {
      const response = await fetch(`${API_BASE}/usf/defense/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          student_id: studentId,
          round_index: currentRoundIndex,
          module_id: selectedModule.id,
          question: currentQuestion,
          answer_text: answerText.trim(),
          audio_transcript: null,
          answered_at: answeredAt,
        }),
      });

      if (!response.ok) {
        throw new Error("USF defense turn save failed");
      }

      const payload = (await response.json()) as TurnResponse;
      setPersistenceEnabled(payload.persistence_enabled);
      const nextTurns = [
        ...turns,
        {
          roundIndex: currentRoundIndex,
          question: currentQuestion,
          answerText: answerText.trim(),
          answeredAt,
        },
      ];
      setTurns(nextTurns);
      await postEvent("defense_turn_submitted", {
        round_index: currentRoundIndex,
        answer_length: answerText.trim().length,
        submit_reason: options.submitReason ?? "manual",
      });

      if (nextTurns.length >= DEFENSE_ROUNDS) {
        const finishedAt = new Date().toISOString();
        setCompletedAt(finishedAt);
        setStage("complete");
        setCurrentQuestion("");
        await saveSnapshot("complete", selectedModule, {
          completedAt: finishedAt,
          turnContext: nextTurns,
        });
        return;
      }

      await generateQuestion(currentRoundIndex + 1, nextTurns);
    } catch (error) {
      console.error(error);
      setDefenseError("We could not save your defense answer.");
    } finally {
      setIsSavingTurn(false);
    }
  };

  const returnToModules = async (): Promise<void> => {
    const currentStudentId = studentId;
    setSessionId("");
    setStage("module");
    setSelectedModuleId("");
    setLearnedResponse("");
    setRemainingQuestionsResponse("");
    setCurrentRoundIndex(0);
    setCurrentQuestion("");
    setAnswerDraft("");
    setTurns([]);
    setSecondsRemaining(ROUND_SECONDS);
    setDefenseError(null);
    setCompletedAt(null);
    setPersistenceEnabled(null);
    answerDraftRef.current = "";
    timedOutRoundRef.current = null;

    if (!currentStudentId) {
      setStage("student-id");
      return;
    }

    setIsStartingSession(true);
    try {
      const response = await fetch(`${API_BASE}/usf/session/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ student_id: currentStudentId }),
      });

      if (!response.ok) {
        throw new Error("Unable to start a new USF session");
      }

      const payload = (await response.json()) as SessionStartResponse;
      setPersistenceEnabled(payload.persistence_enabled);
      setSessionId(payload.session_id);
    } catch (error) {
      console.error(error);
      setStudentId("");
      setStudentIdDraft(currentStudentId);
      setStage("student-id");
      setSessionError("We could not start a new module attempt. Please try again.");
    } finally {
      setIsStartingSession(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#F6F1E8] px-4 py-8 text-[#171717] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="rounded-[2rem] border border-[#E4D8C8] bg-white px-6 py-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)] sm:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Defend what you learned
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-[#5F5D57]">
                Choose a course module, reflect on your learning, then complete five
                60-second live defense rounds with AI-generated follow-up questions.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StepPill active={stage === "student-id"} complete={Boolean(studentId)} label="ID" />
              <StepPill active={stage === "module"} complete={Boolean(selectedModule)} label="Module" />
              <StepPill
                active={stage === "reflection"}
                complete={
                  selectedModule
                    ? !requiresReflection(selectedModule) ||
                      (learnedResponse.trim().length > 0 && remainingQuestionsResponse.trim().length > 0)
                    : false
                }
                label="Reflection"
              />
              <StepPill active={stage === "defense"} complete={turns.length === DEFENSE_ROUNDS} label="Defense" />
              <StepPill active={stage === "complete"} complete={stage === "complete"} label="Complete" />
            </div>
          </div>
          {studentId ? (
            <p className="mt-4 text-sm text-[#6B665E]">
              USF ID (U#): <span className="font-semibold text-[#171717]">{studentId}</span>
              {persistenceEnabled === false ? (
                <span className="font-semibold text-[#B42318]">
                  {" "}
                  · Persistence unavailable - this session is not being saved
                </span>
              ) : isSavingSnapshot ? (
                " · Saving..."
              ) : persistenceEnabled ? (
                " · Saved as you work"
              ) : (
                " · Checking save status..."
              )}
            </p>
          ) : null}
        </header>

        {stage === "student-id" ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <label className="text-sm font-semibold text-[#3A332A]" htmlFor="student-id">
              Enter your USF ID (U#)
            </label>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row">
              <input
                id="student-id"
                value={studentIdDraft}
                onChange={(event) => setStudentIdDraft(event.target.value)}
                className="min-h-12 flex-1 rounded-2xl border border-[#D8D2C7] bg-white px-4 text-base text-[#171717] outline-none [color-scheme:light] placeholder:text-[#8A8178] focus:border-[#171717]"
                placeholder="USF ID (U#)"
              />
              <PrimaryButton disabled={isStartingSession} onClick={startSession}>
                {isStartingSession ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Continue
              </PrimaryButton>
            </div>
            {sessionError ? <p className="mt-3 text-sm text-[#B42318]">{sessionError}</p> : null}
          </section>
        ) : null}

        {stage === "module" ? (
          <section className="mt-6 grid gap-4 md:grid-cols-2">
            {modules.map((moduleItem) => (
              <button
                key={moduleItem.id}
                disabled={!moduleItem.available}
                onClick={() => void selectModule(moduleItem.id)}
                className={cn(
                  "rounded-[1.5rem] border bg-white p-5 text-left shadow-[0_10px_36px_rgba(52,42,28,0.06)] transition hover:-translate-y-0.5 hover:border-[#171717]",
                  moduleItem.available
                    ? "border-[#E4D8C8]"
                    : "cursor-not-allowed border-[#E6E0D5] opacity-60",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#8A5E2A]">
                      Module {moduleItem.moduleNumber}
                    </p>
                    <h2 className="mt-1 text-xl font-bold">{moduleItem.title}</h2>
                  </div>
                  {moduleItem.learningObjectives.length === 0 ? (
                    <span className="rounded-full bg-[#F4E8DE] px-3 py-1 text-xs font-semibold text-[#9B4A1B]">
                      No reflection needed
                    </span>
                  ) : null}
                </div>
                {moduleItem.learningObjectives.length > 0 ? (
                  <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-[#5F5D57]">
                    {moduleItem.learningObjectives.map((objective) => (
                      <li key={objective}>{objective}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-4 text-sm text-[#5F5D57]">
                    No written reflection is needed for this module.
                  </p>
                )}
              </button>
            ))}
          </section>
        ) : null}

        {stage === "reflection" && selectedModule ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <p className="text-sm font-semibold text-[#8A5E2A]">
              Module {selectedModule.moduleNumber}: {selectedModule.title}
            </p>
            <h2 className="mt-2 text-2xl font-bold">Before the defense</h2>
            <div className="mt-5 grid gap-5 lg:grid-cols-2">
              <label className="block">
                <span className="text-sm font-semibold">What have you learned in this module?</span>
                <textarea
                  value={learnedResponse}
                  onChange={(event) => setLearnedResponse(event.target.value)}
                  className="mt-2 min-h-44 w-full rounded-2xl border border-[#D8D2C7] bg-white p-4 text-[#171717] outline-none [color-scheme:light] placeholder:text-[#8A8178] focus:border-[#171717]"
                  placeholder="Summarize concepts, examples, or arguments you understand now."
                />
              </label>
              <label className="block">
                <span className="text-sm font-semibold">What remaining questions do you have?</span>
                <textarea
                  value={remainingQuestionsResponse}
                  onChange={(event) => setRemainingQuestionsResponse(event.target.value)}
                  className="mt-2 min-h-44 w-full rounded-2xl border border-[#D8D2C7] bg-white p-4 text-[#171717] outline-none [color-scheme:light] placeholder:text-[#8A8178] focus:border-[#171717]"
                  placeholder="Name the uncertainties, weak points, or areas you want to test."
                />
              </label>
            </div>
            {defenseError ? <p className="mt-4 text-sm text-[#B42318]">{defenseError}</p> : null}
            <div className="mt-6 flex flex-wrap gap-3">
              <SecondaryButton onClick={() => setStage("module")}>Back</SecondaryButton>
              <PrimaryButton disabled={!canSubmitReflection || isGeneratingQuestion} onClick={() => void submitReflection()}>
                {isGeneratingQuestion ? <Loader2 className="h-4 w-4 animate-spin" /> : <SendHorizonal className="h-4 w-4" />}
                Start defense
              </PrimaryButton>
            </div>
          </section>
        ) : null}

        {stage === "defense" && selectedModule ? (
          <section className="mt-6">
            <div className="rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-[#8A5E2A]">
                    Round {currentRoundIndex + 1} of {DEFENSE_ROUNDS}
                  </p>
                  <h2 className="mt-1 text-2xl font-bold">Live defense question</h2>
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
                    Generating a defense question...
                  </div>
                ) : (
                  <p className="text-lg font-semibold leading-8">{currentQuestion}</p>
                )}
              </div>

              <label className="mt-6 block">
                <span className="text-sm font-semibold">Your defense answer</span>
                <textarea
                  value={answerDraft}
                  onChange={handleAnswerChange}
                  disabled={isRoundTimedOut || isGeneratingQuestion}
                  className="mt-2 min-h-40 w-full rounded-2xl border border-[#D8D2C7] bg-white p-4 text-[#171717] outline-none [color-scheme:light] placeholder:text-[#8A8178] focus:border-[#171717] disabled:cursor-not-allowed disabled:bg-white disabled:text-[#171717]"
                  placeholder="Type your defense here."
                />
              </label>

              <div className="mt-6">
                {isRoundTimedOut ? (
                  <p className="mt-2 text-sm leading-6 text-[#8A5E2A]" aria-live="polite">
                    {isSavingTurn || isGeneratingQuestion
                      ? "Time is up. Moving to the next round..."
                      : "Time is up. Moving to the next round automatically."}
                  </p>
                ) : null}
              </div>

              {defenseError ? <p className="mt-4 text-sm text-[#B42318]">{defenseError}</p> : null}

              <div className="mt-6 flex flex-wrap justify-end gap-3">
                <PrimaryButton disabled={!canSubmitTurn} onClick={() => void saveTurn()}>
                  {isSavingTurn ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  Submit round now
                </PrimaryButton>
              </div>
            </div>
          </section>
        ) : null}

        {stage === "complete" && selectedModule ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <p className="text-sm font-semibold text-[#256C42]">Complete</p>
            <h2 className="mt-2 text-3xl font-bold">Congratulations!</h2>
            <p className="mt-3 text-[#5F5D57]">
              {persistenceEnabled === false
                ? `Your five defense rounds for Module ${selectedModule.moduleNumber}: ${selectedModule.title} are complete, but persistence is unavailable so they were not saved.`
                : `Your five defense rounds for Module ${selectedModule.moduleNumber}: ${selectedModule.title} have been saved.`}
              {" "}You can return to the module list to complete another module.
            </p>
            <div className="mt-6">
              <PrimaryButton onClick={returnToModules}>
                Back to modules
              </PrimaryButton>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
