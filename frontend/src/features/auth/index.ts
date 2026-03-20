/**
 * Auth Feature Module
 *
 * Barrel export for all authentication-related components,
 * hooks, and services.
 */

// Components
export { AuthPageLayout } from "./components/AuthPageLayout";
export { CityStatusBadge } from "./components/CityStatusBadge";
export { ForgotPasswordForm } from "./components/ForgotPasswordForm";
export { LoginForm } from "./components/LoginForm";
export { PasswordRequirements } from "./components/PasswordRequirements";
export { ProtectedRoute } from "./components/ProtectedRoute";
export { RegisterForm } from "./components/RegisterForm";
export { RegistrationWizard } from "./components/RegistrationWizard";

// Hooks
export { authQueryKeys, useAuth } from "./hooks/useAuth";

// Services
export { authApi } from "./services/authApi";

// Constants
export {
  BARANGAY_NAMES,
  PARANAQUE_BARANGAYS,
  getBarangayInfo,
} from "./constants/paranaque-data";
