import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthGuard } from "@/components/AuthProvider";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}

