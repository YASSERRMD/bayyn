"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogIn, LogOut, User } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

export function NavUser() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  if (isLoading) return null;

  if (!user) {
    return (
      <Link
        href="/login"
        className="flex items-center gap-1.5 text-white/80 hover:text-bayyn-gold transition-colors"
      >
        <LogIn className="w-4 h-4" />
        <span>Sign in</span>
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1.5 text-white/70 text-xs">
        <User className="w-3.5 h-3.5" />
        <span className="max-w-[120px] truncate">{user.email ?? user.name ?? "Account"}</span>
      </div>
      <button
        onClick={() => {
          logout();
          router.push("/");
        }}
        className="flex items-center gap-1 text-white/60 hover:text-bayyn-gold transition-colors text-xs"
        aria-label="Sign out"
      >
        <LogOut className="w-3.5 h-3.5" />
        <span>Out</span>
      </button>
    </div>
  );
}
