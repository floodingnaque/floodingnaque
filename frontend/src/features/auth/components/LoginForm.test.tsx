/**
 * LoginForm Component Tests
 *
 * Tests for the LoginForm component with form validation and submission.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@/test/utils';
import { LoginForm } from '@/features/auth/components/LoginForm';

// Mock useAuth hook
const mockLogin = vi.fn();
const mockUseAuth: {
  login: typeof mockLogin;
  isLoggingIn: boolean;
  loginError: { message?: string } | null;
} = {
  login: mockLogin,
  isLoggingIn: false,
  loginError: null,
};

vi.mock('../hooks/useAuth', () => ({
  useAuth: () => mockUseAuth,
}));

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.login = mockLogin;
    mockUseAuth.isLoggingIn = false;
    mockUseAuth.loginError = null;
  });

  describe('Rendering', () => {
    it('should render form title', () => {
      render(<LoginForm />);

      expect(screen.getByText('Welcome back')).toBeInTheDocument();
    });

    it('should render email input', () => {
      render(<LoginForm />);

      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText('name@example.com')).toBeInTheDocument();
    });

    it('should render password input', () => {
      render(<LoginForm />);

      expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
    });

    it('should render submit button', () => {
      render(<LoginForm />);

      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('should render sign up link', () => {
      render(<LoginForm />);

      expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should show error for empty email', async () => {
      const { user } = render(<LoginForm />);

      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument();
      });
    });

    it('should show error for invalid email format', async () => {
      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'invalid-email');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      
      // Use fireEvent.submit to bypass jsdom's native HTML5 email validation
      // that blocks form submission when type="email" has invalid value
      const form = screen.getByRole('button', { name: /sign in/i }).closest('form')!;
      fireEvent.submit(form);

      await waitFor(() => {
        // Zod's email() validation message from LoginForm schema
        expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument();
      });
    });

    it('should show error for empty password', async () => {
      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument();
      });
    });

    it('should show error for short password', async () => {
      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'short');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
      });
    });
  });

  describe('Form Submission', () => {
    it('should call login with credentials when form is valid', async () => {
      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password123');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
        });
      });
    });

    it('should not submit form with invalid data', async () => {
      const { user } = render(<LoginForm />);

      await user.type(screen.getByLabelText(/email/i), 'invalid');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(mockLogin).not.toHaveBeenCalled();
      });
    });
  });

  describe('Loading State', () => {
    it('should show loading state when logging in', () => {
      mockUseAuth.isLoggingIn = true;
      render(<LoginForm />);

      expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument();
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('should disable inputs when logging in', () => {
      mockUseAuth.isLoggingIn = true;
      render(<LoginForm />);

      expect(screen.getByLabelText(/email/i)).toBeDisabled();
      expect(screen.getByLabelText(/password/i)).toBeDisabled();
    });
  });

  describe('Error Display', () => {
    it('should display login error message', () => {
      mockUseAuth.loginError = { message: 'Invalid credentials' };
      render(<LoginForm />);

      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
    });

    it('should display default error message if none provided', () => {
      mockUseAuth.loginError = {};
      render(<LoginForm />);

      expect(screen.getByText(/login failed/i)).toBeInTheDocument();
    });
  });

  describe('Switch to Register', () => {
    it('should call onSwitchToRegister when clicked', async () => {
      const onSwitchToRegister = vi.fn();
      const { user } = render(<LoginForm onSwitchToRegister={onSwitchToRegister} />);

      await user.click(screen.getByRole('button', { name: /sign up/i }));

      expect(onSwitchToRegister).toHaveBeenCalled();
    });

    it('should render button instead of link when onSwitchToRegister is provided', () => {
      const onSwitchToRegister = vi.fn();
      render(<LoginForm onSwitchToRegister={onSwitchToRegister} />);

      expect(screen.getByRole('button', { name: /sign up/i })).toBeInTheDocument();
      expect(screen.queryByRole('link', { name: /sign up/i })).not.toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have correct autocomplete attributes', () => {
      render(<LoginForm />);

      expect(screen.getByLabelText(/email/i)).toHaveAttribute('autocomplete', 'email');
      expect(screen.getByLabelText(/password/i)).toHaveAttribute('autocomplete', 'current-password');
    });

    it('should set aria-invalid when there are errors', async () => {
      const { user } = render(<LoginForm />);

      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true');
      });
    });
  });
});
