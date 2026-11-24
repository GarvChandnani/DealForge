/**
 * DealForge Frontend — Root App Component.
 */

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { authApi } from "./api/client";
import { AuthPage } from "./components/AuthPage";
import { Dashboard } from "./pages/Dashboard";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,  // 1 minute
      retry: 1,
    },
  },
});

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("dealforge_token"));
  const [isCheckingSession, setIsCheckingSession] = useState(Boolean(token));

  useEffect(() => {
    if (!token) return;

    let isMounted = true;
    authApi
      .me()
      .catch(() => {
        localStorage.removeItem("dealforge_token");
        if (isMounted) setToken(null);
      })
      .finally(() => {
        if (isMounted) setIsCheckingSession(false);
      });

    return () => {
      isMounted = false;
    };
  }, [token]);

  function signOut() {
    localStorage.removeItem("dealforge_token");
    queryClient.clear();
    setIsCheckingSession(false);
    setToken(null);
  }

  function signIn(accessToken: string) {
    queryClient.clear();
    setIsCheckingSession(true);
    setToken(accessToken);
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {isCheckingSession ? (
          <main className="flex min-h-screen items-center justify-center bg-[#0d1117] text-slate-300">
            Checking your DealForge session…
          </main>
        ) : token ? (
          <Routes>
            <Route path="*" element={<Dashboard onLogout={signOut} />} />
          </Routes>
        ) : (
          <AuthPage onAuthenticated={signIn} />
        )}
      </BrowserRouter>
    </QueryClientProvider>
  );
}
