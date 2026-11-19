"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function VerifyEmailInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [message, setMessage] = useState("Перевірка токена...");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Токен підтвердження відсутній у посиланні.");
      return;
    }
    api
      .verifyEmail(token)
      .then(() => {
        setStatus("ok");
        setMessage("Ваш email успішно підтверджено!");
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err instanceof Error ? err.message : "Помилка підтвердження");
      });
  }, [token]);

  return (
    <div className="mx-auto max-w-md px-4 py-14">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <h1 className="text-xl font-bold text-slate-900">Підтвердження Email</h1>
        <p className={`mt-3 text-sm ${status === "error" ? "text-red-700" : "text-slate-700"}`}>{message}</p>
        <div className="mt-5 flex justify-center gap-3">
          <Link href="/profile" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white">
            Перейти до профілю
          </Link>
          <Link href="/editor" className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">
            У редактор
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="py-12 text-center text-sm text-slate-500">Завантаження...</div>}>
      <VerifyEmailInner />
    </Suspense>
  );
}
