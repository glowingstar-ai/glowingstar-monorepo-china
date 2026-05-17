import type { Metadata } from "next";
import UsfDefenseExperience from "@/components/usf-defense-experience";
import usfModules from "@/data/usf/modules.json";

export const metadata: Metadata = {
  title: {
    absolute: "USF Defense",
  },
  description: "A five-round learning-objective defense workflow for USF students.",
};

export default function UsfDefensePage(): JSX.Element {
  return <UsfDefenseExperience modules={usfModules} />;
}
