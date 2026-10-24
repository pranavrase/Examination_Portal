import React from 'react';

/**
 * Footer Component
 * Compact, responsive application footer displaying copyright and system information.
 */
const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="footer bg-white border-top py-3 px-4 mt-auto shadow-sm">
      <div className="container-fluid">
        <div className="d-flex flex-column flex-sm-row justify-content-between align-items-center gap-2 small text-muted">
          <div>
            <span className="fw-semibold text-dark">Aptitude & Coding Examination Portal</span>
            <span className="mx-2 d-none d-sm-inline">·</span>
            <span className="d-block d-sm-inline mt-1 mt-sm-0">
              &copy; {currentYear} All Rights Reserved.
            </span>
          </div>
          <div className="d-flex align-items-center gap-3">
            <span className="badge bg-light text-secondary border font-monospace" style={{ fontSize: '0.7rem' }}>
              v1.14.0
            </span>
            <span className="text-success small d-flex align-items-center gap-1">
              <i className="bi bi-shield-check" />
              Secure Session
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
