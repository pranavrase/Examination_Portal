import React, { useState } from 'react';

const TestCaseResultPanel = ({ runResult, submissionResult, isRunning, isSubmitting }) => {
  const [activeTab, setActiveTab] = useState('run'); // 'run' or 'submission'

  if (isRunning) {
    return (
      <div className="p-4 text-center text-light bg-dark h-100 d-flex flex-column justify-content-center align-items-center">
        <div className="spinner-border text-info mb-2" role="status"></div>
        <div className="fw-bold small text-info">Executing Code...</div>
        <small className="text-secondary">Running code against sample test cases</small>
      </div>
    );
  }

  if (isSubmitting) {
    return (
      <div className="p-4 text-center text-light bg-dark h-100 d-flex flex-column justify-content-center align-items-center">
        <div className="spinner-border text-success mb-2" role="status"></div>
        <div className="fw-bold small text-success">Submitting Solution...</div>
        <small className="text-secondary">Evaluating against all hidden test cases</small>
      </div>
    );
  }

  if (!runResult && !submissionResult) {
    return (
      <div className="p-4 text-center text-secondary bg-dark h-100 d-flex flex-column justify-content-center align-items-center">
        <i className="bi bi-terminal fs-2 mb-2 text-secondary"></i>
        <div className="small">Click <strong>Run Code</strong> to test against sample test cases</div>
        <div className="small">or <strong>Submit Solution</strong> to submit for grading.</div>
      </div>
    );
  }

  const currentResult = activeTab === 'submission' && submissionResult ? submissionResult : runResult || submissionResult;

  const renderVerdictBadge = (verdict) => {
    const v = (verdict || '').toLowerCase();
    if (v.includes('pass') || v.includes('accept')) {
      return <span className="badge bg-success"><i className="bi bi-check-circle me-1"></i> {verdict || 'Passed'}</span>;
    }
    if (v.includes('compile')) {
      return <span className="badge bg-warning text-dark"><i className="bi bi-exclamation-triangle me-1"></i> Compilation Error</span>;
    }
    if (v.includes('time') || v.includes('tle')) {
      return <span className="badge bg-purple"><i className="bi bi-hourglass-split me-1"></i> Time Limit Exceeded</span>;
    }
    return <span className="badge bg-danger"><i className="bi bi-x-circle me-1"></i> {verdict || 'Failed'}</span>;
  };

  return (
    <div className="test-case-panel h-100 bg-dark text-light d-flex flex-column border-top border-secondary border-opacity-25 font-monospace">
      {/* Panel Tabs */}
      <div className="d-flex justify-content-between align-items-center px-3 pt-2 bg-black bg-opacity-25 border-bottom border-secondary border-opacity-25">
        <ul className="nav nav-tabs border-bottom-0 font-sans-serif" style={{ fontSize: '0.8rem' }}>
          {runResult && (
            <li className="nav-item">
              <button
                className={`nav-link text-light py-1 px-3 border-0 ${activeTab === 'run' ? 'active bg-dark fw-bold border-top border-primary' : 'opacity-75'}`}
                onClick={() => setActiveTab('run')}
              >
                Sample Run Results
              </button>
            </li>
          )}
          {submissionResult && (
            <li className="nav-item">
              <button
                className={`nav-link text-light py-1 px-3 border-0 ${activeTab === 'submission' || !runResult ? 'active bg-dark fw-bold border-top border-success' : 'opacity-75'}`}
                onClick={() => setActiveTab('submission')}
              >
                Submission Verdict
              </button>
            </li>
          )}
        </ul>

        {/* Exec Time & Memory Info */}
        <div className="small text-secondary font-sans-serif d-flex gap-3">
          {currentResult?.execution_time && (
            <span><i className="bi bi-clock me-1"></i>{currentResult.execution_time}</span>
          )}
          {currentResult?.memory_used && (
            <span><i className="bi bi-cpu me-1"></i>{currentResult.memory_used}</span>
          )}
        </div>
      </div>

      {/* Panel Body */}
      <div className="p-3 flex-grow-1 overflow-auto">
        {/* Compilation or Runtime Error Display */}
        {currentResult?.compile_error || currentResult?.runtime_error ? (
          <div className="bg-danger bg-opacity-10 border border-danger p-3 rounded-3 mb-3">
            <h6 className="fw-bold text-danger mb-2 font-sans-serif">
              <i className="bi bi-bug-fill me-1"></i> Execution Error Output
            </h6>
            <pre className="text-danger-subtle mb-0" style={{ whiteSpace: 'pre-wrap', fontSize: '0.82rem' }}>
              {currentResult.compile_error || currentResult.runtime_error}
            </pre>
          </div>
        ) : null}

        {/* Submission Result Overview */}
        {activeTab === 'submission' && submissionResult ? (
          <div className="bg-black bg-opacity-30 p-3 rounded-3 border border-secondary border-opacity-25 mb-3 font-sans-serif">
            <div className="d-flex align-items-center justify-content-between">
              <div>
                <span className="text-secondary small d-block">Submission Status</span>
                <h5 className="fw-bold text-white mb-0">{renderVerdictBadge(submissionResult.verdict)}</h5>
              </div>
              <div className="text-end">
                <span className="text-secondary small d-block">Evaluation Progress</span>
                <h5 className="fw-bold text-success mb-0">
                  {submissionResult.passed_test_cases || 0} / {submissionResult.total_test_cases || 0} Cases Passed
                </h5>
              </div>
            </div>
          </div>
        ) : null}

        {/* Sample Run Test Cases List */}
        {activeTab === 'run' && runResult?.test_cases && runResult.test_cases.length > 0 ? (
          <div className="d-flex flex-column gap-3">
            {runResult.test_cases.map((tc, idx) => (
              <div key={idx} className="border border-secondary border-opacity-25 rounded-3 p-3 bg-black bg-opacity-25">
                <div className="d-flex justify-content-between align-items-center mb-2 font-sans-serif">
                  <span className="fw-bold text-light small">Sample Case #{idx + 1}</span>
                  {tc.passed ? (
                    <span className="badge bg-success bg-opacity-25 text-success border border-success"><i className="bi bi-check me-1"></i> Passed</span>
                  ) : (
                    <span className="badge bg-danger bg-opacity-25 text-danger border border-danger"><i className="bi bi-x me-1"></i> Wrong Answer</span>
                  )}
                </div>

                <div className="row g-2 small">
                  <div className="col-md-4">
                    <span className="text-secondary font-sans-serif d-block mb-1" style={{ fontSize: '0.7rem' }}>INPUT</span>
                    <pre className="bg-dark p-2 rounded border border-secondary border-opacity-25 text-light mb-0" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>{tc.input}</pre>
                  </div>
                  <div className="col-md-4">
                    <span className="text-secondary font-sans-serif d-block mb-1" style={{ fontSize: '0.7rem' }}>EXPECTED OUTPUT</span>
                    <pre className="bg-dark p-2 rounded border border-secondary border-opacity-25 text-success mb-0" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>{tc.expected_output}</pre>
                  </div>
                  <div className="col-md-4">
                    <span className="text-secondary font-sans-serif d-block mb-1" style={{ fontSize: '0.7rem' }}>YOUR OUTPUT</span>
                    <pre className={`bg-dark p-2 rounded border border-secondary border-opacity-25 mb-0 ${tc.passed ? 'text-success' : 'text-danger'}`} style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>{tc.actual_output || '(No Output)'}</pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default TestCaseResultPanel;
