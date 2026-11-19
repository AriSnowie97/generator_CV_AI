"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, CheckCircle2, FileCheck2, ShieldCheck, Sparkles } from "@/components/Icons";
import { ResumePreview } from "@/components/ResumePreview";
import { DEFAULT_BLOCK_ORDER, DEMO_PROFILE_DATA, TemplateId } from "@/lib/types";

export default function LandingPage() {
  const [selectedTpl, setSelectedTpl] = useState<TemplateId>("minimal");

  return (
    <div className="bg-gradient-to-b from-white to-slate-50">
      {/* Hero */}
      <section className="mx-auto max-w-7xl px-4 pb-14 pt-12 sm:px-6 lg:pt-16">
        <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-12">
          <div className="lg:col-span-6">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
              <Sparkles className="h-3.5 w-3.5" />
              Для шукачів роботи в Україні · Українська та English
            </span>
            <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
              Якісне резюме за 15 хвилин з одного профілю
            </h1>
            <p className="mt-4 text-base leading-relaxed text-slate-600 sm:text-lg">
              Заповніть профіль один раз, перемикайтеся між 3 ATS-дружніми шаблонами без втрати даних, отримуйте
              допомогу AI (лише після вашого підтвердження) і завантажуйте коректний PDF та DOCX без водяних знаків.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition"
              >
                Створити резюме
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/demo"
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition"
              >
                Спробувати демо-редактор
              </Link>
            </div>

            <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="flex items-start gap-2 text-xs text-slate-600">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <span>Виділюваний текст у PDF і кирилиця без помилок</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-slate-600">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                <span>AI не вигадує факти й позначає невідоме як «уточніть»</span>
              </div>
              <div className="flex items-start gap-2 text-xs text-slate-600">
                <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
                <span>Назва файлу формату Імʼя_Прізвище_Посада_Resume</span>
              </div>
            </div>
          </div>

          {/* Interactive Template Gallery Preview */}
          <div className="lg:col-span-6">
            <div className="rounded-2xl border border-slate-200 bg-slate-100/80 p-4 shadow-sm">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Галерея шаблонів (натисніть для перегляду)
                </span>
                <div className="flex gap-1 rounded-lg bg-white p-1 shadow-sm">
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
                      onClick={() => setSelectedTpl(id)}
                      className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                        selectedTpl === id ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="max-h-[540px] overflow-y-auto rounded-xl">
                <ResumePreview
                  data={DEMO_PROFILE_DATA}
                  templateId={selectedTpl}
                  language="uk"
                  blockOrder={DEFAULT_BLOCK_ORDER}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value props */}
      <section className="border-t border-slate-200 bg-white py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <h2 className="text-center text-2xl font-bold text-slate-900">Чому ResumeCraft?</h2>
          <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-3">
            <div className="rounded-xl border border-slate-200 p-5">
              <h3 className="font-semibold text-slate-900">Один профіль — будь-який шаблон</h3>
              <p className="mt-2 text-sm text-slate-600">
                Заповнюєте контакти, досвід, освіту, навички та мови один раз. Перемикання шаблону та перестановка
                блоків зберігаються автоматично.
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <h3 className="font-semibold text-slate-900">Контрольований AI-помічник</h3>
              <p className="mt-2 text-sm text-slate-600">
                Пропонує 2–3 варіанти досягнень («дія + результат + цифра») або 3 варіанти «Про себе». Зміни
                застосовуються лише після натискання «Прийняти».
              </p>
            </div>
            <div className="rounded-xl border border-slate-200 p-5">
              <h3 className="font-semibold text-slate-900">Готово для Work.ua, Djinni та LinkedIn</h3>
              <p className="mt-2 text-sm text-slate-600">
                Чистий PDF без таблиць верстки та структурований DOCX. Повне видалення всіх персональних даних у
                налаштуваннях за одним запитом.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
