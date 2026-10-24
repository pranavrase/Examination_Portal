import React from 'react';
import { useAuth } from '../../context/AuthContext';

const StudentDashboard = () => {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard-container">
      <div className="container py-4">
        <header className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
          <div>
            <span className="badge bg-primary mb-2">STUDENT PORTAL</span>
            <h1 className="h3 mb-0 fw-bold">Candidate Assessment Hub</h1>
            <p className="text-muted mb-0">Access scheduled tests, practice coding challenges, and view results</p>
          </div>
          <button className="btn btn-outline-danger d-flex align-items-center gap-2" onClick={logout}>
            <i className="bi bi-box-arrow-right"></i> Sign Out
          </button>
        </header>

        <div className="row g-4">
          <div className="col-md-4">
            <div className="card border-0 shadow-sm rounded-4 p-3">
              <div className="d-flex align-items-center gap-3">
                <div className="p-3 bg-primary bg-opacity-10 text-primary rounded-3 fs-3">
                  <i className="bi bi-mortarboard-fill"></i>
                </div>
                <div>
                  <h6 className="text-muted mb-1">Candidate Profile</h6>
                  <h5 className="mb-0 fw-bold">{user?.full_name || user?.email || 'Student'}</h5>
                  <small className="text-secondary">{user?.email}</small>
                </div>
              </div>
            </div>
          </div>

          <div className="col-md-8">
            <div className="card border-0 shadow-sm rounded-4 p-4">
              <h5 className="fw-bold mb-3">Scheduled Examinations</h5>
              <div className="alert alert-success border-0 rounded-3">
                <i className="bi bi-check-circle me-2"></i>
                Module 1.1 Authentication & RBAC integration successful. This page is protected for <strong>student</strong> candidates.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;
