import React from 'react';

const ProblemStatementPanel = ({ question, index, totalQuestions }) => {
  if (!question) {
    return (
      <div className="p-4 text-center text-muted">
        <i className="bi bi-file-code fs-1"></i>
        <p className="mt-2">No question selected.</p>
      </div>
    );
  }

  const getDifficultyBadge = (diff) => {
    switch (diff?.toLowerCase()) {
      case 'easy':
        return <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25">Easy</span>;
      case 'hard':
        return <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25">Hard</span>;
      case 'medium':
      default:
        return <span className="badge bg-warning bg-opacity-10 text-warning text-dark border border-warning border-opacity-25">Medium</span>;
    }
  };

  return (
    <div className="problem-statement-panel p-4 overflow-auto h-100 bg-white">
      {/* Question Header */}
      <div className="d-flex justify-content-between align-items-center mb-3 pb-3 border-bottom">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-primary">Question {index + 1} of {totalQuestions}</span>
            {getDifficultyBadge(question.difficulty)}
            <span className="badge bg-light text-dark border">{question.topic || 'Coding'}</span>
          </div>
          <h4 className="fw-bold mb-0 text-dark">{question.title || question.question_text?.substring(0, 40) || 'Coding Challenge'}</h4>
        </div>
        <div className="text-end">
          <div className="text-muted small">Max Score</div>
          <div className="fs-5 fw-bold text-primary">{question.marks || 10} pts</div>
        </div>
      </div>

      {/* Limits info */}
      <div className="d-flex gap-3 mb-4 p-2 px-3 bg-light rounded-3 small text-muted">
        <div><i className="bi bi-clock me-1 text-primary"></i> Time Limit: <strong>{question.time_limit || 2}s</strong></div>
        <div><i className="bi bi-memory me-1 text-primary"></i> Memory Limit: <strong>{question.memory_limit || 256}MB</strong></div>
      </div>

      {/* Problem Description */}
      <div className="mb-4">
        <h6 className="fw-bold text-dark mb-2">Problem Statement</h6>
        <div className="text-secondary lh-base text-break" style={{ whiteSpace: 'pre-wrap' }}>
          {question.question_text || question.description || 'No description provided.'}
        </div>
      </div>

      {/* Input / Output Format if available */}
      {question.input_format && (
        <div className="mb-4">
          <h6 className="fw-bold text-dark mb-2">Input Format</h6>
          <div className="text-secondary small bg-light p-3 rounded-3 border">
            {question.input_format}
          </div>
        </div>
      )}

      {question.output_format && (
        <div className="mb-4">
          <h6 className="fw-bold text-dark mb-2">Output Format</h6>
          <div className="text-secondary small bg-light p-3 rounded-3 border">
            {question.output_format}
          </div>
        </div>
      )}

      {/* Constraints */}
      {question.constraints && (
        <div className="mb-4">
          <h6 className="fw-bold text-dark mb-2">Constraints</h6>
          <div className="bg-light p-3 rounded-3 border font-monospace small text-dark" style={{ whiteSpace: 'pre-wrap' }}>
            {question.constraints}
          </div>
        </div>
      )}

      {/* Sample Test Cases */}
      {question.sample_test_cases && question.sample_test_cases.length > 0 && (
        <div className="mb-4">
          <h6 className="fw-bold text-dark mb-3">Sample Test Cases</h6>
          <div className="d-flex flex-column gap-3">
            {question.sample_test_cases.map((tc, idx) => (
              <div key={idx} className="card border rounded-3 bg-light">
                <div className="card-header bg-white py-2 px-3 fw-semibold small d-flex justify-content-between">
                  <span>Sample #{idx + 1}</span>
                </div>
                <div className="card-body p-3 font-monospace small">
                  <div className="row g-2">
                    <div className="col-md-6">
                      <span className="text-muted fw-bold font-sans-serif d-block mb-1" style={{ fontSize: '0.72rem' }}>INPUT</span>
                      <pre className="bg-white p-2 rounded border mb-0 text-dark" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>{tc.input}</pre>
                    </div>
                    <div className="col-md-6">
                      <span className="text-muted fw-bold font-sans-serif d-block mb-1" style={{ fontSize: '0.72rem' }}>EXPECTED OUTPUT</span>
                      <pre className="bg-white p-2 rounded border mb-0 text-success fw-bold" style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap' }}>{tc.expected_output}</pre>
                    </div>
                  </div>
                  {tc.explanation && (
                    <div className="mt-2 text-muted font-sans-serif" style={{ fontSize: '0.8rem' }}>
                      <strong>Explanation:</strong> {tc.explanation}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProblemStatementPanel;
