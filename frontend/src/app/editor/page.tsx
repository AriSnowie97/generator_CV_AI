"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ResumeEditorWorkspace } from "@/components/ResumeEditorWorkspace";
import { getStoredToken } from "@/lib/api";

export default function EditorPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getStoredToken()) {
      router.push("/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return <div className="py-16 text-center text-sm text-slate-500">Перевірка авторизації...</div>;
  }

  return <ResumeEditorWorkspace />;
}
