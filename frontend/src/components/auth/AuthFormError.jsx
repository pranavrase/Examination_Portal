import React from 'react';

const AuthFormError = ({ error, onClose }) => {
  if (!error) return null;

  // Transform raw error objects or strings into human-readable text
  const getErrorMessage = (err) => {
    if (typeof err === 'string') return err;
    if (err?.response?.data?.detail) {
      const detail = err.response.data.detail;
      if (typeof detail === 'string') return detail;
      if (Array.isArray(detail)) {
        return detail.map((item) => item.msg || JSON.stringify(item)).join(', ');
      }
    }
    if (err?.response?.data?.message) return err.response.data.message;
    if (err?.message) return err.message;
    return 'An unexpected error occurred. Please try again.';
  };

  const message = getErrorMessage(error);

  return (
    <div className="alert alert-danger alert-dismissible fade show d-flex align-items-start shadow-sm border-0 rounded-3 my-3" role="alert">
      <i className="bi bi-exclamation-triangle-fill flex-shrink-0 me-2 mt-1 fs-5"></i>
      <div className="flex-grow-1 fs-6">{message}</div>
      {onClose && (
        <button
          type="button"
          className="btn-close"
          data-bs-dismiss="alert"
          aria-label="Close"
          onClick={onClose}
        ></button>
      )}
    </div>
  );
};

export default AuthFormError;
