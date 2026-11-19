"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, LogOut, Settings, User as UserIcon } from "@/components/Icons";
import { getStoredToken, setStoredToken } from "@/lib/api";

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isAuthed, setIsAuthed] = useState(false);

  useEffect(() => {
    setIsAuthed(Boolean(getStoredToken()));
  }, [pathname]);

  const handleLogout = () => {
    setStoredToken(null);
    setIsAuthed(false);
    router.push("/login");
  };

  const navLinkClass = (href: string) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium transition ${pathname === href
      ? "bg-blue-50 text-blue-700"
      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
    }`;

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-bold text-slate-900">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white">
            <FileText className="h-4 w-4" />
          </span>
          <span className="text-lg tracking-tight">ResumeCraft</span>
        </Link>

        <nav className="flex flex-wrap items-center gap-1 sm:gap-2">
          {!isAuthed ? (
            <>
              <Link href="/demo" className={navLinkClass("/demo")}>
                Демо-редактор
              </Link>
              <Link href="/login" className={navLinkClass("/login")}>
                Увійти
              </Link>
              <Link
                href="/register"
                className="rounded-lg bg-blue-600 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-blue-700 transition"
              >
                Створити резюме
              </Link>
            </>
          ) : (
            <>
              <Link href="/profile" className={navLinkClass("/profile")}>
                <span className="inline-flex items-center gap-1.5">
                  <UserIcon className="h-4 w-4" />
                  Профіль
                </span>
              </Link>
              <Link href="/editor" className={navLinkClass("/editor")}>
                Редактор
              </Link>
              <Link href="/settings" className={navLinkClass("/settings")}>
                <span className="inline-flex items-center gap-1.5">
                  <Settings className="h-4 w-4" />
                  Налаштування
                </span>
              </Link>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                title="Вийти"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Вийти</span>
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
