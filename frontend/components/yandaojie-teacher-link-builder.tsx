"use client";

import { Check, Copy, Link2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { YandaojieSubject } from "@/lib/yandaojie";

type Props = {
  subjects: YandaojieSubject[];
};

export default function YandaojieTeacherLinkBuilder({
  subjects,
}: Readonly<Props>): JSX.Element {
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const [copied, setCopied] = useState(false);

  const selectedSubject = subjects.find((s) => s.id === selectedSubjectId);

  const studentUrl = selectedSubjectId
    ? `${typeof window !== "undefined" ? window.location.origin : ""}/yandaojie/student?subject=${selectedSubjectId}`
    : "";

  const handleCopy = async (): Promise<void> => {
    if (!studentUrl) return;
    try {
      await navigator.clipboard.writeText(studentUrl);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = studentUrl;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen bg-[#F6F1E8] px-4 py-8 text-[#171717] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="rounded-[2rem] border border-[#E4D8C8] bg-white px-6 py-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)] sm:px-8">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            知识保卫 · 教师端
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-[#5F5D57]">
            选择科目后，将生成的链接发送给学生。学生打开链接后输入学号，完成反思并进行五轮知识保卫答辩。
          </p>
          <div className="mt-2 flex flex-wrap gap-2 text-sm text-[#8A5E2A]">
            <span className="rounded-full bg-[#F4E8DE] px-3 py-1 font-medium">
              版本：试点
            </span>
            <span className="rounded-full bg-[#F4E8DE] px-3 py-1 font-medium">
              年级：小学六年级
            </span>
            <span className="rounded-full bg-[#F4E8DE] px-3 py-1 font-medium">
              模式：知识保卫
            </span>
          </div>
        </header>

        <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
          <h2 className="text-xl font-bold">选择科目</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {subjects.map((subject) => (
              <button
                key={subject.id}
                onClick={() => setSelectedSubjectId(subject.id)}
                className={cn(
                  "rounded-2xl border p-5 text-left transition hover:-translate-y-0.5",
                  selectedSubjectId === subject.id
                    ? "border-[#171717] bg-[#171717] text-white shadow-lg"
                    : "border-[#E4D8C8] bg-white hover:border-[#171717]",
                )}
              >
                <p className="text-lg font-bold">{subject.label}</p>
                <p
                  className={cn(
                    "mt-1 text-sm",
                    selectedSubjectId === subject.id
                      ? "text-white/70"
                      : "text-[#8A5E2A]",
                  )}
                >
                  {subject.topic}
                </p>
              </button>
            ))}
          </div>
        </section>

        {selectedSubject ? (
          <section className="mt-6 rounded-[2rem] border border-[#E4D8C8] bg-white p-6 shadow-[0_18px_60px_rgba(52,42,28,0.08)]">
            <h2 className="text-xl font-bold">教学目标</h2>
            <p className="mt-1 text-sm font-semibold text-[#8A5E2A]">
              {selectedSubject.label} · {selectedSubject.topic}
            </p>
            <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-[#5F5D57]">
              {selectedSubject.learningObjectives.map((obj) => (
                <li key={obj}>{obj}</li>
              ))}
            </ul>

            <div className="mt-6">
              <h3 className="text-sm font-semibold text-[#3A332A]">
                学生链接
              </h3>
              <div className="mt-2 flex items-center gap-2">
                <div className="flex min-h-12 flex-1 items-center rounded-2xl border border-[#D8D2C7] bg-[#F6F1E8] px-4">
                  <Link2 className="mr-2 h-4 w-4 shrink-0 text-[#8A8178]" />
                  <span className="truncate text-sm text-[#5F5D57]">
                    {studentUrl}
                  </span>
                </div>
                <button
                  onClick={() => void handleCopy()}
                  className="inline-flex min-h-12 items-center gap-2 rounded-2xl bg-[#171717] px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#2A2A2A]"
                >
                  {copied ? (
                    <Check className="h-4 w-4" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  {copied ? "已复制" : "复制链接"}
                </button>
              </div>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
