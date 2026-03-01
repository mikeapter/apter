"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { clearToken, clearStoredUser } from "@/lib/auth";

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    // Call backend to clear httpOnly cookies, then clear client state
    fetch("/auth/logout", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    })
      .catch(() => {})
      .finally(() => {
        clearToken();
        clearStoredUser();
        router.replace("/");
      });
  }, [router]);

  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="text-sm text-muted-foreground">Logging out...</div>
    </div>
  );
}
