import React, { useState, useEffect } from 'react';

const RoleAssignmentModal = ({ user, isOpen, onClose, onSave, loading, error }) => {
  const [selectedRole, setSelectedRole] = useState('student');
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    if (user) {
      setSelectedRole(user.role || 'student');
      setValidationError('');
    }
  }, [user]);

  if (!isOpen || !user) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!selectedRole) {
      setValidationError('Please select a valid role');
      return;
    }
    onSave(user.id || user._id, selectedRole);
  };

  return (
    <div
      className="modal fade show d-block"
      tabIndex="-1"
      role="dialog"
      aria-labelledby="roleModalTitle"
      aria-modal="true"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
    >
      <div className="modal-dialog modal-dialog-centered" role="document">
        <div className="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
          <div className="modal-header bg-dark text-white border-secondary border-opacity-25 px-4 py-3">
            <h5 className="modal-title fw-bold fs-6 d-flex align-items-center gap-2" id="roleModalTitle">
              <i className="bi bi-person-badge-fill text-primary"></i> Change User Role
            </h5>
            <button
              type="button"
              className="btn-close btn-close-white"
              aria-label="Close modal"
              onClick={onClose}
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
                  {validationError}
                </div>
              )}

              <div className="card bg-light border-0 rounded-3 p-3 mb-3">
                <div className="row g-2">
                  <div className="col-12">
                    <span className="text-muted fs-7">User Full Name:</span>
                    <p className="fw-semibold text-dark mb-0">{user.full_name || user.name || 'N/A'}</p>
                  </div>
                  <div className="col-12">
                    <span className="text-muted fs-7">Email Address:</span>
                    <p className="fw-semibold text-dark mb-0">{user.email}</p>
                  </div>
                  <div className="col-12">
                    <span className="text-muted fs-7">Current Role:</span>
                    <div>
                      <span className="badge bg-secondary text-uppercase">{user.role}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mb-3">
                <label className="form-label fw-semibold" htmlFor="roleSelect">
                  Select New Role
                </label>
                <select
                  id="roleSelect"
                  className="form-select rounded-3 py-2"
                  value={selectedRole}
                  onChange={(e) => setSelectedRole(e.target.value)}
                  disabled={loading}
                >
                  <option value="student">Student / Candidate</option>
                  <option value="examiner">Examiner / Question Creator</option>
                  <option value="admin">System Administrator</option>
                </select>
                <small className="form-text text-muted mt-1 d-block">
                  Updating role will immediately modify system permissions for this user on next API call.
                </small>
              </div>
            </div>

            <div className="modal-footer bg-light px-4 py-3 border-top border-light">
              <button
                type="button"
                className="btn btn-outline-secondary rounded-3 px-3"
                onClick={onClose}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary rounded-3 px-4 d-flex align-items-center gap-2"
                disabled={loading || selectedRole === user.role}
              >
                {loading ? (
                  <>
                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                    Updating...
                  </>
                ) : (
                  <>
                    <i className="bi bi-check-lg"></i> Save Role
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default RoleAssignmentModal;
