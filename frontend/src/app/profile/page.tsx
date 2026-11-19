"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, Plus, Save, Trash2 } from "@/components/Icons";
import { api, getStoredToken } from "@/lib/api";
import { EMPTY_PROFILE_DATA, ProfileData } from "@/lib/types";
import { validateProfileData } from "@/lib/validation";

const BLOCK_NAMES: Record<string, string> = {
  contacts: "Контакти",
  target_role: "Бажана посада",
  summary: "Про себе",
  experience: "Досвід роботи",
  education: "Освіта",
  skills: "Навички",
  languages: "Мови",
  links: "Посилання",
};

export default function ProfilePage() {
  const router = useRouter();
  const [data, setData] = useState<ProfileData>(EMPTY_PROFILE_DATA);
  const [score, setScore] = useState(0);
  const [missing, setMissing] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [savedNotice, setSavedNotice] = useState("");
  const [skillInput, setSkillInput] = useState("");

  useEffect(() => {
    if (!getStoredToken()) {
      router.push("/login");
      return;
    }
    api
      .getProfile()
      .then((res) => {
        setData(res.data);
        setScore(res.completeness_score);
        setMissing(res.missing_blocks);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Помилка завантаження профілю"))
      .finally(() => setLoading(false));
  }, [router]);

  const handleSave = async () => {
    const errs = validateProfileData(data);
    if (errs.length > 0) {
      setError(errs[0]);
      return;
    }
    setError("");
    setSavedNotice("");
    setSaving(true);
    try {
      const updated = await api.updateProfile(data, true);
      setData(updated.data);
      setScore(updated.completeness_score);
      setMissing(updated.missing_blocks);
      setSavedNotice("Профіль збережено та синхронізовано з вашим резюме.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не вдалося зберегти профіль");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="py-16 text-center text-sm text-slate-500">Завантаження профілю...</div>;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* Header & Completeness */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Єдиний профіль кандидата</h1>
            <p className="mt-1 text-sm text-slate-600">
              Заповніть дані один раз — вони автоматично підставляться у вибраний шаблон резюме.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={saving}
              onClick={() => void handleSave()}
              className="inline-flex items-center gap-1.5 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              <Save className="h-4 w-4" />
              {saving ? "Збереження..." : "Зберегти профіль"}
            </button>
            <Link
              href="/editor"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            >
              До редактора
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
            <span>Заповненість профілю</span>
            <span>{score}%</span>
          </div>
          <div className="mt-1.5 h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${score}%` }} />
          </div>
          {missing.length > 0 && (
            <p className="mt-2 text-xs text-slate-500">
              Щоб покращити резюме, заповніть: {missing.map((m) => BLOCK_NAMES[m] || m).join(", ")}.
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
      )}
      {savedNotice && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {savedNotice}
        </div>
      )}

      <div className="mt-6 space-y-5">
        {/* Contacts & Goal */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">1. Контакти та ціль</h2>
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
              onChange={(e) => setData((prev) => ({ ...prev, contacts: { ...prev.contacts, email: e.target.value } }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Телефон (+380...)"
              value={data.contacts.phone}
              onChange={(e) => setData((prev) => ({ ...prev, contacts: { ...prev.contacts, phone: e.target.value } }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Місто"
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
            <input
              type="text"
              placeholder="Формат роботи (Віддалено / Гібрид / Офіс)"
              value={data.work_format}
              onChange={(e) => setData((prev) => ({ ...prev, work_format: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
            <input
              type="text"
              placeholder="Бажана зарплата (необов'язково)"
              value={data.desired_salary}
              onChange={(e) => setData((prev) => ({ ...prev, desired_salary: e.target.value }))}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
            />
          </div>
          <textarea
            rows={3}
            placeholder="Коротко про себе..."
            value={data.summary}
            onChange={(e) => setData((prev) => ({ ...prev, summary: e.target.value }))}
            className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </section>

        {/* Languages & Links */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">2. Мови та посилання (GitHub, портфоліо, LinkedIn)</h2>
          </div>

          <div className="mt-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">Мови</span>
              <button
                type="button"
                onClick={() =>
                  setData((prev) => ({ ...prev, languages: [...prev.languages, { name: "", level: "" }] }))
                }
                className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
              >
                <Plus className="h-3.5 w-3.5" /> Додати мову
              </button>
            </div>
            {data.languages.map((lang, idx) => (
              <div key={idx} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Мова (напр. Англійська)"
                  value={lang.name}
                  onChange={(e) => {
                    const val = e.target.value;
                    setData((prev) => {
                      const next = [...prev.languages];
                      next[idx] = { ...next[idx], name: val };
                      return { ...prev, languages: next };
                    });
                  }}
                  className="w-1/2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                />
                <input
                  type="text"
                  placeholder="Рівень (B2, Рідна...)"
                  value={lang.level}
                  onChange={(e) => {
                    const val = e.target.value;
                    setData((prev) => {
                      const next = [...prev.languages];
                      next[idx] = { ...next[idx], level: val };
                      return { ...prev, languages: next };
                    });
                  }}
                  className="w-1/2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                />
                <button
                  type="button"
                  onClick={() =>
                    setData((prev) => ({ ...prev, languages: prev.languages.filter((_, i) => i !== idx) }))
                  }
                  className="text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">Посилання</span>
              <button
                type="button"
                onClick={() => setData((prev) => ({ ...prev, links: [...prev.links, { label: "", url: "" }] }))}
                className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
              >
                <Plus className="h-3.5 w-3.5" /> Додати посилання
              </button>
            </div>
            {data.links.map((lnk, idx) => (
              <div key={idx} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Назва (GitHub, LinkedIn)"
                  value={lnk.label}
                  onChange={(e) => {
                    const val = e.target.value;
                    setData((prev) => {
                      const next = [...prev.links];
                      next[idx] = { ...next[idx], label: val };
                      return { ...prev, links: next };
                    });
                  }}
                  className="w-1/3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                />
                <input
                  type="url"
                  placeholder="https://..."
                  value={lnk.url}
                  onChange={(e) => {
                    const val = e.target.value;
                    setData((prev) => {
                      const next = [...prev.links];
                      next[idx] = { ...next[idx], url: val };
                      return { ...prev, links: next };
                    });
                  }}
                  className="w-2/3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
                />
                <button
                  type="button"
                  onClick={() => setData((prev) => ({ ...prev, links: prev.links.filter((_, i) => i !== idx) }))}
                  className="text-red-500"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Skills */}
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">3. Навички ({data.skills.length}/30)</h2>
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              value={skillInput}
              onChange={(e) => setSkillInput(e.target.value)}
              placeholder="Додати навичку..."
              className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            />
            <button
              type="button"
              onClick={() => {
                const s = skillInput.trim();
                if (!s || data.skills.length >= 30) return;
                setData((prev) => ({ ...prev, skills: [...prev.skills, s] }));
                setSkillInput("");
              }}
              className="rounded-lg bg-slate-900 px-3.5 py-1.5 text-xs font-medium text-white"
            >
              Додати
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {data.skills.map((skill, idx) => (
              <span key={idx} className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs">
                {skill}
                <button
                  type="button"
                  onClick={() => setData((prev) => ({ ...prev, skills: prev.skills.filter((_, i) => i !== idx) }))}
                  className="text-slate-400 hover:text-red-600"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
