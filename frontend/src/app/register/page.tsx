"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { api, setStoredToken } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [verifyToken, setVerifyToken] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!consent) {
      setError("Необхідно надати згоду на обробку персональних даних.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await api.register(email, password, consent);
      setStoredToken(res.access_token);
      if (res.verification_token_preview) {
        setVerifyToken(res.verification_token_preview);
      } else {
        router.push("/profile");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Помилка реєстрації");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md px-4 py-12">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <h1 className="text-2xl font-bold text-slate-900">Реєстрація</h1>
        <p className="mt-1 text-sm text-slate-600">Створіть акаунт, щоб зберігати профіль, резюме та експортувати PDF/DOCX.</p>

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>
        )}

        {verifyToken ? (
          <div className="mt-5 space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
            <p className="font-semibold">Акаунт створено!</p>
            <p>
              У dev-режимі ви можете миттєво підтвердити email за посиланням нижче або перейти одразу до заповнення
              профілю:
            </p>
            <div className="flex flex-wrap gap-2">
              <Link
                href={`/verify-email?token=${encodeURIComponent(verifyToken)}`}
                className="rounded-lg bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-800"
              >
                Підтвердити email
              </Link>
              <Link
                href="/profile"
                className="rounded-lg border border-emerald-700 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-white"
              >
                Перейти до профілю
              </Link>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700">Пароль (мінімум 8 символів)</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
            </div>
            <label className="flex items-start gap-2 text-xs text-slate-600">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                Я надаю згоду на обробку моїх персональних даних для створення й експорту резюме та знаю, що можу
                остаточно видалити акаунт у налаштуваннях.
              </span>
            </label>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
            >
              {loading ? "Створення..." : "Зареєструватися"}
            </button>
          </form>
        )}

        <p className="mt-5 text-center text-sm text-slate-600">
          Вже маєте акаунт?{" "}
          <Link href="/login" className="font-semibold text-blue-600 hover:underline">
            Увійти
          </Link>
        </p>
      </div>
    </div>
  );
}
