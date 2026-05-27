import type { Metadata } from "next";

import YandaojieResearchDashboard from "@/components/yandaojie-research-dashboard";

export const metadata: Metadata = {
  title: "研道街 知识保卫 Research",
  description:
    "Internal dashboard for reviewing Yandaojie defense sessions, reflections, and generated questions.",
};

export default function InternalYandaojieResearchPage(): JSX.Element {
  return <YandaojieResearchDashboard />;
}
