import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import AuthFormError from '../../components/auth/AuthFormError';
import { EMAIL_REGEX } from '../../utils/validators';

const RegisterPage = () => {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [apiError, setApiError] = useState(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      fullName: '',
      email: '',
      password: '',
      confirmPassword: '',
      role: 'student',
    },
  });

  const passwordValue = watch('password');

  const onSubmit = async (data) => {
    setApiError(null);
    try {
      await registerUser({
        full_name: data.fullName.trim(),
        email: data.email.trim(),
        password: data.password,
        role: data.role,
      });

      // Navigate to login page with registration success indicator
      navigate('/login', {
        state: { message: 'Account created successfully! Please sign in.' },
      });
    } catch (err) {
      setApiError(err);
    }
  };

  return (
    <div>
      <div className="mb-4">
        <h3 className="fw-bold text-dark mb-1">Create Account</h3>
        <p className="text-muted">Register to start taking tests or managing examinations</p>
      </div>

      <AuthFormError error={apiError} onClose={() => setApiError(null)} />

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        {/* Full Name Field */}
        <div className="mb-3">
          <label className="form-label" htmlFor="fullName">
            Full Name
          </label>
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-person"></i>
            </span>
            <input
              id="fullName"
              type="text"
              className={`form-control ${errors.fullName ? 'is-invalid' : ''}`}
              placeholder="John Doe"
              {...register('fullName', {
                required: 'Full name is required',
                minLength: {
                  value: 2,
                  message: 'Name must be at least 2 characters',
                },
              })}
            />
            {errors.fullName && (
              <div className="invalid-feedback">{errors.fullName.message}</div>
            )}
          </div>
        </div>

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

        {/* Role Selection Field */}
        <div className="mb-3">
          <label className="form-label" htmlFor="role">
            Account Role
          </label>
          <div className="input-group">
            <span className="input-group-text">
              <i className="bi bi-person-badge"></i>
            </span>
            <select
              id="role"
              className={`form-select ${errors.role ? 'is-invalid' : ''}`}
              {...register('role', { required: 'Please select a role' })}
            >
              <option value="student">Student / Candidate</option>
            </select>
            {errors.role && (
              <div className="invalid-feedback">{errors.role.message}</div>
            )}
          </div>
          <small className="form-text text-muted">
            Examiner and Admin accounts must be provisioned internally by an administrator.
          </small>
        </div>

        {/* Password Field */}
        <div className="mb-3">
          <label className="form-label" htmlFor="password">
            Password
          </label>
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
              placeholder="Minimum 6 characters"
              autoComplete="new-password"
              {...register('password', {
                required: 'Password is required',
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
            {errors.password && (
              <div className="invalid-feedback d-block">{errors.password.message}</div>
            )}
          </div>
        </div>

        {/* Confirm Password Field */}
        <div className="mb-4">
          <label className="form-label" htmlFor="confirmPassword">
            Confirm Password
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
              placeholder="Re-enter password"
              autoComplete="new-password"
              {...register('confirmPassword', {
                required: 'Please confirm your password',
                validate: (value) =>
                  value === passwordValue || 'Passwords do not match',
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
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <span
                className="spinner-border spinner-border-sm me-2"
                role="status"
                aria-hidden="true"
              ></span>
              Creating Account...
            </>
          ) : (
            <>
              Register Account <i className="bi bi-arrow-right ms-2"></i>
            </>
          )}
        </button>

        {/* Link to Login */}
        <div className="text-center">
          <span className="text-muted me-1 fs-7">Already have an account?</span>
          <Link to="/login" className="auth-link fs-7">
            Sign in
          </Link>
        </div>
      </form>
    </div>
  );
};

export default RegisterPage;
