import React, { useEffect, useState } from 'react';
import { getAllResults, toggleResultVisibility } from '../../api/examinerApi';

const ExaminerResultsPanel = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const fetchResults = async () => {
    try {
      setLoading(true);
      const data = await getAllResults();
      setResults(data || []);
    } catch (err) {
      console.error('Failed to load examination results:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  const handleToggleVisibility = async (resultId) => {
    try {
      await toggleResultVisibility(resultId);
      setResults((prev) =>
        prev.map((r) => (r.id === resultId ? { ...r, is_published: !r.is_published } : r))
      );
    } catch (err) {
      alert('Failed to update result visibility');
    }
  };

  const handleExportCSV = () => {
    if (!results.length) return;
    const headers = ['Rank', 'Candidate Name', 'Email', 'Exam Title', 'Score', 'Total Marks', 'Percentage', 'Percentile', 'Pass/Fail', 'Time Taken'];
    const rows = results.map((r) => [
      r.rank || '—',
      `"${r.candidate_name}"`,
      r.candidate_email,
      `"${r.exam_title}"`,
      r.score_obtained,
      r.total_marks_possible,
      `${r.percentage}%`,
      r.percentile || '—',
      r.pass_fail ? 'PASSED' : 'FAILED',
      r.time_spent_minutes ? `${r.time_spent_minutes} mins` : '—',
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Exam_Results_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filtered = results.filter((r) => {
    const term = search.toLowerCase();
    const matchesSearch = r.candidate_name?.toLowerCase().includes(term) || r.candidate_email?.toLowerCase().includes(term) || r.exam_title?.toLowerCase().includes(term);
    const matchesStatus = statusFilter === 'passed' ? r.pass_fail : statusFilter === 'failed' ? !r.pass_fail : true;
    return matchesSearch && matchesStatus;
  });

  const avgScore = results.length ? (results.reduce((acc, r) => acc + (r.percentage || 0), 0) / results.length).toFixed(1) : 0;
  const passedCount = results.filter((r) => r.pass_fail).length;
  const passRate = results.length ? ((passedCount / results.length) * 100).toFixed(1) : 0;

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="examiner-results-management">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
          <div>
            <span className="badge bg-warning text-dark mb-1 text-uppercase fw-semibold">
              Evaluation & Grading
            </span>
            <h5 className="fw-bold mb-0 text-dark">Results Management & Scorecards</h5>
            <p className="text-muted small mb-0">Review candidate scores, pass/fail status, percentiles, and control candidate result visibility</p>
          </div>

          <div className="d-flex align-items-center gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm rounded-3 d-flex align-items-center gap-1.5 px-3"
              onClick={fetchResults}
            >
              <i className="bi bi-arrow-repeat" />
              <span>Refresh Results</span>
            </button>

            <button
              type="button"
              className="btn btn-primary btn-sm rounded-3 d-flex align-items-center gap-1.5 px-3 shadow-sm"
              onClick={handleExportCSV}
            >
              <i className="bi bi-file-earmark-spreadsheet-fill" />
              <span>Export CSV</span>
            </button>
          </div>
        </div>

        {/* Summary Metrics */}
        <div className="row g-3 mb-3">
          <div className="col-md-4">
            <div className="p-3 bg-primary bg-opacity-10 rounded-3 border border-primary border-opacity-10 text-center">
              <div className="fs-4 fw-bold text-primary">{avgScore}%</div>
              <div className="text-muted small fw-medium">Average Score</div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="p-3 bg-success bg-opacity-10 rounded-3 border border-success border-opacity-10 text-center">
              <div className="fs-4 fw-bold text-success">{passRate}%</div>
              <div className="text-muted small fw-medium">Pass Percentage ({passedCount}/{results.length})</div>
            </div>
          </div>
          <div className="col-md-4">
            <div className="p-3 bg-info bg-opacity-10 rounded-3 border border-info border-opacity-10 text-center">
              <div className="fs-4 fw-bold text-info">{results.length}</div>
              <div className="text-muted small fw-medium">Evaluated Submissions</div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="row g-2 mb-3">
          <div className="col-12 col-md-7">
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0">
                <i className="bi bi-search text-muted" />
              </span>
              <input
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search candidate name, email, or exam title..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="col-6 col-md-3">
            <select
              className="form-select bg-light"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Results</option>
              <option value="passed">Passed Candidates Only</option>
              <option value="failed">Failed Candidates Only</option>
            </select>
          </div>
          <div className="col-6 col-md-2 d-flex align-items-center">
            <span className="text-muted small">
              <strong>{filtered.length}</strong> items
            </span>
          </div>
        </div>
      </div>

      {/* Table Body */}
      <div className="card-body p-0">
        {loading ? (
          <div className="p-5 text-center">
            <div className="spinner-border text-warning" role="status" />
            <p className="text-muted small mt-2">Loading candidate scorecards...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-award display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">No results found</h6>
            <p className="small mb-0">Results will appear after candidates complete examinations.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3 fw-semibold text-muted small">RANK</th>
                  <th className="py-3 fw-semibold text-muted small">CANDIDATE</th>
                  <th className="py-3 fw-semibold text-muted small">EXAM</th>
                  <th className="py-3 fw-semibold text-muted small">SCORE</th>
                  <th className="py-3 fw-semibold text-muted small">PERCENTILE</th>
                  <th className="py-3 fw-semibold text-muted small">RESULT</th>
                  <th className="py-3 fw-semibold text-muted small">TIME TAKEN</th>
                  <th className="pe-4 py-3 fw-semibold text-muted small text-end">VISIBILITY</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id} className="border-top">
                    <td className="ps-4 py-3">
                      {r.rank ? (
                        <span className={`badge ${r.rank === 1 ? 'bg-warning text-dark' : r.rank === 2 ? 'bg-secondary text-white' : r.rank === 3 ? 'bg-danger text-white' : 'bg-light text-dark border'} rounded-pill px-2.5 py-1 fw-bold`}>
                          #{r.rank}
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="py-3">
                      <div className="fw-semibold text-dark">{r.candidate_name}</div>
                      <div className="text-muted small">{r.candidate_email}</div>
                    </td>
                    <td className="text-muted small">{r.exam_title}</td>
                    <td>
                      <span className="fw-bold text-dark">{r.score_obtained}</span>
                      <span className="text-muted small"> / {r.total_marks_possible} ({r.percentage}%)</span>
                    </td>
                    <td>
                      {r.percentile ? (
                        <span className="badge bg-info-subtle text-info rounded-pill px-2.5 py-1 fw-semibold">
                          {r.percentile}th %ile
                        </span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
                      {r.pass_fail ? (
                        <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3">
                          <i className="bi bi-check-circle-fill me-1" /> Passed
                        </span>
                      ) : (
                        <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-3">
                          <i className="bi bi-x-circle-fill me-1" /> Failed
                        </span>
                      )}
                    </td>
                    <td className="text-muted small">{r.time_spent_minutes ? `${r.time_spent_minutes} mins` : '—'}</td>
                    <td className="pe-4 text-end">
                      <button
                        type="button"
                        className={`btn btn-sm rounded-pill px-3 ${r.is_published ? 'btn-outline-success' : 'btn-outline-secondary'}`}
                        onClick={() => handleToggleVisibility(r.id)}
                        title={r.is_published ? 'Results visible to student' : 'Hidden from student'}
                      >
                        <i className={`bi ${r.is_published ? 'bi-eye-fill me-1' : 'bi-eye-slash-fill me-1'}`} />
                        {r.is_published ? 'Published' : 'Hidden'}
                      </button>
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

export default ExaminerResultsPanel;
