import React from 'react';

const RunButton = ({ onRun, isRunning, disabled }) => {
  return (
    <button
      type="button"
      className="btn btn-outline-light btn-sm px-3 rounded-3 d-flex align-items-center gap-2"
      onClick={onRun}
      disabled={isRunning || disabled}
      title="Test your code against sample test cases (Does not finalize submission)"
    >
      {isRunning ? (
        <>
          <span className="spinner-border spinner-border-sm text-info" role="status" aria-hidden="true"></span>
          <span>Running...</span>
        </>
      ) : (
        <>
          <i className="bi bi-play-circle-fill text-info"></i>
          <span>Run Code</span>
        </>
      )}
    </button>
  );
};

export default RunButton;
