import type { Metadata } from "next";
import YandaojieDefenseExperience from "@/components/yandaojie-defense-experience";
import yandaojieSubjects from "@/data/yandaojie/subjects.json";
import { normalizeYandaojieSearchParams } from "@/lib/yandaojie";

export const metadata: Metadata = {
  title: "研道街 · 知识保卫",
  description: "学生知识保卫流程页面，包含反思与五轮答辩。",
};

type PageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default function YandaojieStudentPage({
  searchParams,
}: Readonly<PageProps>): JSX.Element {
  const selection = normalizeYandaojieSearchParams(searchParams);
  const selectedSubject =
    yandaojieSubjects.find((s) => s.id === selection.subject) ?? null;

  return (
    <YandaojieDefenseExperience
      subject={selectedSubject}
      subjects={yandaojieSubjects}
    />
  );
}
