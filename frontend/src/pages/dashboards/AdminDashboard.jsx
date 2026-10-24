import React from 'react';
import { useAuth } from '../../context/AuthContext';

const AdminDashboard = () => {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard-container">
      <div className="container py-4">
        <header className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
          <div>
            <span className="badge bg-danger mb-2">ADMIN PORTAL</span>
            <h1 className="h3 mb-0 fw-bold">Admin Management Dashboard</h1>
            <p className="text-muted mb-0">Manage system settings, users, and overall exam system health</p>
          </div>
          <button className="btn btn-outline-danger d-flex align-items-center gap-2" onClick={logout}>
            <i className="bi bi-box-arrow-right"></i> Sign Out
          </button>
        </header>

        <div className="row g-4">
          <div className="col-md-4">
            <div className="card border-0 shadow-sm rounded-4 p-3">
              <div className="d-flex align-items-center gap-3">
                <div className="p-3 bg-danger bg-opacity-10 text-danger rounded-3 fs-3">
                  <i className="bi bi-people-fill"></i>
                </div>
                <div>
                  <h6 className="text-muted mb-1">Authenticated User</h6>
                  <h5 className="mb-0 fw-bold">{user?.full_name || user?.email || 'Administrator'}</h5>
                  <small className="text-secondary">{user?.email}</small>
                </div>
              </div>
            </div>
          </div>

          <div className="col-md-8">
            <div className="card border-0 shadow-sm rounded-4 p-4">
              <h5 className="fw-bold mb-3">Admin Portal System Status</h5>
              <div className="alert alert-info border-0 rounded-3">
                <i className="bi bi-info-circle me-2"></i>
                Module 1.1 Authentication & RBAC integration successful. This page is protected for <strong>admin</strong> users only.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
