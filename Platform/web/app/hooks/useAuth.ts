"use client";

import { createContext, useContext } from "react";

export type AuthUser = {
  user_id: number;
  email: string;
  tier: string;
  status: string;
};

export type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
};

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
