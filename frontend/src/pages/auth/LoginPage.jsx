import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AuthFormError from '../../components/auth/AuthFormError';
import { EMAIL_REGEX } from '../../utils/validators';
import { getRoleDashboardPath } from '../../components/common/RoleBasedRedirect';

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false,
    },
  });

  const onSubmit = async (data) => {
    setApiError(null);
    try {
      const result = await login({
        email: data.email.trim(),
        password: data.password,
        rememberMe: data.rememberMe,
      });

      // Redirect to intended route if specified in location state, or role dashboard
      const fromPath = location.state?.from?.pathname;
      const targetPath = fromPath || getRoleDashboardPath(result.role);
      navigate(targetPath, { replace: true });
    } catch (err) {
      setApiError(err);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <h3 className="fw-bold text-dark mb-1">Welcome Back</h3>
        <p className="text-muted">Sign in to access your examination workspace</p>
      </div>

      <AuthFormError error={apiError} onClose={() => setApiError(null)} />


      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {/* Email Field */}
        <div className="mb-3">
          <label className="form-label" htmlFor="email">
            Email Address
          </label>
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-envelope"></i>
            </span>
            <input
              id="email"
              type="email"
              className={`form-control ${errors.email ? 'is-invalid' : ''}`}
              placeholder="name@example.com"
              autoComplete="email"
              {...register('email', {
                required: 'Email address is required',
                pattern: {
                  value: EMAIL_REGEX,
                  message: 'Please enter a valid email address',
                },
              })}
            />
            {errors.email && (
              <div className="invalid-feedback">{errors.email.message}</div>
            )}
          </div>
        </div>

        {/* Password Field */}
        <div className="mb-3">
          <div className="d-flex justify-content-between align-items-center mb-1">
            <label className="form-label mb-0" htmlFor="password">
              Password
            </label>
            <Link to="/forgot-password" className="auth-link fs-7">
              Forgot password?
            </Link>
          </div>
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-key"></i>
            </span>
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              className={`form-control password-input-has-toggle ${
                errors.password ? 'is-invalid' : ''
              }`}
              placeholder="Enter your password"
              autoComplete="current-password"
              {...register('password', {
                required: 'Password is required',
                minLength: {
                  value: 6,
                  message: 'Password must be at least 6 characters',
                },
              })}
            />
            <button
              type="button"
              className="btn password-toggle-btn"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              onClick={() => setShowPassword(!showPassword)}
            >
              <i className={`bi ${showPassword ? 'bi-eye-slash' : 'bi-eye'}`}></i>
            </button>
            {errors.password && (
              <div className="invalid-feedback d-block">{errors.password.message}</div>
            )}
          </div>
        </div>

        {/* Remember Me Checkbox */}
        <div className="mb-4 form-check">
          <input
            id="rememberMe"
            type="checkbox"
            className="form-check-input"
            {...register('rememberMe')}
          />
          <label className="form-check-label text-muted fs-7" htmlFor="rememberMe">
            Remember this device for 30 days
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="btn btn-primary w-100 mb-3 d-flex align-items-center justify-content-center"
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <span
                className="spinner-border spinner-border-sm me-2"
                role="status"
                aria-hidden="true"
              ></span>
              Signing in...
            </>
          ) : (
            <>
              Sign In <i className="bi bi-arrow-right ms-2"></i>
            </>
          )}
        </button>

        {/* Link to Register */}
        <div className="text-center">
          <span className="text-muted me-1 fs-7">Don't have an account?</span>
          <Link to="/register" className="auth-link fs-7">
            Create account
          </Link>
        </div>
      </form>
    </div>
  );
};

export default LoginPage;
