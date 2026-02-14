"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

export default function LogoutPage() {
  const router = useRouter();

  useEffect(() => {
    clearToken();
    router.replace("/");
  }, [router]);

  return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="text-sm text-muted-foreground">Logging out...</div>
    </div>
  );
}
