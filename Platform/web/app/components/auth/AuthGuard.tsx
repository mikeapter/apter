"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken, clearToken } from "@/lib/auth";
import { authGet } from "@/lib/fetchWithAuth";
import { AuthContext, type AuthUser } from "../../hooks/useAuth";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Use fetchWithAuth which sends cookies + bearer header and handles 401 refresh
    authGet<AuthUser>("/auth/me").then((r) => {
      if (r.ok) {
        setUser(r.data);
      } else {
        // fetchWithAuth already handles force-logout on genuine 401
        // If we get here with a non-transient error, clear local state
        if (!("transient" in r) || !r.transient) {
          clearToken();
          router.replace("/login");
        }
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
