import React from 'react';
import { Outlet } from 'react-router-dom';

const AuthLayout = () => {
  return (
    <div className="auth-wrapper">
      <div className="auth-container">
        <div className="auth-card-wrapper">
          <div className="row g-0">
            {/* Left Brand Panel */}
            <div className="col-lg-5 auth-brand-side d-none d-lg-flex">
              <div>
                <div className="auth-brand-badge mb-4">
                  <i className="bi bi-shield-check"></i> Secure Assessment Portal
                </div>
                <h2 className="display-6 fw-bold mb-3">ExamPortal</h2>
                <p className="lead opacity-90 mb-4 fs-6">
                  Next-generation Aptitude, Logical Reasoning, and Coding Examination Platform.
                </p>

                <ul className="auth-feature-list">
                  <li className="auth-feature-item">
                    <div className="auth-feature-icon">
                      <i className="bi bi-cpu"></i>
                    </div>
                    <span>Automated Live Code Execution</span>
                  </li>
                  <li className="auth-feature-item">
                    <div className="auth-feature-icon">
                      <i className="bi bi-lightning"></i>
                    </div>
                    <span>Real-time Aptitude & Reasoning Tests</span>
                  </li>
                  <li className="auth-feature-item">
                    <div className="auth-feature-icon">
                      <i className="bi bi-lock-fill"></i>
                    </div>
                    <span>Enterprise Role-Based Security</span>
                  </li>
                </ul>
              </div>

              <div className="pt-4 border-top border-white border-opacity-10 fs-7 opacity-75">
                © {new Date().getFullYear()} ExamPortal. All rights reserved.
              </div>
            </div>

            {/* Right Form Content Panel */}
            <div className="col-lg-7 auth-form-side">
              <Outlet />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
