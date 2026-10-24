import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * NotFoundPage Component
 * Professional 404 page redirecting users safely back to their role-appropriate dashboard.
 */
const NotFoundPage = () => {
  const navigate = useNavigate();
  const { isAuthenticated, role } = useAuth();

  const getDashboardPath = () => {
    if (!isAuthenticated) return '/login';
    switch (role?.toLowerCase()) {
      case 'admin':
        return '/admin';
      case 'examiner':
        return '/examiner';
      case 'student':
        return '/student';
      default:
        return '/';
    }
  };

  const handleGoDashboard = () => {
    navigate(getDashboardPath());
  };

  return (
    <div className="bg-light min-vh-100 d-flex align-items-center justify-content-center p-4">
      <div className="card border-0 shadow-lg rounded-4 text-center p-5 overflow-hidden" style={{ maxWidth: 520 }}>
        {/* Accent Bar */}
        <div style={{ height: 6, position: 'absolute', top: 0, left: 0, right: 0, background: 'linear-gradient(90deg, #ef4444, #f59e0b, #6366f1)' }} />

        <div className="mb-4 text-danger opacity-75">
          <i className="bi bi-exclamation-octagon-fill" style={{ fontSize: '4.5rem' }} />
        </div>

        <h1 className="display-1 fw-bold text-dark mb-0" style={{ letterSpacing: '-0.04em' }}>
          404
        </h1>

        <h3 className="fw-bold text-secondary mb-3">Page Not Found</h3>

        <p className="text-muted mb-4 fs-6">
          The page you're looking for doesn't exist, has been removed, or you may not have authorization to view it.
        </p>

        <div className="d-flex flex-wrap gap-2 justify-content-center">
          <button
            id="not-found-dashboard-btn"
            onClick={handleGoDashboard}
            className="btn btn-primary rounded-3 px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2"
          >
            <i className="bi bi-house-door-fill" />
            Go to Dashboard
          </button>
          <button
            onClick={() => navigate(-1)}
            className="btn btn-outline-secondary rounded-3 px-4 py-2 fw-semibold d-inline-flex align-items-center gap-2"
          >
            <i className="bi bi-arrow-left" />
            Go Back
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
