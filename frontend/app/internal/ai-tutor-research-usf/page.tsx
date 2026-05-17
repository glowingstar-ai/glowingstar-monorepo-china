import type { Metadata } from "next";

import UsfResearchDashboard from "@/components/usf-research-dashboard";

export const metadata: Metadata = {
  title: "USF Defense Research",
  description:
    "Internal dashboard for reviewing USF defense sessions, reflections, transcripts, ratings, and generated questions.",
};

export default function InternalUsfResearchPage(): JSX.Element {
  return <UsfResearchDashboard />;
}
