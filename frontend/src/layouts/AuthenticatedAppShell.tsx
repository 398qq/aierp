import { useEffect, useRef } from "react";
import { Navigate } from "react-router";

import MainLayout from "./MainLayout";
import { useAuthStore } from "../store/auth";
import FullPageLoader from "../ui/FullPageLoader";

export default function AuthenticatedAppShell() {
  const initializationStarted = useRef(false);
  const init = useAuthStore((state) => state.init);
  const loading = useAuthStore((state) => state.loading);
  const username = useAuthStore((state) => state.username);

  useEffect(() => {
    if (initializationStarted.current) {
      return;
    }

    initializationStarted.current = true;
    void init();
  }, [init]);

  if (loading) {
    return <FullPageLoader />;
  }

  return username ? <MainLayout /> : <Navigate to="/login" replace />;
}
