import React, { useState } from 'react';

const CreateExaminerModal = ({ isOpen, onClose, onSave, loading, error }) => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [validationError, setValidationError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');

    if (!fullName.trim() || fullName.trim().length < 2) {
      setValidationError('Full Name must be at least 2 characters.');
      return;
    }

    if (!email.trim() || !/\S+@\S+\.\S+/.test(email.trim())) {
      setValidationError('Please provide a valid email address.');
      return;
    }

    if (!password || password.length < 6) {
      setValidationError('Password must be at least 6 characters.');
      return;
    }

    try {
      await onSave({
        full_name: fullName.trim(),
        email: email.trim(),
        password: password,
      });
      // Reset form
      setFullName('');
      setEmail('');
      setPassword('');
      setValidationError('');
    } catch (err) {
      // Handled by parent error state
    }
  };

  const handleClose = () => {
    if (!loading) {
      setFullName('');
      setEmail('');
      setPassword('');
      setValidationError('');
      onClose();
    }
  };

  return (
    <div
      className="modal fade show d-block"
      tabIndex="-1"
      role="dialog"
      aria-labelledby="createExaminerModalTitle"
      aria-modal="true"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
    >
      <div className="modal-dialog modal-dialog-centered" role="document">
        <div className="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
          <div className="modal-header bg-dark text-white border-secondary border-opacity-25 px-4 py-3">
            <h5 className="modal-title fw-bold fs-6 d-flex align-items-center gap-2" id="createExaminerModalTitle">
              <i className="bi bi-person-plus-fill text-warning"></i> Provision Examiner Account
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              aria-label="Close modal"
              onClick={handleClose}
              disabled={loading}
            ></button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="modal-body p-4">
              {error && (
                <div className="alert alert-danger border-0 rounded-3 mb-3 d-flex align-items-start">
                  <i className="bi bi-exclamation-octagon-fill me-2 mt-1 fs-5"></i>
                  <div>{error}</div>
                </div>
              )}

              {validationError && (
                <div className="alert alert-warning border-0 rounded-3 mb-3">
                  <i className="bi bi-exclamation-triangle-fill me-2"></i>
                  {validationError}
                </div>
              )}

              <p className="text-muted fs-7 mb-3">
                Create an official Examiner account. The examiner will receive privileges to create, configure, and evaluate exams and questions.
              </p>

              {/* Full Name */}
              <div className="mb-3">
                <label className="form-label fw-semibold text-dark fs-7" htmlFor="examinerFullName">
                  Full Name <span className="text-danger">*</span>
                </label>
                <div className="input-group">
                  <span className="input-group-text bg-light border-end-0">
                    <i className="bi bi-person text-muted"></i>
                  </span>
                  <input
                    id="examinerFullName"
                    type="text"
                    className="form-control border-start-0"
                    placeholder="e.g. Dr. Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Email */}
              <div className="mb-3">
                <label className="form-label fw-semibold text-dark fs-7" htmlFor="examinerEmail">
                  Email Address <span className="text-danger">*</span>
                </label>
                <div className="input-group">
                  <span className="input-group-text bg-light border-end-0">
                    <i className="bi bi-envelope text-muted"></i>
                  </span>
                  <input
                    id="examinerEmail"
                    type="email"
                    className="form-control border-start-0"
                    placeholder="e.g. examiner@institution.edu"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Password */}
              <div className="mb-3">
                <label className="form-label fw-semibold text-dark fs-7" htmlFor="examinerPassword">
                  Initial Password <span className="text-danger">*</span>
                </label>
                <div className="input-group">
                  <span className="input-group-text bg-light border-end-0">
                    <i className="bi bi-key text-muted"></i>
                  </span>
                  <input
                    id="examinerPassword"
                    type="password"
                    className="form-control border-start-0"
                    placeholder="Minimum 6 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={loading}
                  />
                </div>
                <div className="form-text fs-8 text-muted">
                  Share these credentials securely with the designated examiner.
                </div>
              </div>
            </div>

            <div className="modal-footer bg-light px-4 py-3 border-0">
              <button
                type="button"
                className="btn btn-outline-secondary rounded-3 px-3"
                onClick={handleClose}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-warning text-dark fw-semibold rounded-3 px-4 d-flex align-items-center gap-2"
                disabled={loading}
              >
                {loading && (
                  <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                )}
                <span>{loading ? 'Creating...' : 'Create Examiner'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CreateExaminerModal;
