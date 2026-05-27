export type YandaojieSubject = {
  id: string;
  label: string;
  topic: string;
  learningObjectives: string[];
};

export type YandaojieSelection = {
  subject?: string;
};

export function normalizeFirstValue(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

export function normalizeYandaojieSearchParams(
  searchParams: Record<string, string | string[] | undefined> | undefined,
): YandaojieSelection {
  return {
    subject: normalizeFirstValue(searchParams?.subject),
  };
}

export function buildYandaojieStudentUrl(subject: string): string {
  const params = new URLSearchParams();
  params.set("subject", subject);
  return `/yandaojie/student?${params.toString()}`;
}
