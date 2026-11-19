"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Download, Trash2 } from "@/components/Icons";
import { api, getStoredToken, setStoredToken } from "@/lib/api";
import { User } from "@/lib/types";

export default function SettingsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [lang, setLang] = useState<"uk" | "en">("uk");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getStoredToken()) {
      router.push("/login");
      return;
    }
    api
      .me()
      .then((u) => {
        setUser(u);
        setLang((u.preferred_interface_language as "uk" | "en") || "uk");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Помилка профілю"));
  }, [router]);

  const handleSaveLang = async (nextLang: "uk" | "en") => {
    setLang(nextLang);
    setError("");
    try {
      const updated = await api.updatePreferences(nextLang);
      setUser(updated);
      setStatus("Налаштування збережено.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не вдалося оновити налаштування");
    }
  };

  const handleExportJson = async () => {
    setError("");
    try {
      const bundle = await api.exportPersonalData();
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "resumecraft_personal_data.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка експорту даних");
    }
  };

  const handleDeleteAccount = async () => {
    setError("");
    try {
      await api.deleteAccount();
      setStoredToken(null);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не вдалося видалити акаунт");
    }
  };

  if (!user) {
    return <div className="py-16 text-center text-sm text-slate-500">Завантаження налаштувань...</div>;
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold text-slate-900">Налаштування акаунта</h1>

      {status && (
        <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm text-emerald-800">
          {status}
        </div>
      )}
      {error && (
        <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">{error}</div>
      )}

      <div className="mt-6 space-y-5">
        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Акаунт</h2>
          <p className="mt-2 text-sm text-slate-700">
            Email: <strong>{user.email}</strong>{" "}
            <span className="ml-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs">
              {user.is_email_verified ? "Підтверджено" : "Не підтверджено"}
            </span>
          </p>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Мова</h2>
          <select
            value={lang}
            onChange={(e) => void handleSaveLang(e.target.value as "uk" | "en")}
            className="mt-2 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="uk">Українська (за замовчуванням)</option>
            <option value="en">English</option>
          </select>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-900">Експорт персональних даних</h2>
          <p className="mt-1 text-sm text-slate-600">
            Завантажте копію вашого профілю, резюме та історії подій у форматі JSON.
          </p>
          <button
            type="button"
            onClick={() => void handleExportJson()}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Download className="h-4 w-4" />
            Експортувати дані (JSON)
          </button>
        </section>

        <section className="rounded-xl border border-red-200 bg-red-50/40 p-5">
          <h2 className="text-base font-semibold text-red-900">Видалення акаунта</h2>
          <p className="mt-1 text-sm text-red-800">
            Ця дія остаточно видалить ваш профіль, резюме, журнали AI-запитів та всі експортовані PDF/DOCX файли без
            можливості відновлення.
          </p>

          {!confirmDelete ? (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              <Trash2 className="h-4 w-4" />
              Видалити акаунт
            </button>
          ) : (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void handleDeleteAccount()}
                className="rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800"
              >
                Підтвердити остаточне видалення
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700"
              >
                Скасувати
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
