"use client";

import { AlertTriangle } from "@/components/Icons";
import { BlockKey, ProfileData, ResumeLanguage, TemplateId } from "@/lib/types";

interface ResumePreviewProps {
  data: ProfileData;
  templateId: TemplateId;
  language: ResumeLanguage;
  blockOrder: BlockKey[];
  estimatedPages?: number;
  pageWarning?: boolean;
}

const LABELS: Record<
  ResumeLanguage,
  {
    summary: string;
    experience: string;
    education: string;
    skills: string;
    languages: string;
    links: string;
    present: string;
    salary: string;
    format: string;
  }
> = {
  uk: {
    summary: "Про себе",
    experience: "Досвід роботи",
    education: "Освіта",
    skills: "Навички",
    languages: "Мови",
    links: "Посилання",
    present: "дотепер",
    salary: "Бажана зарплата",
    format: "Формат роботи",
  },
  en: {
    summary: "Summary",
    experience: "Experience",
    education: "Education",
    skills: "Skills",
    languages: "Languages",
    links: "Links",
    present: "Present",
    salary: "Desired salary",
    format: "Work format",
  },
};

export function estimatePagesClient(data: ProfileData): { pages: number; warning: boolean } {
  let chars = (data.summary || "").length + (data.target_role || "").length;
  for (const exp of data.experiences) {
    chars += exp.company.length + exp.position.length + exp.bullets.reduce((a, b) => a + b.length, 0) + 60;
  }
  for (const edu of data.education) {
    chars += edu.institution.length + edu.degree.length + edu.field_of_study.length + 50;
  }
  chars += data.skills.reduce((a, s) => a + s.length + 4, 0);
  chars += data.languages.length * 25 + data.links.length * 40;

  const lines = data.experiences.length * 3 + data.education.length * 2 + Math.floor(chars / 75);
  const pages =
    lines <= 42 && chars <= 2600
      ? 1
      : lines <= 84 && chars <= 5200
        ? 2
        : Math.max(3, Math.floor(chars / 2500) + 1);
  return { pages, warning: pages > 2 };
}

