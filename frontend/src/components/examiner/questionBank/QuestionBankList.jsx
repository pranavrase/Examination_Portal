import React, { useState } from 'react';

const QuestionBankList = ({
  questions = [],
  loading = false,
  error = null,
  filters = {},
  pagination = { page: 1, limit: 10, totalPages: 1 },
  onFilterChange,
  onPageChange,
  onOpenAddMCQ,
  onOpenAddCoding,
  onOpenImport,
  onEditQuestion,
  onDeleteQuestion,
}) => {
  const [expandedId, setExpandedId] = useState(null);

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getDifficultyBadge = (diff) => {
    const diffStr = typeof diff === 'string'
      ? diff
      : (typeof diff === 'object' && diff !== null ? (diff.difficulty || diff.name || '') : '');
    switch (diffStr?.toLowerCase()) {
      case 'easy':
        return <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25">Easy</span>;
      case 'hard':
        return <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25">Hard</span>;
      case 'medium':
      default:
        return <span className="badge bg-warning bg-opacity-10 text-warning text-dark border border-warning border-opacity-25">Medium</span>;
    }
  };

  const getTypeBadge = (type) => {
    const typeStr = typeof type === 'string' ? type : '';
    if (typeStr.toLowerCase() === 'coding') {
      return <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25"><i className="bi bi-code-slash me-1"></i> Coding</span>;
    }
    return <span className="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25"><i className="bi bi-ui-radios me-1"></i> MCQ</span>;
  };

  return (
    <div className="card shadow-sm border-0 rounded-4 bg-white">
      {/* Header with Search and Action Buttons */}
      <div className="card-header bg-white border-bottom p-4">
        <div className="row g-3 align-items-center">
          <div className="col-lg-5">
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0">
                <i className="bi bi-search text-muted"></i>
              </span>
              <input
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search questions by text or topic..."
                value={filters.search || ''}
                onChange={(e) => onFilterChange({ search: e.target.value })}
              />
            </div>
          </div>

          <div className="col-lg-7 d-flex flex-wrap justify-content-lg-end gap-2">
            <button
              className="btn btn-outline-success rounded-3 btn-sm d-flex align-items-center gap-1"
              onClick={onOpenImport}
            >
              <i className="bi bi-file-earmark-spreadsheet"></i> Bulk Import
            </button>
            <button
              className="btn btn-outline-primary rounded-3 btn-sm d-flex align-items-center gap-1"
              onClick={onOpenAddMCQ}
            >
              <i className="bi bi-plus-circle"></i> Add MCQ
            </button>
            <button
              className="btn btn-primary rounded-3 btn-sm d-flex align-items-center gap-1"
              onClick={onOpenAddCoding}
            >
              <i className="bi bi-code-square"></i> Add Coding Question
            </button>
          </div>
        </div>
      </div>

      {/* Main Table Body */}
      <div className="card-body p-0">
        {error && (
          <div className="p-4">
            <div className="alert alert-danger rounded-3 mb-0">
              <i className="bi bi-exclamation-triangle-fill me-2"></i> {error}
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading questions...</span>
            </div>
            <p className="text-muted mt-2 small">Fetching question bank...</p>
          </div>
        ) : questions.length === 0 ? (
          <div className="text-center py-5 p-4">
            <div className="display-4 text-muted mb-3">
              <i className="bi bi-patch-question"></i>
            </div>
            <h5 className="fw-bold text-dark">No Questions Found</h5>
            <p className="text-secondary small mb-3">
              No questions match your filter criteria or question bank is currently empty.
            </p>
            <div className="d-flex justify-content-center gap-2">
              <button className="btn btn-sm btn-outline-primary" onClick={onOpenAddMCQ}>
                <i className="bi bi-plus-lg me-1"></i> Add First MCQ
              </button>
              <button className="btn btn-sm btn-primary" onClick={onOpenAddCoding}>
                <i className="bi bi-code-square me-1"></i> Add First Coding Question
              </button>
            </div>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th className="px-4 py-3 border-0" style={{ width: '80px' }}>ID</th>
                  <th className="py-3 border-0">Question Statement</th>
                  <th className="py-3 border-0">Category / Topic</th>
                  <th className="py-3 border-0">Type</th>
                  <th className="py-3 border-0">Difficulty</th>
                  <th className="py-3 border-0">Marks</th>
                  <th className="px-4 py-3 border-0 text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => {
                  const isExpanded = expandedId === q.id;
                  const isCoding = q.question_type?.toLowerCase() === 'coding';
                  const categoryName = typeof q.category === 'object' && q.category !== null
                    ? (q.category.name || 'General')
                    : (q.category || 'General');
                  const topicName = (typeof q.category === 'object' && q.category !== null ? q.category.topic : null)
                    || q.topic
                    || 'N/A';
                  const difficultyVal = (typeof q.category === 'object' && q.category !== null ? q.category.difficulty : null)
                    || q.difficulty
                    || 'Medium';
                  const options = q.mcq_options || q.options || [];

                  return (
                    <React.Fragment key={q.id}>
                      <tr>
                        <td className="px-4 py-3 text-muted fw-mono small">#{q.id}</td>
                        <td className="py-3">
                          <div className="d-flex align-items-start gap-2">
                            <button
                              className="btn btn-sm btn-light border-0 p-0 text-muted"
                              onClick={() => toggleExpand(q.id)}
                              title="Toggle details"
                            >
                              <i className={`bi ${isExpanded ? 'bi-chevron-down' : 'bi-chevron-right'}`}></i>
                            </button>
                            <div>
                              <div className="fw-semibold text-dark text-break" style={{ maxWidth: '400px' }}>
                                {q.question_text || q.text || 'Untitled Question'}
                              </div>
                              {q.explanation && (
                                <small className="text-muted text-truncate d-block" style={{ maxWidth: '380px' }}>
                                  Sol: {q.explanation}
                                </small>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="py-3">
                          <span className="badge bg-light text-dark border me-1 text-capitalize">{categoryName}</span>
                          <small className="text-secondary d-block mt-1">{topicName}</small>
                        </td>
                        <td className="py-3">{getTypeBadge(q.question_type)}</td>
                        <td className="py-3">{getDifficultyBadge(difficultyVal)}</td>
                        <td className="py-3 fw-bold text-dark">{q.marks || 1}</td>
                        <td className="px-4 py-3 text-end">
                          <div className="d-flex justify-content-end gap-1">
                            <button
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => onEditQuestion(q)}
                              title="Edit Question"
                            >
                              <i className="bi bi-pencil"></i>
                            </button>
                            <button
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => onDeleteQuestion(q)}
                              title="Delete Question"
                            >
                              <i className="bi bi-trash"></i>
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expandable Details Row */}
                      {isExpanded && (
                        <tr className="bg-light">
                          <td colSpan="7" className="p-3 px-4">
                            {!isCoding ? (
                              <div className="bg-white p-3 rounded-3 border">
                                <h6 className="fw-bold small mb-2 text-primary">MCQ Options:</h6>
                                <div className="row g-2">
                                  {options && options.length > 0 ? (
                                    options.map((opt, oIdx) => {
                                      const isCorrect = typeof opt === 'object' ? !!opt.is_correct : false;
                                      const text = typeof opt === 'object' ? (opt.option_text || opt.text || '') : opt;
                                      return (
                                        <div key={opt.id || oIdx} className="col-md-6">
                                          <div className={`p-2 rounded-2 border text-break small ${isCorrect ? 'bg-success bg-opacity-10 border-success fw-bold text-success' : 'bg-light'}`}>
                                            <span className="me-2">{String.fromCharCode(65 + oIdx)}.</span> {text}
                                            {isCorrect && <i className="bi bi-check-circle-fill ms-2"></i>}
                                          </div>
                                        </div>
                                      );
                                    })
                                  ) : (
                                    <span className="text-muted small">No options configured.</span>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <div className="bg-white p-3 rounded-3 border">
                                <h6 className="fw-bold small mb-2 text-danger">Coding Question Details:</h6>
                                <div className="row g-3 small">
                                  <div className="col-md-6">
                                    <strong>Constraints:</strong>
                                    <pre className="bg-light p-2 rounded mb-0 mt-1">{q.coding_details?.constraints || q.constraints || 'None specified'}</pre>
                                  </div>
                                  <div className="col-md-6">
                                    <strong>Limits:</strong>
                                    <div className="mt-1">
                                      <span className="badge bg-light text-dark me-2">
                                        Time: {q.coding_details?.time_limit_ms ? `${q.coding_details.time_limit_ms / 1000}s` : `${q.time_limit || 2}s`}
                                      </span>
                                      <span className="badge bg-light text-dark">
                                        Memory: {q.coding_details?.memory_limit_kb ? `${Math.round(q.coding_details.memory_limit_kb / 1024)}MB` : `${q.memory_limit || 256}MB`}
                                      </span>
                                    </div>
                                    <strong className="d-block mt-2">Test Cases:</strong>
                                    <span className="text-muted">
                                      {q.coding_details?.test_cases ? `${q.coding_details.test_cases.length} configured` : q.test_cases ? `${q.test_cases.length} configured` : '0 configured'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer Pagination */}
      {pagination.totalPages > 1 && (
        <div className="card-footer bg-white border-top p-3 d-flex justify-content-between align-items-center">
          <small className="text-muted">
            Page {pagination.page} of {pagination.totalPages}
          </small>
          <div className="d-flex gap-1">
            <button
              className="btn btn-sm btn-outline-secondary"
              disabled={pagination.page <= 1}
              onClick={() => onPageChange(pagination.page - 1)}
            >
              <i className="bi bi-chevron-left me-1"></i> Prev
            </button>
            <button
              className="btn btn-sm btn-outline-secondary"
              disabled={pagination.page >= pagination.totalPages}
              onClick={() => onPageChange(pagination.page + 1)}
            >
              Next <i className="bi bi-chevron-right ms-1"></i>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionBankList;
