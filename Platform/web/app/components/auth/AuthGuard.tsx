"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, clearToken } from "@/lib/auth";
import { apiGet } from "@/lib/api";
import { AuthContext, type AuthUser } from "../../hooks/useAuth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      clearToken();
      router.replace("/login");
      return;
    }

    apiGet<AuthUser>("/auth/me", undefined, token).then((r) => {
      if (r.ok) {
        setUser(r.data);
      } else {
        clearToken();
        router.replace("/login");
      }
      setLoading(false);
    });
  }, [router]);

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-background text-foreground">
        <div className="text-sm text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  );
}
