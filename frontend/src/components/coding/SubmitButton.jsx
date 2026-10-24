import React, { useState } from 'react';

const SubmitButton = ({ onSubmit, isSubmitting, isSubmitted, disabled, attemptId }) => {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleConfirmSubmit = () => {
    setShowConfirm(false);
    onSubmit(attemptId);
  };

  return (
    <>
      <button
        type="button"
        className={`btn btn-sm px-4 rounded-3 d-flex align-items-center gap-2 ${
          isSubmitted ? 'btn-success' : 'btn-primary'
        }`}
        onClick={() => setShowConfirm(true)}
        disabled={isSubmitting || disabled}
      >
        {isSubmitting ? (
          <>
            <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
            <span>Submitting...</span>
          </>
        ) : isSubmitted ? (
          <>
            <i className="bi bi-check-circle-fill"></i>
            <span>Submitted</span>
          </>
        ) : (
          <>
            <i className="bi bi-cloud-upload-fill"></i>
            <span>Submit Solution</span>
          </>
        )}
      </button>

      {/* Submission Confirmation Modal */}
      {showConfirm && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.6)', zIndex: 1060 }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 rounded-4 shadow-lg text-dark">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold">
                  <i className="bi bi-send-check text-primary me-2"></i>
                  Confirm Final Submission
                </h5>
                <button type="button" className="btn-close" onClick={() => setShowConfirm(false)}></button>
              </div>

              <div className="modal-body py-3">
                <p className="mb-2">
                  Are you sure you want to submit your code for evaluation against all test cases?
                </p>
                <div className="bg-light p-3 rounded-3 border small text-secondary">
                  <i className="bi bi-info-circle text-primary me-1"></i> Your solution will be tested against hidden test cases and scored. You can resubmit anytime before the exam duration ends.
                </div>
              </div>

              <div className="modal-footer border-top-0 pt-0">
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => setShowConfirm(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary btn-sm px-4"
                  onClick={handleConfirmSubmit}
                >
                  Yes, Submit Now
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SubmitButton;
