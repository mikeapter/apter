"use client";

import { useState, useEffect, useRef } from "react";
import { User, Camera, Save, Loader2 } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { authGet, authPut, fetchWithAuth } from "@/lib/fetchWithAuth";

type ProfileData = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  account_name: string | null;
  avatar_url: string | null;
  subscription_tier: string;
  created_at: string | null;
};

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    authGet<ProfileData>("/api/me").then((res) => {
      if (res.ok) {
        setProfile(res.data);
        setFullName(res.data.full_name || "");
        setPhone(res.data.phone || "");
      }
      setLoading(false);
    });
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSuccess(false);

    const res = await authPut<ProfileData>("/api/me", {
      full_name: fullName,
      phone: phone || null,
    });

    if (res.ok) {
      setProfile(res.data);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } else {
      setError(res.error || "Failed to save");
    }
    setSaving(false);
  }

  async function handleAvatarUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetchWithAuth<{ avatar_url: string }>("/api/me/avatar", {
      method: "PUT",
      body: formData,
      headers: {},
    });

    if (res.ok && profile) {
      setProfile({ ...profile, avatar_url: res.data.avatar_url });
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground text-sm">
        <Loader2 size={18} className="animate-spin mr-2" /> Loading profile...
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Profile</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your personal information and avatar.</p>
      </div>

      {/* Avatar section */}
      <section className="bt-panel p-6">
        <div className="flex items-center gap-6">
          <div className="relative">
            <div className="h-20 w-20 rounded-full border-2 border-border bg-panel-2 flex items-center justify-center overflow-hidden">
              {profile?.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt="Avatar"
                  className="h-full w-full object-cover"
                />
              ) : (
                <User size={32} className="text-muted-foreground" />
              )}
            </div>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="absolute -bottom-1 -right-1 h-8 w-8 rounded-full border border-border bg-panel flex items-center justify-center hover:bg-muted transition-colors"
              title="Upload photo"
            >
              <Camera size={14} />
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleAvatarUpload}
            />
          </div>
          <div>
            <div className="font-medium">{profile?.full_name || "—"}</div>
            <div className="text-sm text-muted-foreground">{profile?.email}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Member since {profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : "—"}
            </div>
          </div>
        </div>
      </section>

      {/* Info form */}
      <section className="bt-panel p-6 space-y-4">
        <div className="bt-panel-title">PERSONAL INFORMATION</div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="bt-label">Full Name</label>
            <input
              className="bt-input h-11"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="bt-label">Email</label>
            <input
              className="bt-input h-11 text-muted-foreground"
              value={profile?.email || ""}
              readOnly
            />
            <p className="text-[10px] text-muted-foreground mt-1">Email cannot be changed.</p>
          </div>
          <div>
            <label className="bt-label">Phone</label>
            <input
              className="bt-input h-11"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+1 (555) 000-0000"
            />
          </div>
          <div>
            <label className="bt-label">Account Tier</label>
            <input
              className="bt-input h-11 text-muted-foreground capitalize"
              value={profile?.subscription_tier || "observer"}
              readOnly
            />
          </div>
        </div>

        {/* Save button + feedback */}
        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="bt-button-primary h-11 px-6 gap-2"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            Save Changes
          </button>
          {success && <span className="text-xs text-risk-on">Profile updated successfully.</span>}
          {error && <span className="text-xs text-risk-off">{error}</span>}
        </div>
      </section>
    </div>
  );
}
