import type { Metadata } from "next";
import YandaojieTeacherLinkBuilder from "@/components/yandaojie-teacher-link-builder";
import yandaojieSubjects from "@/data/yandaojie/subjects.json";

export const metadata: Metadata = {
  title: "研道街 · 教师端",
  description: "教师选择科目后，生成可分享给学生的知识保卫链接。",
};

export default function YandaojieTeacherPage(): JSX.Element {
  return <YandaojieTeacherLinkBuilder subjects={yandaojieSubjects} />;
}
