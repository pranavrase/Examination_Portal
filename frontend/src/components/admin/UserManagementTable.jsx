import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';

const UserManagementTable = ({
  users = [],
  loading,
  error,
  onOpenRoleModal,
  onDeactivateUser,
  onOpenCreateExaminer,
  onDeleteExaminer,
  onSearchChange,
  onFilterChange,
  onRetry,
}) => {
  const { user: currentUser } = useAuth();

  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [deactivatingUserId, setDeactivatingUserId] = useState(null);
  const [deletingExaminerId, setDeletingExaminerId] = useState(null);

  // Prevent initial mount from triggering redundant search request
  const isInitialMount = useRef(true);
  const prevSearchTermRef = useRef('');

  // Debounced search trigger (only fires when user actively changes search text)
  useEffect(() => {
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    if (prevSearchTermRef.current === searchTerm) {
      return;
    }
    const handler = setTimeout(() => {
      prevSearchTermRef.current = searchTerm;
      onSearchChange(searchTerm);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm, onSearchChange]);

  const handleRoleFilterChange = (e) => {
    const value = e.target.value;
    setRoleFilter(value);
    onFilterChange(value, statusFilter);
  };

  const handleStatusFilterChange = (e) => {
    const value = e.target.value;
    setStatusFilter(value);
    onFilterChange(roleFilter, value);
  };

  const handleConfirmDeactivate = (userToDeactivate) => {
    const confirmMsg = `Are you sure you want to deactivate ${userToDeactivate.full_name || userToDeactivate.email}? They will no longer be able to log in to the portal.`;
    if (window.confirm(confirmMsg)) {
      setDeactivatingUserId(userToDeactivate.id || userToDeactivate._id);
      onDeactivateUser(userToDeactivate.id || userToDeactivate._id).finally(() => {
        setDeactivatingUserId(null);
      });
    }
  };

  const handleConfirmDeleteExaminer = (examinerUser) => {
    const confirmMsg = `Are you sure you want to permanently delete examiner account "${examinerUser.full_name || examinerUser.email}"? This action cannot be undone.`;
    if (window.confirm(confirmMsg)) {
      setDeletingExaminerId(examinerUser.id || examinerUser._id);
      onDeleteExaminer(examinerUser.id || examinerUser._id).finally(() => {
        setDeletingExaminerId(null);
      });
    }
  };

  const getRoleBadge = (role) => {
    switch (role?.toLowerCase()) {
      case 'admin':
        return <span className="badge bg-danger text-uppercase px-2 py-1">Admin</span>;
      case 'examiner':
        return <span className="badge bg-warning text-dark text-uppercase px-2 py-1">Examiner</span>;
      case 'student':
        return <span className="badge bg-primary text-uppercase px-2 py-1">Student</span>;
      default:
        return <span className="badge bg-secondary text-uppercase px-2 py-1">{role || 'user'}</span>;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="user-management">
      <div className="card-header bg-white border-bottom border-light p-4 rounded-top-4">
        <div className="row g-3 align-items-center justify-content-between">
          <div className="col-12 col-md-5 d-flex align-items-center justify-content-between justify-content-md-start gap-2">
            <h5 className="fw-bold mb-0 text-dark d-flex align-items-center gap-2">
              <i className="bi bi-person-lines-fill text-primary"></i>
              <span>User Management Directory</span>
              {loading && users.length > 0 && (
                <span
                  className="spinner-border spinner-border-sm text-primary ms-2"
                  role="status"
                  aria-label="Updating users..."
                  title="Updating user list in background..."
                ></span>
              )}
            </h5>
            {onOpenCreateExaminer && (
              <button
                className="btn btn-warning text-dark fw-semibold btn-sm rounded-3 d-flex align-items-center gap-1 shadow-sm ms-md-2"
                onClick={onOpenCreateExaminer}
                title="Create a new Examiner account"
              >
                <i className="bi bi-person-plus-fill"></i>
                <span>Create Examiner</span>
              </button>
            )}
          </div>

          {/* Controls: Search & Filters */}
          <div className="col-12 col-md-7">
            <div className="row g-2">
              {/* Search Bar */}
              <div className="col-12 col-sm-6">
                <div className="input-group">
                  <span className="input-group-text bg-light border-end-0 text-muted">
                    <i className="bi bi-search"></i>
                  </span>
                  <input
                    type="text"
                    className="form-control bg-light border-start-0 ps-0"
                    placeholder="Search name or email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
              </div>

              {/* Role Filter */}
              <div className="col-6 col-sm-3">
                <select
                  className="form-select bg-light"
                  value={roleFilter}
                  onChange={handleRoleFilterChange}
                >
                  <option value="all">All Roles</option>
                  <option value="student">Student</option>
                  <option value="examiner">Examiner</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              {/* Status Filter */}
              <div className="col-6 col-sm-3">
                <select
                  className="form-select bg-light"
                  value={statusFilter}
                  onChange={handleStatusFilterChange}
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error alert with Retry button */}
      {error && (
        <div className="px-4 pt-3">
          <div className="alert alert-danger border-0 rounded-3 mb-0 d-flex align-items-center justify-content-between">
            <div className="d-flex align-items-center">
              <i className="bi bi-exclamation-triangle-fill me-2 fs-5"></i>
              <span>{error || 'Unable to load users. Please try again.'}</span>
            </div>
            {onRetry && (
              <button
                type="button"
                className="btn btn-outline-danger btn-sm rounded-pill px-3 ms-3 d-flex align-items-center gap-1"
                onClick={onRetry}
                disabled={loading}
              >
                <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                <span>Retry</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Table Body */}
      <div className="card-body p-0">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted fs-7 text-uppercase tracking-wider">
              <tr>
                <th className="ps-4">User ID</th>
                <th>Full Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Joined Date</th>
                <th className="pe-4 text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {/* Show skeleton placeholders ONLY on initial load before any users exist */}
              {loading && users.length === 0 ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx}>
                    <td className="ps-4">
                      <span className="placeholder col-8 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-10 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-10 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-6 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-6 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-8 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td className="pe-4 text-end">
                      <span className="placeholder col-6 bg-secondary opacity-25 rounded"></span>
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-5 text-muted">
                    <i className="bi bi-people fs-1 d-block mb-2 text-secondary opacity-50"></i>
                    No registered users match the search criteria.
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const uid = u.id || u._id;
                  const isCurrentAdmin = currentUser?.email === u.email || currentUser?.id === uid;
                  const isActive = u.is_active !== false && u.status !== 'inactive';

                  return (
                    <tr key={uid || u.email}>
                      <td className="ps-4 fw-mono fs-7 text-muted">
                        {uid ? `#${String(uid).slice(-6)}` : 'N/A'}
                      </td>
                      <td>
                        <div className="fw-semibold text-dark">{u.full_name || u.name || 'N/A'}</div>
                      </td>
                      <td className="text-muted fs-7">{u.email}</td>
                      <td>{getRoleBadge(u.role)}</td>
                      <td>
                        {isActive ? (
                          <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2.5 py-1">
                            <i className="bi bi-circle-fill fs-8 me-1"></i> Active
                          </span>
                        ) : (
                          <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-2.5 py-1">
                            <i className="bi bi-dash-circle-fill fs-8 me-1"></i> Inactive
                          </span>
                        )}
                      </td>
                      <td className="text-muted fs-7">{formatDate(u.created_at || u.createdAt)}</td>
                      <td className="pe-4 text-end">
                        <div className="d-inline-flex gap-2">
                          <button
                            className="btn btn-outline-primary btn-sm rounded-3 d-flex align-items-center gap-1"
                            onClick={() => onOpenRoleModal(u)}
                            title="Change User Role"
                          >
                            <i className="bi bi-pencil-square"></i>
                            <span className="d-none d-xl-inline">Role</span>
                          </button>

                          {/* Delete Examiner button (Admin only, Examiner accounts only) */}
                          {u.role === 'examiner' && onDeleteExaminer && (
                            <button
                              className="btn btn-outline-danger btn-sm rounded-3 d-flex align-items-center gap-1"
                              onClick={() => handleConfirmDeleteExaminer(u)}
                              disabled={deletingExaminerId === uid}
                              title="Permanently Delete Examiner Account"
                            >
                              {deletingExaminerId === uid ? (
                                <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                              ) : (
                                <i className="bi bi-trash"></i>
                              )}
                              <span className="d-none d-xl-inline">Delete</span>
                            </button>
                          )}

                          <button
                            className="btn btn-outline-secondary btn-sm rounded-3 d-flex align-items-center gap-1"
                            onClick={() => handleConfirmDeactivate(u)}
                            disabled={isCurrentAdmin || !isActive || deactivatingUserId === uid}
                            title={isCurrentAdmin ? 'You cannot deactivate your own active admin account' : 'Deactivate User'}
                          >
                            {deactivatingUserId === uid ? (
                              <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                            ) : (
                              <i className="bi bi-person-x"></i>
                            )}
                            <span className="d-none d-xl-inline">Deactivate</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default UserManagementTable;
