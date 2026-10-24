import React from 'react';
import { useCodingExam } from '../../context/CodingExamContext';

const QuestionNavigatorSidebar = ({ isOpen, onClose }) => {
  const {
    questions,
    currentQuestionIndex,
    selectQuestion,
    questionStatuses,
  } = useCodingExam();

  const submittedCount = Object.values(questionStatuses).filter((s) => s === 'submitted').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'submitted':
        return <span className="badge bg-success"><i className="bi bi-check-lg me-1"></i> Submitted</span>;
      case 'attempted':
        return <span className="badge bg-warning text-dark"><i className="bi bi-pencil-fill me-1"></i> In Progress</span>;
      case 'unattempted':
      default:
        return <span className="badge bg-secondary opacity-75">Unattempted</span>;
    }
  };

  return (
    <>
      {/* Mobile Drawer Overlay */}
      {isOpen && (
        <div
          className="navigator-overlay d-lg-none"
          onClick={onClose}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1045,
          }}
        ></div>
      )}

      <aside
        className={`bg-dark text-white p-3 border-start border-secondary border-opacity-25 d-flex flex-column ${
          isOpen ? 'd-block' : 'd-none d-lg-flex'
        }`}
        style={{
          width: '300px',
          height: '100%',
          flexShrink: 0,
          zIndex: 1040,
        }}
      >
        {/* Sidebar Header */}
        <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25">
          <h6 className="fw-bold mb-0 text-uppercase text-secondary tracking-wider" style={{ fontSize: '0.8rem' }}>
            <i className="bi bi-grid-3x3-gap-fill me-2 text-primary"></i> Question Palette
          </h6>
          <button type="button" className="btn-close btn-close-white d-lg-none" onClick={onClose}></button>
        </div>

        {/* Progress Overview */}
        <div className="bg-black bg-opacity-30 p-3 rounded-3 mb-3 border border-secondary border-opacity-25">
          <div className="d-flex justify-content-between align-items-center mb-1">
            <span className="small text-secondary">Progress</span>
            <span className="small fw-bold text-success">{submittedCount} / {questions.length} Submitted</span>
          </div>
          <div className="progress" style={{ height: '6px' }}>
            <div
              className="progress-bar bg-success"
              role="progressbar"
              style={{ width: `${questions.length ? (submittedCount / questions.length) * 100 : 0}%` }}
            ></div>
          </div>
        </div>

        {/* Question Palette Buttons 5-Column Grid */}
        <div className="mb-4">
          <label className="form-label small text-secondary fw-bold mb-2">Questions Grid</label>
          <div
            className="questions-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '8px',
            }}
          >
            {questions.map((q, idx) => {
              const isActive = currentQuestionIndex === idx;
              const status = questionStatuses[q.id] || 'unattempted';
              const serialNum = idx + 1;

              let bgStyle = '#374151';
              let borderStyle = '1px solid rgba(255, 255, 255, 0.15)';
              let textStyle = '#F3F4F6';

              if (status === 'submitted') {
                bgStyle = '#16A34A';
                borderStyle = '1px solid #15803D';
                textStyle = '#FFFFFF';
              } else if (status === 'attempted') {
                bgStyle = '#F59E0B';
                borderStyle = '1px solid #D97706';
                textStyle = '#FFFFFF';
              }

              return (
                <button
                  key={q.id || idx}
                  type="button"
                  className="btn p-0 d-flex align-items-center justify-content-center position-relative transition-all"
                  style={{
                    height: '42px',
                    width: '100%',
                    backgroundColor: isActive && status === 'unattempted' ? '#2563EB' : bgStyle,
                    color: textStyle,
                    border: isActive ? '2px solid #60A5FA' : borderStyle,
                    borderRadius: '8px',
                    fontWeight: '700',
                    fontSize: '0.9rem',
                    outline: isActive ? '2px solid #93C5FD' : 'none',
                    outlineOffset: isActive ? '2px' : '0px',
                    boxShadow: isActive ? '0 0 10px rgba(96, 165, 250, 0.75)' : 'none',
                  }}
                  onClick={() => {
                    selectQuestion(idx);
                    if (onClose) onClose();
                  }}
                  title={`Question ${serialNum} - ${status}`}
                  aria-label={`Question ${serialNum} - ${status}`}
                >
                  {serialNum}
                </button>
              );
            })}
          </div>
        </div>

        {/* Detailed Questions List */}
        <div className="flex-grow-1 overflow-auto pe-1">
          <label className="form-label small text-secondary fw-bold mb-2">Question Details</label>
          <div className="list-group list-group-flush border-0">
            {questions.map((q, idx) => {
              const isActive = currentQuestionIndex === idx;
              const status = questionStatuses[q.id] || 'unattempted';

              return (
                <button
                  key={q.id || idx}
                  type="button"
                  className={`list-group-item list-group-item-action bg-transparent text-white border-secondary border-opacity-25 rounded-3 mb-2 p-2 text-start transition-all ${
                    isActive ? 'border-primary bg-primary bg-opacity-10 fw-bold' : 'hover-bg-dark opacity-75'
                  }`}
                  onClick={() => {
                    selectQuestion(idx);
                    if (onClose) onClose();
                  }}
                >
                  <div className="d-flex justify-content-between align-items-start mb-1">
                    <span className="small fw-semibold text-truncate" style={{ maxWidth: '150px' }}>
                      Q{idx + 1}. {q.title || 'Coding Challenge'}
                    </span>
                    <span className="small text-muted">{q.marks || 10} pts</span>
                  </div>
                  <div className="d-flex justify-content-between align-items-center">
                    <span className="small text-secondary">{q.topic || 'Coding'}</span>
                    {getStatusBadge(status)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </aside>
    </>
  );
};

export default QuestionNavigatorSidebar;
