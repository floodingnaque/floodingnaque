/* eslint-disable react-refresh/only-export-components */
/**
 * Application Providers
 *
 * Composes all application providers into a single component
 * for clean integration in the app root.
 */

import { graphqlClient } from "@/lib/graphql-client";
import { MotionConfig } from "framer-motion";
import { type ReactNode } from "react";
import { Provider as UrqlProvider } from "urql";
import { QueryProvider } from "./QueryProvider";
import { ThemeProvider } from "./ThemeProvider";

/**
 * Props for Providers component
 */
interface ProvidersProps {
  children: ReactNode;
}

/**
 * Providers component
 *
 * Wraps the application with all necessary providers in the correct order:
 * 1. QueryProvider - React Query for server state
 * 2. ThemeProvider - Theme context for dark/light mode
 */
export function Providers({ children }: ProvidersProps) {
  return (
    <QueryProvider>
      <UrqlProvider value={graphqlClient}>
        <ThemeProvider>
          <MotionConfig reducedMotion="user">{children}</MotionConfig>
        </ThemeProvider>
      </UrqlProvider>
    </QueryProvider>
  );
}

export default Providers;

// Re-export providers and hooks for convenience
export { QueryProvider } from "./QueryProvider";
export { ThemeProvider, useTheme } from "./ThemeProvider";
