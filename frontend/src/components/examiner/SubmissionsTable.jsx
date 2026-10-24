import React, { useEffect, useState } from 'react';
import { useExaminer } from '../../context/ExaminerContext';

const SubmissionsTable = ({ exam, onBack }) => {
  const { submissions, loadingSubmissions, submissionsError, fetchSubmissions } = useExaminer();
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (exam?.id) fetchSubmissions(exam.id);
  }, [exam?.id, fetchSubmissions]);

  const filtered = submissions.filter((s) => {
    const term = search.toLowerCase();
    const name = (s.student_name || s.candidate_name || s.user?.full_name || '').toLowerCase();
    const email = (s.student_email || s.user?.email || '').toLowerCase();
    return name.includes(term) || email.includes(term);
  });

  const getScoreBadge = (score, total) => {
    const pct = total > 0 ? (score / total) * 100 : 0;
    if (pct >= 70) return 'bg-success-subtle text-success';
    if (pct >= 40) return 'bg-warning-subtle text-warning';
    return 'bg-danger-subtle text-danger';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const averageScore = () => {
    if (!submissions.length) return '—';
    const avg = submissions.reduce((acc, s) => acc + (s.score || 0), 0) / submissions.length;
    return `${avg.toFixed(1)} / ${submissions[0]?.total_marks || exam?.total_marks || 100}`;
  };

  const passCount = submissions.filter((s) => s.passed || s.is_passed).length;

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="submissions-table">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
          <div>
            <button
              id="btn-back-from-results"
              className="btn btn-sm btn-light rounded-3 mb-2"
              onClick={onBack}
            >
              <i className="bi bi-arrow-left me-1" />
              Back to Exams
            </button>
            <h5 className="fw-bold mb-1">
              <i className="bi bi-bar-chart-line text-primary me-2" />
              Submissions & Results
            </h5>
            <p className="text-muted small mb-0">
              Exam: <strong>{exam?.title}</strong> &nbsp;·&nbsp; {submissions.length} submission
              {submissions.length !== 1 ? 's' : ''}
            </p>
          </div>
          <button
            className="btn btn-outline-primary d-flex align-items-center gap-2 rounded-3"
            onClick={() => fetchSubmissions(exam.id)}
          >
            <i className="bi bi-arrow-clockwise" />
            Refresh
          </button>
        </div>

        {/* Summary Cards */}
        {submissions.length > 0 && (
          <div className="row g-3 mb-3">
            {[
              { label: 'Total Submissions', value: submissions.length, icon: 'bi-file-earmark-check', color: 'primary' },
              { label: 'Passed', value: passCount, icon: 'bi-emoji-smile-fill', color: 'success' },
              { label: 'Failed', value: submissions.length - passCount, icon: 'bi-emoji-frown', color: 'danger' },
              { label: 'Average Score', value: averageScore(), icon: 'bi-graph-up', color: 'info' },
            ].map((c) => (
              <div key={c.label} className="col-6 col-md-3">
                <div className={`card border-0 bg-${c.color}-subtle rounded-3 p-3`}>
                  <div className="d-flex align-items-center gap-2">
                    <i className={`${c.icon} text-${c.color} fs-4`} />
                    <div>
                      <div className={`fw-bold text-${c.color}`}>{c.value}</div>
                      <div className="small text-muted">{c.label}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Search */}
        <div className="mb-3">
          <div className="input-group">
            <span className="input-group-text bg-light border-end-0">
              <i className="bi bi-search text-muted" />
            </span>
            <input
              id="submissions-search-input"
              type="text"
              className="form-control border-start-0 bg-light"
              placeholder="Search by student name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="card-body p-0">
        {loadingSubmissions ? (
          <div className="p-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="placeholder-glow d-flex gap-3 mb-3 p-2 rounded border">
                <span className="placeholder flex-grow-1 rounded-3" style={{ height: 20 }} />
                <span className="placeholder rounded-3" style={{ width: 80, height: 20 }} />
              </div>
            ))}
          </div>
        ) : submissionsError ? (
          <div className="alert alert-danger m-4 border-0 rounded-3">
            <i className="bi bi-exclamation-triangle-fill me-2" />
            {submissionsError}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-file-earmark-x display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">
              {submissions.length === 0 ? 'No submissions yet' : 'No matching submissions'}
            </h6>
            <p className="small">
              {submissions.length === 0
                ? 'Students have not submitted this exam yet.'
                : 'Try adjusting your search query.'}
            </p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3 fw-semibold text-muted small">#</th>
                  <th className="py-3 fw-semibold text-muted small">STUDENT</th>
                  <th className="py-3 fw-semibold text-muted small">SCORE</th>
                  <th className="py-3 fw-semibold text-muted small">STATUS</th>
                  <th className="py-3 fw-semibold text-muted small">TIME TAKEN</th>
                  <th className="py-3 fw-semibold text-muted small">SUBMITTED AT</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((sub, i) => {
                  const name = sub.student_name || sub.candidate_name || sub.user?.full_name || 'Unknown';
                  const email = sub.student_email || sub.user?.email || '—';
                  const score = sub.score ?? 0;
                  const total = sub.total_marks || exam?.total_marks || 100;
                  const pct = total > 0 ? ((score / total) * 100).toFixed(1) : 0;
                  const passed = sub.passed || sub.is_passed;
                  const timeTaken = sub.time_taken_minutes
                    ? `${sub.time_taken_minutes} min`
                    : sub.duration_taken
                    ? `${sub.duration_taken} min`
                    : '—';

                  return (
                    <tr key={sub.id || i} className="border-top">
                      <td className="ps-4 py-3 text-muted small">{i + 1}</td>
                      <td className="py-3">
                        <div className="d-flex align-items-center gap-2">
                          <div
                            className="bg-primary text-white rounded-circle d-flex align-items-center justify-content-center fw-bold flex-shrink-0"
                            style={{ width: 36, height: 36, fontSize: 14 }}
                          >
                            {name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="fw-semibold text-dark">{name}</div>
                            <div className="text-muted small">{email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3">
                        <span className={`badge rounded-pill px-3 py-2 ${getScoreBadge(score, total)}`}>
                          {score} / {total} ({pct}%)
                        </span>
                      </td>
                      <td className="py-3">
                        {passed ? (
                          <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3">
                            <i className="bi bi-check-circle me-1" />
                            Passed
                          </span>
                        ) : (
                          <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-3">
                            <i className="bi bi-x-circle me-1" />
                            Failed
                          </span>
                        )}
                      </td>
                      <td className="text-muted small">{timeTaken}</td>
                      <td className="text-muted small">{formatDate(sub.submitted_at || sub.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default SubmissionsTable;
