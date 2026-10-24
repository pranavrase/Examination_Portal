import React, { useState } from 'react';
import { useExaminer } from '../../context/ExaminerContext';
import { duplicateExam } from '../../api/examinerApi';

const STATUS_OPTIONS = [
  { value: '', label: 'All Status' },
  { value: 'published', label: 'Active / Published' },
  { value: 'draft', label: 'Draft / Upcoming' },
  { value: 'closed', label: 'Closed / Completed' },
];

const ExamListTable = ({ onCreateNew, onViewExam, onManageQuestions, onViewResults }) => {
  const {
    exams,
    loadingExams,
    examsError,
    actionLoading,
    fetchExams,
    removeExam,
    togglePublishExam,
  } = useExaminer();

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [duplicatingId, setDuplicatingId] = useState(null);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchExams(search, statusFilter);
  };

  const handleDelete = async (examId) => {
    try {
      await removeExam(examId);
      setConfirmDeleteId(null);
    } catch (_) {}
  };

  const handleDuplicate = async (examId) => {
    try {
      setDuplicatingId(examId);
      await duplicateExam(examId);
      fetchExams(search, statusFilter);
    } catch (err) {
      alert('Failed to duplicate exam');
    } finally {
      setDuplicatingId(null);
    }
  };

  const getStatusBadge = (exam) => {
    if (exam.status === 'published') {
      return <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3">Active / Published</span>;
    }
    if (exam.status === 'closed') {
      return <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill px-3">Closed</span>;
    }
    return <span className="badge bg-warning-subtle text-warning border border-warning-subtle rounded-pill px-3">Draft</span>;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="exam-list">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="mb-3">
          <h5 className="fw-bold mb-1 d-flex align-items-center gap-2">
            <i className="bi bi-journal-richtext text-primary" />
            <span>Examinations Directory</span>
          </h5>
          <p className="text-muted small mb-0">
            {exams.length} examination{exams.length !== 1 ? 's' : ''} available under your supervision
          </p>
        </div>

        {/* Search & Filter */}
        <form onSubmit={handleSearch} className="row g-2 mb-3">
          <div className="col-12 col-md-6">
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0">
                <i className="bi bi-search text-muted" />
              </span>
              <input
                id="exam-search-input"
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search examinations by title keyword..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="col-6 col-md-3">
            <select
              id="exam-status-filter"
              className="form-select bg-light"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                fetchExams(search, e.target.value);
              }}
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="col-6 col-md-3">
            <button type="submit" className="btn btn-outline-primary w-100 rounded-3">
              <i className="bi bi-funnel me-1" />
              Apply Filter
            </button>
          </div>
        </form>
      </div>

      {/* Table Body */}
      <div className="card-body p-0">
        {loadingExams ? (
          <div className="p-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="placeholder-glow d-flex align-items-center gap-3 mb-3 p-2 rounded-3 border">
                <span className="placeholder rounded-3 flex-grow-1" style={{ height: 20 }} />
                <span className="placeholder rounded-3" style={{ width: 80, height: 20 }} />
                <span className="placeholder rounded-3" style={{ width: 60, height: 20 }} />
              </div>
            ))}
          </div>
        ) : examsError ? (
          <div className="alert alert-danger m-4 border-0 rounded-3">
            <i className="bi bi-exclamation-triangle-fill me-2" />
            {examsError}
          </div>
        ) : exams.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-journal-x display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">No examinations found</h6>
            <p className="small mb-3">Get started by creating your first exam using the wizard.</p>
            <button className="btn btn-primary rounded-3 px-4" onClick={onCreateNew}>
              <i className="bi bi-plus me-1" /> Create Examination
            </button>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3 fw-semibold text-muted small">EXAM TITLE</th>
                  <th className="py-3 fw-semibold text-muted small">CATEGORY</th>
                  <th className="py-3 fw-semibold text-muted small">DURATION</th>
                  <th className="py-3 fw-semibold text-muted small">QUESTIONS</th>
                  <th className="py-3 fw-semibold text-muted small">STATUS</th>
                  <th className="py-3 fw-semibold text-muted small">CREATED</th>
                  <th className="pe-4 py-3 fw-semibold text-muted small text-end">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr key={exam.id} className="border-top">
                    <td className="ps-4 py-3">
                      <div className="fw-semibold text-dark">{exam.title}</div>
                      {exam.description && (
                        <div className="text-muted small text-truncate" style={{ maxWidth: 240 }}>
                          {exam.description}
                        </div>
                      )}
                    </td>
                    <td>
                      <span className="badge bg-primary-subtle text-primary rounded-pill px-3">
                        {exam.category || exam.exam_type || 'Aptitude & Technical'}
                      </span>
                    </td>
                    <td className="text-muted small">
                      <i className="bi bi-clock me-1 text-primary" />
                      {exam.duration_minutes ?? exam.duration ?? 60} mins
                    </td>
                    <td>
                      <span className="badge bg-light text-dark border px-2.5 py-1 fw-bold">
                        {exam.total_questions ?? exam.question_count ?? 0} Qs
                      </span>
                    </td>
                    <td>{getStatusBadge(exam)}</td>
                    <td className="text-muted small">{formatDate(exam.created_at)}</td>
                    <td className="pe-4 text-end">
                      <div className="d-flex justify-content-end gap-1">
                        <button
                          id={`btn-view-exam-${exam.id}`}
                          className="btn btn-sm btn-light rounded-3 text-primary"
                          title="Configure Details"
                          onClick={() => onViewExam(exam)}
                        >
                          <i className="bi bi-gear-fill" />
                        </button>
                        <button
                          id={`btn-questions-${exam.id}`}
                          className="btn btn-sm btn-light rounded-3 text-info"
                          title="Manage Questions & Paper"
                          onClick={() => onManageQuestions(exam)}
                        >
                          <i className="bi bi-patch-question-fill" />
                        </button>
                        <button
                          id={`btn-results-${exam.id}`}
                          className="btn btn-sm btn-light rounded-3 text-success"
                          title="View Results & Submissions"
                          onClick={() => onViewResults(exam)}
                        >
                          <i className="bi bi-bar-chart-line-fill" />
                        </button>
                        <button
                          id={`btn-duplicate-${exam.id}`}
                          className="btn btn-sm btn-light rounded-3 text-secondary"
                          title="Duplicate Exam"
                          onClick={() => handleDuplicate(exam.id)}
                          disabled={duplicatingId === exam.id}
                        >
                          {duplicatingId === exam.id ? (
                            <span className="spinner-border spinner-border-sm" />
                          ) : (
                            <i className="bi bi-copy" />
                          )}
                        </button>
                        <button
                          id={`btn-publish-${exam.id}`}
                          className={`btn btn-sm rounded-3 ${exam.status === 'published' ? 'btn-warning' : 'btn-success'}`}
                          title={exam.status === 'published' ? 'Deactivate / Close' : 'Activate / Publish'}
                          onClick={() => togglePublishExam(exam.id)}
                          disabled={actionLoading || exam.status === 'closed'}
                        >
                          <i className={`bi ${exam.status === 'published' ? 'bi-pause-circle' : 'bi-send-check'}`} />
                        </button>
                        <button
                          id={`btn-delete-exam-${exam.id}`}
                          className="btn btn-sm btn-outline-danger rounded-3"
                          title="Delete Exam"
                          onClick={() => setConfirmDeleteId(exam.id)}
                          disabled={actionLoading}
                        >
                          <i className="bi bi-trash" />
                        </button>
                      </div>

                      {/* Inline delete confirmation */}
                      {confirmDeleteId === exam.id && (
                        <div className="mt-2 p-2 bg-danger-subtle border border-danger-subtle rounded-3 text-start">
                          <p className="small mb-2 text-danger fw-semibold">
                            <i className="bi bi-exclamation-triangle me-1" />
                            Delete this examination?
                          </p>
                          <div className="d-flex gap-2">
                            <button
                              className="btn btn-danger btn-sm rounded-3 flex-grow-1"
                              onClick={() => handleDelete(exam.id)}
                              disabled={actionLoading}
                            >
                              {actionLoading ? (
                                <span className="spinner-border spinner-border-sm" />
                              ) : (
                                'Delete'
                              )}
                            </button>
                            <button
                              className="btn btn-secondary btn-sm rounded-3 flex-grow-1"
                              onClick={() => setConfirmDeleteId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExamListTable;
