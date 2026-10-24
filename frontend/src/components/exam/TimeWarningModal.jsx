import React from 'react';
import { useExamAttempt } from '../../context/ExamAttemptContext';

const TimeWarningModal = () => {
  const { activeWarning, dismissWarning } = useExamAttempt();

  if (!activeWarning) return null;

  const isOneMin = activeWarning === '1min';

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 1070 }}>
      <div className="modal-dialog modal-dialog-centered">
        <div className={`modal-content border-0 rounded-4 shadow-lg ${isOneMin ? 'border border-danger' : 'border border-warning'}`}>
          <div className="modal-header border-bottom-0 pb-0">
            <h5 className={`modal-title fw-bold ${isOneMin ? 'text-danger' : 'text-warning'}`}>
              <i className={`bi ${isOneMin ? 'bi-alarm-fill' : 'bi-exclamation-triangle-fill'} me-2`}></i>
              {isOneMin ? 'CRITICAL: 1 Minute Remaining!' : 'Notice: 5 Minutes Remaining'}
            </h5>
          </div>

          <div className="modal-body py-3 text-dark">
            <p className="mb-2">
              {isOneMin ? (
                <>Your exam will automatically submit in <strong>less than 60 seconds</strong>. Please finalize your answers immediately.</>
              ) : (
                <>You have <strong>5 minutes</strong> left before your exam time expires. Please review your answers and prepare for submission.</>
              )}
            </p>
            <div className="bg-light p-3 rounded-3 border text-secondary small">
              <i className="bi bi-info-circle me-1"></i> Answers are auto-saved. When the timer hits 00:00:00, your exam will automatically submit.
            </div>
          </div>

          <div className="modal-footer border-top-0 pt-0">
            <button
              type="button"
              className={`btn px-4 rounded-3 ${isOneMin ? 'btn-danger' : 'btn-warning text-dark fw-bold'}`}
              onClick={dismissWarning}
            >
              I Understand
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimeWarningModal;
