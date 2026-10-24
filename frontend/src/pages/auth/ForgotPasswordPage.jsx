import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { requestOTP, verifyOTP, resetPasswordWithOTP } from '../../api/authApi';
import AuthFormError from '../../components/auth/AuthFormError';
import { EMAIL_REGEX } from '../../utils/validators';

const ForgotPasswordPage = () => {
  const [step, setStep] = useState('email'); // 'email', 'otp', 'reset'
  const [email, setEmail] = useState('');
  const [apiError, setApiError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const [otpCountdown, setOtpCountdown] = useState(0);
  const [canResend, setCanResend] = useState(false);
  const navigate = useNavigate();

  const {
    register: registerEmail,
    handleSubmit: handleSubmitEmail,
    formState: { errors: emailErrors, isSubmitting: isSubmittingEmail },
  } = useForm({
    defaultValues: { email: '' },
  });

  const {
    register: registerOTP,
    handleSubmit: handleSubmitOTP,
    formState: { errors: otpErrors, isSubmitting: isSubmittingOTP },
  } = useForm({
    defaultValues: { otp: '' },
  });

  const {
    register: registerReset,
    handleSubmit: handleSubmitReset,
    watch,
    formState: { errors: resetErrors, isSubmitting: isSubmittingReset },
  } = useForm({
    defaultValues: { newPassword: '', confirmPassword: '' },
  });

  const newPasswordValue = watch('newPassword');

  useEffect(() => {
    let interval;
    if (otpCountdown > 0) {
      interval = setInterval(() => {
        setOtpCountdown((prev) => {
          if (prev <= 1) {
            setCanResend(true);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [otpCountdown]);

  const onEmailSubmit = async (data) => {
    setApiError(null);
    setSuccessMessage(null);
    try {
      const response = await requestOTP({ email: data.email.trim() });
      setEmail(data.email.trim());
      setSuccessMessage(
        response?.message || 'If an account exists, an OTP has been sent to your email.'
      );
      setStep('otp');
      setOtpCountdown(60);
      setCanResend(false);
    } catch (err) {
      setApiError(err);
    }
  };

  const onOTPSubmit = async (data) => {
    setApiError(null);
    setSuccessMessage(null);
    try {
      const response = await verifyOTP({ email, otp: data.otp });
      setSuccessMessage(response?.message || 'OTP verified successfully');
      setStep('reset');
    } catch (err) {
      setApiError(err);
    }
  };

  const onResendOTP = async () => {
    setApiError(null);
    setSuccessMessage(null);
    try {
      const response = await requestOTP({ email });
      setSuccessMessage(response?.message || 'A new OTP has been sent to your email.');
      setOtpCountdown(60);
      setCanResend(false);
    } catch (err) {
      setApiError(err);
    }
  };

  const onResetSubmit = async (data) => {
    setApiError(null);
    setSuccessMessage(null);
    try {
      const response = await resetPasswordWithOTP({
        email,
        otp: data.otp,
        new_password: data.newPassword,
        confirm_password: data.confirmPassword,
      });
      setSuccessMessage(response?.message || 'Password reset successfully');
      setTimeout(() => {
        navigate('/login', {
          state: { message: 'Password reset successfully. Please sign in.' },
        });
      }, 2000);
    } catch (err) {
      setApiError(err);
    }
  };

  const renderEmailStep = () => (
    <form onSubmit={handleSubmitEmail(onEmailSubmit)} noValidate>
      <div className="mb-4">
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
            className={`form-control ${emailErrors.email ? 'is-invalid' : ''}`}
            placeholder="name@example.com"
            autoComplete="email"
            {...registerEmail('email', {
              required: 'Email address is required',
              pattern: {
                value: EMAIL_REGEX,
                message: 'Please enter a valid email address',
              },
            })}
          />
          {emailErrors.email && (
            <div className="invalid-feedback">{emailErrors.email.message}</div>
          )}
        </div>
      </div>

      <button
        type="submit"
        className="btn btn-primary w-100 mb-3 d-flex align-items-center justify-content-center"
        disabled={isSubmittingEmail}
      >
        {isSubmittingEmail ? (
          <>
            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Sending OTP...
          </>
        ) : (
          <>
            Send OTP <i className="bi bi-arrow-right ms-2"></i>
          </>
        )}
      </button>

      <div className="text-center">
        <Link to="/login" className="auth-link fs-7 d-inline-flex align-items-center">
          <i className="bi bi-arrow-left me-1"></i> Back to Sign In
        </Link>
      </div>
    </form>
  );

  const renderOTPStep = () => (
    <form onSubmit={handleSubmitOTP(onOTPSubmit)} noValidate>
      <div className="mb-3">
        <label className="form-label" htmlFor="otp">
          Enter 6-Digit OTP
        </label>
        <div className="input-group">
          <span className="input-group-text">
            <i className="bi bi-shield-lock"></i>
          </span>
          <input
            id="otp"
            type="text"
            inputMode="numeric"
            maxLength="6"
            className={`form-control ${otpErrors.otp ? 'is-invalid' : ''}`}
            placeholder="123456"
            autoComplete="one-time-code"
            {...registerOTP('otp', {
              required: 'OTP is required',
              pattern: {
                value: /^\d{6}$/,
                message: 'Please enter a valid 6-digit OTP',
              },
            })}
          />
          {otpErrors.otp && (
            <div className="invalid-feedback">{otpErrors.otp.message}</div>
          )}
        </div>
      </div>

      <div className="mb-4">
        <small className="text-muted">
          OTP sent to <strong>{email}</strong>
        </small>
      </div>

      <button
        type="submit"
        className="btn btn-primary w-100 mb-3 d-flex align-items-center justify-content-center"
        disabled={isSubmittingOTP}
      >
        {isSubmittingOTP ? (
          <>
            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Verifying OTP...
          </>
        ) : (
          <>
            Verify OTP <i className="bi bi-arrow-right ms-2"></i>
          </>
        )}
      </button>

      <div className="text-center mb-3">
        <button
          type="button"
          className="btn btn-link p-0 text-decoration-none"
          onClick={onResendOTP}
          disabled={!canResend || isSubmittingOTP}
        >
          {canResend ? (
            <span className="text-primary">Resend OTP</span>
          ) : (
            <span className="text-muted">
              Resend OTP in {otpCountdown}s
            </span>
          )}
        </button>
      </div>

      <div className="text-center">
        <button
          type="button"
          className="btn btn-link p-0 auth-link fs-7 d-inline-flex align-items-center"
          onClick={() => setStep('email')}
        >
          <i className="bi bi-arrow-left me-1"></i> Change Email
        </button>
      </div>
    </form>
  );

  const renderResetStep = () => (
    <form onSubmit={handleSubmitReset(onResetSubmit)} noValidate>
      <div className="mb-3">
        <label className="form-label" htmlFor="resetOtp">
          Verify OTP
        </label>
        <div className="input-group">
          <span className="input-group-text">
            <i className="bi bi-shield-lock"></i>
          </span>
          <input
            id="resetOtp"
            type="text"
            inputMode="numeric"
            maxLength="6"
            className={`form-control ${resetErrors.otp ? 'is-invalid' : ''}`}
            placeholder="Enter the OTP from your email"
            autoComplete="one-time-code"
            {...registerReset('otp', {
              required: 'OTP is required',
              pattern: {
                value: /^\d{6}$/,
                message: 'Please enter a valid 6-digit OTP',
              },
            })}
          />
          {resetErrors.otp && (
            <div className="invalid-feedback">{resetErrors.otp.message}</div>
          )}
        </div>
      </div>

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
            type="password"
            className={`form-control ${resetErrors.newPassword ? 'is-invalid' : ''}`}
            placeholder="Minimum 8 characters"
            autoComplete="new-password"
            {...registerReset('newPassword', {
              required: 'New password is required',
              minLength: {
                value: 8,
                message: 'Password must be at least 8 characters long',
              },
            })}
          />
          {resetErrors.newPassword && (
            <div className="invalid-feedback">{resetErrors.newPassword.message}</div>
          )}
        </div>
      </div>

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
            type="password"
            className={`form-control ${resetErrors.confirmPassword ? 'is-invalid' : ''}`}
            placeholder="Re-enter new password"
            autoComplete="new-password"
            {...registerReset('confirmPassword', {
              required: 'Please confirm your new password',
              validate: (value) =>
                value === newPasswordValue || 'Passwords do not match',
            })}
          />
          {resetErrors.confirmPassword && (
            <div className="invalid-feedback">{resetErrors.confirmPassword.message}</div>
          )}
        </div>
      </div>

      <button
        type="submit"
        className="btn btn-primary w-100 mb-3 d-flex align-items-center justify-content-center"
        disabled={isSubmittingReset}
      >
        {isSubmittingReset ? (
          <>
            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            Resetting Password...
          </>
        ) : (
          <>
            Reset Password <i className="bi bi-arrow-right ms-2"></i>
          </>
        )}
      </button>

      <div className="text-center">
        <button
          type="button"
          className="btn btn-link p-0 auth-link fs-7 d-inline-flex align-items-center"
          onClick={() => setStep('otp')}
        >
          <i className="bi bi-arrow-left me-1"></i> Back to OTP
        </button>
      </div>
    </form>
  );

  return (
    <div>
      <div className="mb-4">
        <h3 className="fw-bold text-dark mb-1">Forgot Password</h3>
        {step === 'email' && (
          <p className="text-muted">
            Enter your registered email address to receive a password reset OTP.
          </p>
        )}
        {step === 'otp' && (
          <p className="text-muted">
            Enter the 6-digit OTP sent to your email address.
          </p>
        )}
        {step === 'reset' && (
          <p className="text-muted">
            Create a new password for your account.
          </p>
        )}
      </div>

      <AuthFormError error={apiError} onClose={() => setApiError(null)} />

      {successMessage && (
        <div
          className="alert alert-success d-flex align-items-start shadow-sm border-0 rounded-3 my-3"
          role="alert"
        >
          <i className="bi bi-check-circle-fill flex-shrink-0 me-2 mt-1 fs-5"></i>
          <div className="flex-grow-1 fs-6">{successMessage}</div>
        </div>
      )}

      {step === 'email' && renderEmailStep()}
      {step === 'otp' && renderOTPStep()}
      {step === 'reset' && renderResetStep()}
    </div>
  );
};

export default ForgotPasswordPage;
