"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUp,
  Download,
  Eye,
  FileDown,
  PenLine,
  Plus,
  RefreshCw,
  Save,
  Sparkles,
  Trash2,
} from "@/components/Icons";
import { api } from "@/lib/api";
import {
  AIQuotaInfo,
  BLOCK_LABELS_UK,
  BlockKey,
  DEFAULT_BLOCK_ORDER,
  DEMO_PROFILE_DATA,
  EMPTY_PROFILE_DATA,
  ProfileData,
  ResumeLanguage,
  TemplateId,
} from "@/lib/types";
import { validateProfileData } from "@/lib/validation";
import { AiSuggestionPanel } from "./AiSuggestionPanel";
import { ResumePreview } from "./ResumePreview";

interface ResumeEditorWorkspaceProps {
  demoMode?: boolean;
}

interface PendingSuggestion {
  title: string;
  variants: string[];
  disclaimer: string;
  apply: (chosen: string) => void;
}

export function ResumeEditorWorkspace({ demoMode = false }: ResumeEditorWorkspaceProps) {
  const [title, setTitle] = useState("Моє резюме");
  const [templateId, setTemplateId] = useState<TemplateId>("minimal");
  const [language, setLanguage] = useState<ResumeLanguage>("uk");
  const [blockOrder, setBlockOrder] = useState<BlockKey[]>(DEFAULT_BLOCK_ORDER);
  const [data, setData] = useState<ProfileData>(demoMode ? DEMO_PROFILE_DATA : EMPTY_PROFILE_DATA);
  const [loading, setLoading] = useState(!demoMode);
  const [saveStatus, setSaveStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [quota, setQuota] = useState<AIQuotaInfo | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [pendingAi, setPendingAi] = useState<PendingSuggestion | null>(null);
  const [exporting, setExporting] = useState<"pdf" | "docx" | null>(null);
  const [mobileTab, setMobileTab] = useState<"edit" | "preview">("edit");
  const [skillInput, setSkillInput] = useState("");
  const [editInstruction, setEditInstruction] = useState("Зроби формулювання чіткішим і професійнішим");

  const hydratedRef = useRef(false);
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (demoMode) {
      hydratedRef.current = true;
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const [resumeRes, quotaRes] = await Promise.all([api.getResume(), api.getAiQuota()]);
        if (cancelled) return;
        setTitle(resumeRes.title);
        setTemplateId(resumeRes.template_id);
        setLanguage(resumeRes.language);
        setBlockOrder(resumeRes.block_order);
        setData(resumeRes.data);
        setQuota(quotaRes);
        hydratedRef.current = true;
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Не вдалося завантажити резюме");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [demoMode]);

  const performSave = async (
    nextTitle = title,
    nextTpl = templateId,
    nextLang = language,
    nextOrder = blockOrder,
    nextData = data
  ) => {
    if (demoMode) return;
    const validationErrors = validateProfileData(nextData);
    if (validationErrors.length > 0) {
      setError(validationErrors[0]);
      return;
    }
    setError("");
    setSaveStatus("Збереження...");
    try {
      await api.updateResume({
        title: nextTitle,
        template_id: nextTpl,
        language: nextLang,
        block_order: nextOrder,
        data: nextData,
      });
      setSaveStatus("Автозбережено");
    } catch (err) {
      setSaveStatus("");
      setError(err instanceof Error ? err.message : "Помилка збереження");
    }
  };

  useEffect(() => {
    if (demoMode || !hydratedRef.current) return;
    if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    autosaveTimerRef.current = setTimeout(() => {
      void performSave(title, templateId, language, blockOrder, data);
    }, 900);
    return () => {
      if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, templateId, language, blockOrder, data]);

  const moveBlock = (idx: number, dir: -1 | 1) => {
    const target = idx + dir;
    if (target < 0 || target >= blockOrder.length) return;
    const copy = [...blockOrder];
    [copy[idx], copy[target]] = [copy[target], copy[idx]];
    setBlockOrder(copy);
  };

  const handleSyncProfile = async () => {
    if (demoMode) return;
    setError("");
    try {
      const synced = await api.syncResumeFromProfile();
      setData(synced.data);
      setSaveStatus("Дані підтягнуто з профілю");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не вдалося синхронізувати профіль");
    }
  };

  const handleAiGenerateSummary = async () => {
    if (demoMode) {
      setError("AI-помічник доступний після входу або реєстрації.");
      return;
    }
    setError("");
    setAiLoading(true);
    try {
      const res = await api.generateSummary({
        target_role: data.target_role,
        experiences_summary: data.experiences.map((e) => `${e.position} (${e.company})`),
        skills: data.skills,
        languages: data.languages.map((l) => `${l.name} ${l.level}`),
        language,
      });
      setQuota(res.quota);
      setPendingAi({
        title: "Варіанти блоку «Про себе» від AI",
        variants: res.variants,
        disclaimer: res.disclaimer,
        apply: (chosen) => {
          setData((prev) => ({ ...prev, summary: chosen }));
          setPendingAi(null);
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI недоступний, спробуйте через хвилину");
    } finally {
      setAiLoading(false);
    }
  };

  const handleAiImproveBullet = async (expIdx: number, bulletIdx: number) => {
    if (demoMode) {
      setError("AI-помічник доступний після входу або реєстрації.");
      return;
    }
    const exp = data.experiences[expIdx];
    const bullet = exp?.bullets[bulletIdx] || "";
    if (bullet.trim().length < 3) {
      setError("Спочатку введіть короткий опис досягнення (мінімум 3 символи).");
      return;
    }
    setError("");
    setAiLoading(true);
    try {
      const res = await api.improveBullet({
        bullet,
        role_title: exp.position,
        company: exp.company,
        skills: data.skills,
        language,
      });
      setQuota(res.quota);
      setPendingAi({
        title: "Покращення пункту досвіду (дія + результат + цифра)",
        variants: res.variants,
        disclaimer: res.disclaimer,
        apply: (chosen) => {
          setData((prev) => {
            const nextExp = [...prev.experiences];
            const bullets = [...nextExp[expIdx].bullets];
            bullets[bulletIdx] = chosen;
            nextExp[expIdx] = { ...nextExp[expIdx], bullets };
            return { ...prev, experiences: nextExp };
          });
          setPendingAi(null);
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI недоступний, спробуйте через хвилину");
    } finally {
      setAiLoading(false);
    }
  };

  const handleAiEditSummary = async () => {
    if (demoMode) {
      setError("AI-помічник доступний після входу або реєстрації.");
      return;
    }
    if (data.summary.trim().length < 3) {
      setError("Додайте текст у блок «Про себе», щоб AI запропонував правку.");
      return;
    }
    setError("");
    setAiLoading(true);
    try {
      const res = await api.editSelectedText({
        selected_text: data.summary,
        instruction: editInstruction,
        language,
      });
      setQuota(res.quota);
      setPendingAi({
        title: "Запропонована правка тексту «Про себе»",
        variants: res.variants,
        disclaimer: res.disclaimer,
        apply: (chosen) => {
          setData((prev) => ({ ...prev, summary: chosen }));
          setPendingAi(null);
        },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI недоступний, спробуйте через хвилину");
    } finally {
      setAiLoading(false);
    }
  };

  const handleExport = async (format: "pdf" | "docx") => {
    if (demoMode) {
      setError("Експорт у PDF і DOCX доступний після безкоштовної реєстрації.");
      return;
    }
    setError("");
    setExporting(format);
    try {
      const filename = await api.downloadResumeFile({
        format,
        template_id: templateId,
        language,
        block_order: blockOrder,
        data,
      });
      setSaveStatus(`Завантажено: ${filename}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка експорту");
    } finally {
      setExporting(null);
    }
  };

  const addSkill = () => {
    const trimmed = skillInput.trim();
    if (!trimmed) return;
    if (data.skills.length >= 30) {
      setError("Максимум 30 навичок.");
      return;
    }
    setData((prev) => ({ ...prev, skills: [...prev.skills, trimmed] }));
    setSkillInput("");
  };

  if (loading) {
    return <div className="py-16 text-center text-sm text-slate-500">Завантаження редактора резюме...</div>;
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {demoMode && (
        <div className="mb-4 flex flex-col items-start justify-between gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 sm:flex-row sm:items-center">
          <div>
            <strong>Демо-редактор (без збереження):</strong> ви можете протестувати форму, шаблони та перегляд.
          </div>
          <Link
            href="/register"
            className="shrink-0 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
          >
            Зареєструватися і зберегти
          </Link>
        </div>
      )}

      {/* Top Toolbar */}
      <div className="mb-5 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 rounded-lg bg-slate-100 p-1">
            {(
              [
                ["minimal", "Мінімальний"],
                ["classic", "Класичний"],
                ["it", "IT"],
              ] as [TemplateId, string][]
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setTemplateId(id)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                  templateId === id ? "bg-white text-blue-700 shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as ResumeLanguage)}
            className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700"
            aria-label="Мова резюме"
          >
            <option value="uk">Мова резюме: Українська</option>
            <option value="en">Мова резюме: English</option>
          </select>

          {!demoMode && quota && (
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-800">
              AI ліміт: {quota.remaining_today}/{quota.daily_limit} на добу
            </span>
          )}
          {saveStatus && <span className="text-xs text-emerald-700">{saveStatus}</span>}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!demoMode && (
            <>
              <button
                type="button"
                onClick={handleSyncProfile}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                З профілю
              </button>
              <button
                type="button"
                onClick={() => void performSave()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Save className="h-3.5 w-3.5" />
                Зберегти
              </button>
            </>
          )}
          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => void handleExport("pdf")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
          >
            <FileDown className="h-3.5 w-3.5" />
            {exporting === "pdf" ? "Генерація PDF..." : "Завантажити PDF"}
          </button>
          <button
            type="button"
            disabled={exporting !== null}
            onClick={() => void handleExport("docx")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-blue-600 px-3.5 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50 disabled:opacity-60"
          >
            <Download className="h-3.5 w-3.5" />
            {exporting === "docx" ? "Генерація DOCX..." : "Завантажити DOCX"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      )}

      {/* Mobile switch */}
      <div className="mb-4 flex gap-2 lg:hidden">
        <button
          type="button"
          onClick={() => setMobileTab("edit")}
          className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium ${
            mobileTab === "edit" ? "bg-blue-600 text-white" : "border border-slate-200 bg-white text-slate-700"
          }`}
        >
          <PenLine className="h-4 w-4" />
          Форма
        </button>
        <button
          type="button"
          onClick={() => setMobileTab("preview")}
          className={`inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-medium ${
            mobileTab === "preview" ? "bg-blue-600 text-white" : "border border-slate-200 bg-white text-slate-700"
          }`}
        >
          <Eye className="h-4 w-4" />
          Попередній перегляд
        </button>
      </div>

      {/* Main Split View */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Left: Form */}
        <div className={`space-y-5 lg:col-span-6 ${mobileTab === "preview" ? "hidden lg:block" : ""}`}>
          {pendingAi && (
            <AiSuggestionPanel
              title={pendingAi.title}
              variants={pendingAi.variants}
              disclaimer={pendingAi.disclaimer}
              onAccept={pendingAi.apply}
              onReject={() => setPendingAi(null)}
            />
          )}

          {/* Contacts & Target Role */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">Контакти та ціль</h2>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <input
                type="text"
                placeholder="Ім'я"
                value={data.contacts.first_name}
                onChange={(e) => {
                  const first_name = e.target.value;
                  setData((prev) => ({
                    ...prev,
                    contacts: {
                      ...prev.contacts,
                      first_name,
                      full_name: `${first_name} ${prev.contacts.last_name}`.trim(),
                    },
                  }));
                }}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                placeholder="Прізвище"
                value={data.contacts.last_name}
                onChange={(e) => {
                  const last_name = e.target.value;
                  setData((prev) => ({
                    ...prev,
                    contacts: {
                      ...prev.contacts,
                      last_name,
                      full_name: `${prev.contacts.first_name} ${last_name}`.trim(),
                    },
                  }));
                }}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="email"
                placeholder="Email"
                value={data.contacts.email}
                onChange={(e) =>
                  setData((prev) => ({ ...prev, contacts: { ...prev.contacts, email: e.target.value } }))
                }
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                placeholder="Телефон (+380...)"
                value={data.contacts.phone}
                onChange={(e) =>
                  setData((prev) => ({ ...prev, contacts: { ...prev.contacts, phone: e.target.value } }))
                }
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                placeholder="Місто / Локація"
                value={data.contacts.location}
                onChange={(e) =>
                  setData((prev) => ({ ...prev, contacts: { ...prev.contacts, location: e.target.value } }))
                }
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                type="text"
                placeholder="Бажана посада"
                value={data.target_role}
                onChange={(e) => setData((prev) => ({ ...prev, target_role: e.target.value }))}
                className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
          </section>

          {/* Reorderable Block Order */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Порядок блоків у резюме</h2>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {blockOrder.map((blockKey, idx) => (
                <div
                  key={blockKey}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700"
                >
                  <span>{BLOCK_LABELS_UK[blockKey]}</span>
                  <button
                    type="button"
                    onClick={() => moveBlock(idx, -1)}
                    disabled={idx === 0}
                    className="rounded p-0.5 hover:bg-slate-200 disabled:opacity-30"
                    title="Вгору"
                  >
                    <ArrowUp className="h-3 w-3" />
                  </button>
                  <button
                    type="button"
                    onClick={() => moveBlock(idx, 1)}
                    disabled={idx === blockOrder.length - 1}
                    className="rounded p-0.5 hover:bg-slate-200 disabled:opacity-30"
                    title="Вниз"
                  >
                    <ArrowDown className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* Summary + AI buttons */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-slate-900">Про себе</h2>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={aiLoading}
                  onClick={() => void handleAiGenerateSummary()}
                  className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  AI: 3 варіанти
                </button>
                <button
                  type="button"
                  disabled={aiLoading}
                  onClick={() => void handleAiEditSummary()}
                  className="inline-flex items-center gap-1 rounded-lg border border-blue-200 px-2.5 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50 disabled:opacity-50"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  AI: Покращити текст
                </button>
              </div>
            </div>
            <textarea
              rows={4}
              value={data.summary}
              onChange={(e) => setData((prev) => ({ ...prev, summary: e.target.value }))}
              placeholder="Коротко опишіть свій досвід, ключові навички та фокус..."
              className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="text"
              value={editInstruction}
              onChange={(e) => setEditInstruction(e.target.value)}
              placeholder="Інструкція для AI-правки"
              className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600"
            />
          </section>

          {/* Experience + AI per bullet */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">
                Досвід роботи ({data.experiences.length}/15)
              </h2>
              <button
                type="button"
                disabled={data.experiences.length >= 15}
                onClick={() =>
                  setData((prev) => ({
                    ...prev,
                    experiences: [
                      ...prev.experiences,
                      {
                        id: crypto.randomUUID(),
                        company: "",
                        position: "",
                        start_date: "",
                        end_date: "",
                        is_current: false,
                        bullets: [""],
                      },
                    ],
                  }))
                }
                className="inline-flex items-center gap-1 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-50"
              >
                <Plus className="h-3.5 w-3.5" />
                Додати місце
              </button>
            </div>

            <div className="mt-3 space-y-4">
              {data.experiences.map((exp, ei) => (
                <div key={exp.id || ei} className="rounded-lg border border-slate-200 p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-500">Місце роботи #{ei + 1}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setData((prev) => ({
                          ...prev,
                          experiences: prev.experiences.filter((_, idx) => idx !== ei),
                        }))
                      }
                      className="text-red-500 hover:text-red-700"
                      title="Видалити"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                  <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <input
                      type="text"
                      placeholder="Посада"
                      value={exp.position}
                      onChange={(e) => {
                        const val = e.target.value;
                        setData((prev) => {
                          const next = [...prev.experiences];
                          next[ei] = { ...next[ei], position: val };
                          return { ...prev, experiences: next };
                        });
                      }}
                      className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Компанія"
                      value={exp.company}
                      onChange={(e) => {
                        const val = e.target.value;
                        setData((prev) => {
                          const next = [...prev.experiences];
                          next[ei] = { ...next[ei], company: val };
                          return { ...prev, experiences: next };
                        });
                      }}
                      className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                    />
                    <input
                      type="month"
                      value={exp.start_date}
                      onChange={(e) => {
                        const val = e.target.value;
                        setData((prev) => {
                          const next = [...prev.experiences];
                          next[ei] = { ...next[ei], start_date: val };
                          return { ...prev, experiences: next };
                        });
                      }}
                      className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                    />
                    <div className="flex items-center gap-2">
                      <input
                        type="month"
                        disabled={exp.is_current}
                        value={exp.end_date}
                        onChange={(e) => {
                          const val = e.target.value;
                          setData((prev) => {
                            const next = [...prev.experiences];
                            next[ei] = { ...next[ei], end_date: val };
                            return { ...prev, experiences: next };
                          });
                        }}
                        className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm disabled:bg-slate-100"
                      />
                      <label className="flex shrink-0 items-center gap-1 text-xs text-slate-600">
                        <input
                          type="checkbox"
                          checked={exp.is_current}
                          onChange={(e) => {
                            const checked = e.target.checked;
                            setData((prev) => {
                              const next = [...prev.experiences];
                              next[ei] = {
                                ...next[ei],
                                is_current: checked,
                                end_date: checked ? "" : next[ei].end_date,
                              };
                              return { ...prev, experiences: next };
                            });
                          }}
                        />
                        Зараз
                      </label>
                    </div>
                  </div>

                  {/* Bullets */}
                  <div className="mt-3 space-y-2">
                    {exp.bullets.map((b, bi) => (
                      <div key={bi} className="flex items-center gap-2">
                        <input
                          type="text"
                          value={b}
                          placeholder="Опишіть досягнення або задачу..."
                          onChange={(e) => {
                            const val = e.target.value;
                            setData((prev) => {
                              const next = [...prev.experiences];
                              const bullets = [...next[ei].bullets];
                              bullets[bi] = val;
                              next[ei] = { ...next[ei], bullets };
                              return { ...prev, experiences: next };
                            });
                          }}
                          className="w-full rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                        />
                        <button
                          type="button"
                          disabled={aiLoading}
                          onClick={() => void handleAiImproveBullet(ei, bi)}
                          className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-blue-50 px-2.5 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
                          title="Покращити пункт з AI"
                        >
                          <Sparkles className="h-3.5 w-3.5" />
                          AI
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={() =>
                        setData((prev) => {
                          const next = [...prev.experiences];
                          next[ei] = { ...next[ei], bullets: [...next[ei].bullets, ""] };
                          return { ...prev, experiences: next };
                        })
                      }
                      className="text-xs font-medium text-blue-600 hover:underline"
                    >
                      + Додати пункт досягнення
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Education */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-slate-900">Освіта</h2>
              <button
                type="button"
                onClick={() =>
                  setData((prev) => ({
                    ...prev,
                    education: [
                      ...prev.education,
                      {
                        id: crypto.randomUUID(),
                        institution: "",
                        degree: "",
                        field_of_study: "",
                        start_date: "",
                        end_date: "",
                        is_current: false,
                      },
                    ],
                  }))
                }
                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                <Plus className="h-3.5 w-3.5" />
                Додати освіту
              </button>
            </div>
            <div className="mt-3 space-y-3">
              {data.education.map((edu, idx) => (
                <div key={edu.id || idx} className="grid grid-cols-1 gap-2 rounded-lg border border-slate-200 p-3 sm:grid-cols-2">
                  <input
                    type="text"
                    placeholder="Заклад освіти"
                    value={edu.institution}
                    onChange={(e) => {
                      const val = e.target.value;
                      setData((prev) => {
                        const next = [...prev.education];
                        next[idx] = { ...next[idx], institution: val };
                        return { ...prev, education: next };
                      });
                    }}
                    className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm sm:col-span-2"
                  />
                  <input
                    type="text"
                    placeholder="Ступінь (напр. Бакалавр)"
                    value={edu.degree}
                    onChange={(e) => {
                      const val = e.target.value;
                      setData((prev) => {
                        const next = [...prev.education];
                        next[idx] = { ...next[idx], degree: val };
                        return { ...prev, education: next };
                      });
                    }}
                    className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                  <input
                    type="text"
                    placeholder="Спеціальність"
                    value={edu.field_of_study}
                    onChange={(e) => {
                      const val = e.target.value;
                      setData((prev) => {
                        const next = [...prev.education];
                        next[idx] = { ...next[idx], field_of_study: val };
                        return { ...prev, education: next };
                      });
                    }}
                    className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm"
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Skills */}
          <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900">Навички ({data.skills.length}/30)</h2>
            <div className="mt-2 flex gap-2">
              <input
                type="text"
                value={skillInput}
                onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addSkill();
                  }
                }}
                placeholder="Наприклад: TypeScript"
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
              <button
                type="button"
                onClick={addSkill}
                className="rounded-lg bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
              >
                Додати
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {data.skills.map((skill, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800"
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() =>
                      setData((prev) => ({ ...prev, skills: prev.skills.filter((_, i) => i !== idx) }))
                    }
                    className="text-slate-400 hover:text-red-600"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </section>
        </div>

        {/* Right: Live Preview */}
        <div className={`lg:col-span-6 ${mobileTab === "edit" ? "hidden lg:block" : ""}`}>
          <div className="sticky top-20">
            <ResumePreview
              data={data}
              templateId={templateId}
              language={language}
              blockOrder={blockOrder}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
