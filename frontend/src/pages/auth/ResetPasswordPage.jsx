import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { resetPassword } from '../../api/authApi';
import AuthFormError from '../../components/auth/AuthFormError';

const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [apiError, setApiError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      newPassword: '',
      confirmPassword: '',
    },
  });

  const newPasswordValue = watch('newPassword');

  const onSubmit = async (data) => {
    setApiError(null);
    setSuccessMessage(null);

    if (!token) {
      setApiError('Invalid or missing password reset token. Please request a new link.');
      return;
    }

    try {
      const response = await resetPassword({
        token,
        new_password: data.newPassword,
      });

      setSuccessMessage(
        response?.message || 'Password reset successfully! Redirecting to login...'
      );

      setTimeout(() => {
        navigate('/login', {
          state: { message: 'Password reset successfully. Please sign in.' },
        });
      }, 2500);
    } catch (err) {
      setApiError(err);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <h3 className="fw-bold text-dark mb-1">Set New Password</h3>
        <p className="text-muted">Enter your new password below to update your account</p>
      </div>

      {!token && (
        <div className="alert alert-warning border-0 shadow-sm rounded-3 my-3">
          <i className="bi bi-exclamation-triangle me-2"></i>
          Reset token is missing from the link. Please check your email or request a new reset link.
        </div>
      )}

      <AuthFormError error={apiError} onClose={() => setApiError(null)} />

      {successMessage && (
        <div
          className="alert alert-success d-flex align-items-center shadow-sm border-0 rounded-3 my-3"
          role="alert"
        >
          <i className="bi bi-check-circle-fill flex-shrink-0 me-2 fs-5"></i>
          <div>{successMessage}</div>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {/* New Password Field */}
        <div className="mb-3">
          <label className="form-label" htmlFor="newPassword">
            New Password
          </label>
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-key"></i>
            </span>
            <input
              id="newPassword"
              type={showPassword ? 'text' : 'password'}
              className={`form-control password-input-has-toggle ${
                errors.newPassword ? 'is-invalid' : ''
              }`}
              placeholder="Minimum 6 characters"
              autoComplete="new-password"
              {...register('newPassword', {
                required: 'New password is required',
                minLength: {
                  value: 6,
                  message: 'Password must be at least 6 characters long',
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
            {errors.newPassword && (
              <div className="invalid-feedback d-block">
                {errors.newPassword.message}
              </div>
            )}
          </div>
        </div>

        {/* Confirm New Password Field */}
        <div className="mb-4">
          <label className="form-label" htmlFor="confirmPassword">
            Confirm New Password
          </label>
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-check-circle"></i>
            </span>
            <input
              id="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              className={`form-control password-input-has-toggle ${
                errors.confirmPassword ? 'is-invalid' : ''
              }`}
              placeholder="Re-enter new password"
              autoComplete="new-password"
              {...register('confirmPassword', {
                required: 'Please confirm your new password',
                validate: (value) =>
                  value === newPasswordValue || 'Passwords do not match',
              })}
            />
            <button
              type="button"
              className="btn password-toggle-btn"
              aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
            >
              <i
                className={`bi ${
                  showConfirmPassword ? 'bi-eye-slash' : 'bi-eye'
                }`}
              ></i>
            </button>
            {errors.confirmPassword && (
              <div className="invalid-feedback d-block">
                {errors.confirmPassword.message}
              </div>
            )}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="btn btn-primary w-100 mb-3 d-flex align-items-center justify-content-center"
          disabled={isSubmitting || !token}
        >
          {isSubmitting ? (
            <>
              <span
                className="spinner-border spinner-border-sm me-2"
                role="status"
                aria-hidden="true"
              ></span>
              Resetting Password...
            </>
          ) : (
            <>
              Reset Password <i className="bi bi-arrow-right ms-2"></i>
            </>
          )}
        </button>

        {/* Link back to login */}
        <div className="text-center">
          <Link to="/login" className="auth-link fs-7 d-inline-flex align-items-center">
            <i className="bi bi-arrow-left me-1"></i> Back to Sign In
          </Link>
        </div>
      </form>
    </div>
  );
};

export default ResetPasswordPage;
