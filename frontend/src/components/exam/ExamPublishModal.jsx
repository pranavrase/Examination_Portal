import React, { useState } from 'react';
import { useExam } from '../../context/ExamContext';

const ExamPublishModal = ({ show, onClose }) => {
  const { currentExam, publishExam, actionLoading, actionError } = useExam();
  const [localError, setLocalError] = useState(null);

  if (!show || !currentExam) return null;

  const handlePublish = async () => {
    setLocalError(null);
    try {
      await publishExam(currentExam.id);
      onClose();
    } catch (err) {
      setLocalError(err.message || 'Failed to publish exam');
    }
  };

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
      <div className="modal-dialog modal-dialog-centered">
        <div className="modal-content border-0 rounded-4 shadow">
          <div className="modal-header border-bottom-0 pb-0">
            <h5 className="modal-title fw-bold">Publish Examination?</h5>
            <button type="button" className="btn-close" onClick={onClose} disabled={actionLoading}></button>
          </div>
          <div className="modal-body">
            {(actionError || localError) && (
              <div className="alert alert-danger py-2 px-3 small rounded-3">
                <i className="bi bi-exclamation-triangle-fill me-2"></i>
                {localError || actionError}
              </div>
            )}
            
            <p className="mb-2">
              Are you sure you want to publish <strong>"{currentExam.title}"</strong>?
            </p>
            <p className="text-muted small mb-0">
              Once published, students may be able to access this examination according to its assignments and schedule. Some fields will become uneditable.
            </p>
          </div>
          <div className="modal-footer border-top-0 pt-0">
            <button 
              type="button" 
              className="btn btn-outline-secondary" 
              onClick={onClose}
              disabled={actionLoading}
            >
              Cancel
            </button>
            <button 
              type="button" 
              className="btn btn-primary"
              onClick={handlePublish}
              disabled={actionLoading}
            >
              {actionLoading ? (
                <><span className="spinner-border spinner-border-sm me-2"></span>Publishing...</>
              ) : (
                'Publish Exam'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ExamPublishModal;
