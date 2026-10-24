import React from 'react';

const Loader = ({ fullScreen = true, text = 'Initializing authentication...' }) => {
  if (fullScreen) {
    return (
      <div className="full-page-loader">
        <div className="spinner-border text-light spinner-custom mb-3" role="status">
          <span className="visually-hidden">Loading...</span>
        </div>
        <p className="fw-medium text-light opacity-75">{text}</p>
      </div>
    );
  }

  return (
    <div className="d-flex align-items-center justify-content-center p-4">
      <div className="spinner-border text-primary me-2" role="status">
        <span className="visually-hidden">Loading...</span>
      </div>
      <span className="text-muted fw-medium">{text}</span>
    </div>
  );
};

export default Loader;