export function ResumePreview({
  data,
  templateId,
  language,
  blockOrder,
  estimatedPages,
  pageWarning,
}: ResumePreviewProps) {
  const labels = LABELS[language] || LABELS.uk;
  const computed = estimatePagesClient(data);
  const pages = estimatedPages ?? computed.pages;
  const showWarning = pageWarning ?? computed.warning;

  const fullName =
    data.contacts.full_name.trim() ||
    `${data.contacts.first_name} ${data.contacts.last_name}`.trim() ||
    (language === "uk" ? "Ваше Ім'я Прізвище" : "Your Full Name");

  const contactItems = [
    data.contacts.email.trim(),
    data.contacts.phone.trim(),
    data.contacts.location.trim(),
    data.work_format.trim() ? `${labels.format}: ${data.work_format.trim()}` : "",
    data.desired_salary.trim() ? `${labels.salary}: ${data.desired_salary.trim()}` : "",
  ].filter(Boolean);

  const isClassic = templateId === "classic";
  const isIT = templateId === "it";

  const headingCls = isIT
    ? "border-b border-blue-100 pb-0.5 text-xs font-bold uppercase tracking-wider text-blue-700"
    : isClassic
      ? "border-b border-slate-300 pb-0.5 text-xs font-bold uppercase tracking-wider text-slate-900"
      : "border-b border-zinc-200 pb-0.5 text-xs font-bold uppercase tracking-wider text-zinc-900";

  const formatRange = (start: string, end: string, isCurrent: boolean) => {
    const s = start.trim();
    const e = isCurrent ? labels.present : end.trim();
    if (s && e) return `${s} — ${e}`;
    return s || e;
  };

  const renderSection = (key: BlockKey) => {
    if (key === "summary" && data.summary.trim()) {
      return (
        <section key={key} className="mt-4">
          <h2 className={headingCls}>{labels.summary}</h2>
          <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-zinc-800">{data.summary}</p>
        </section>
      );
    }

    if (key === "experience" && data.experiences.length > 0) {
      return (
        <section key={key} className="mt-4">
          <h2 className={headingCls}>{labels.experience}</h2>
          <div className="mt-1.5 space-y-3">
            {data.experiences.map((exp, idx) => (
              <article key={exp.id || idx}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="text-sm font-semibold text-zinc-900">
                    {exp.position || "Посада"}
                    {exp.company ? <span className="font-normal text-zinc-700"> · {exp.company}</span> : null}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {formatRange(exp.start_date, exp.end_date, exp.is_current)}
                  </div>
                </div>
                {exp.bullets.filter((b) => b.trim()).length > 0 && (
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-zinc-800">
                    {exp.bullets
                      .filter((b) => b.trim())
                      .map((b, bi) => (
                        <li key={bi}>{b}</li>
                      ))}
                  </ul>
                )}
              </article>
            ))}
          </div>
        </section>
      );
    }

    if (key === "education" && data.education.length > 0) {
      return (
        <section key={key} className="mt-4">
          <h2 className={headingCls}>{labels.education}</h2>
          <div className="mt-1.5 space-y-2">
            {data.education.map((edu, idx) => (
              <article key={edu.id || idx}>
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div className="text-sm font-semibold text-zinc-900">{edu.institution || "Навчальний заклад"}</div>
                  <div className="text-xs text-zinc-500">
                    {formatRange(edu.start_date, edu.end_date, edu.is_current)}
                  </div>
                </div>
                {(edu.degree || edu.field_of_study) && (
                  <p className="text-xs text-zinc-600">
                    {[edu.degree, edu.field_of_study].filter(Boolean).join(" — ")}
                  </p>
                )}
              </article>
            ))}
          </div>
        </section>
      );
    }

    if (key === "skills" && data.skills.filter((s) => s.trim()).length > 0) {
      return (
        <section key={key} className="mt-4">
          <h2 className={headingCls}>{labels.skills}</h2>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {data.skills
              .filter((s) => s.trim())
              .map((skill, idx) => (
                <span
                  key={idx}
                  className={
                    isIT
                      ? "rounded border border-blue-200 bg-blue-50 px-2 py-0.5 font-mono text-xs text-blue-900"
                      : isClassic
                        ? "text-xs text-zinc-800 after:ml-1.5 after:text-zinc-400 after:content-['•'] last:after:content-none"
                        : "rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-800"
                  }
                >
                  {skill}
                </span>
              ))}
          </div>
        </section>
      );
    }

    if (key === "languages" && data.languages.filter((l) => l.name.trim()).length > 0) {
      return (
        <section key={key} className="mt-4">
          <h2 className={headingCls}>{labels.languages}</h2>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-zinc-800">
            {data.languages
              .filter((l) => l.name.trim())
              .map((l, idx) => (
                <span key={idx}>
                  <strong>{l.name}</strong>
                  {l.level ? ` — ${l.level}` : ""}
                </span>
              ))}
          </div>
        </section>
      );
    }

    if (key === "links" && data.links.filter((l) => l.url.trim()).length > 0) {
      return (
        <section key={key} className="mt-4">
          <h2 className={headingCls}>{labels.links}</h2>
          <ul className="mt-1 space-y-0.5 text-xs text-zinc-700">
            {data.links
              .filter((l) => l.url.trim())
              .map((lnk, idx) => (
                <li key={idx} className="break-all">
                  <strong>{lnk.label || "Link"}:</strong> {lnk.url}
                </li>
              ))}
          </ul>
        </section>
      );
    }

    return null;
  };

  return (
    <div className="space-y-3">
      {showWarning && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
          <span>
            Орієнтовна довжина резюме — <strong>{pages} стор.</strong> Рекомендуємо скоротити текст до 1–2 сторінок для
            кращого проходження ATS і зручності рекрутера.
          </span>
        </div>
      )}

      <div
        className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 ${
          isClassic ? "font-serif" : "font-sans"
        }`}
      >
        <header
          className={
            isClassic
              ? "border-b-2 border-slate-800 pb-3 text-center"
              : isIT
                ? "border-l-4 border-blue-600 pb-1 pl-3"
                : "border-b border-zinc-200 pb-3"
          }
        >
          <h1 className="text-2xl font-bold text-zinc-950">{fullName}</h1>
          {data.target_role.trim() && (
            <div
              className={`mt-0.5 text-sm ${
                isIT ? "font-semibold text-blue-600" : isClassic ? "italic text-slate-700" : "font-medium text-zinc-700"
              }`}
            >
              {data.target_role}
            </div>
          )}
          {contactItems.length > 0 && (
            <div
              className={`mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-zinc-600 ${
                isClassic ? "justify-center" : ""
              }`}
            >
              {contactItems.map((item, idx) => (
                <span key={idx}>{item}</span>
              ))}
            </div>
          )}
        </header>

        <main>{blockOrder.map((blockKey) => renderSection(blockKey))}</main>
      </div>
    </div>
  );
}
