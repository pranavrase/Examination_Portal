import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStudent } from '../../context/StudentContext';

const MyResultsPage = () => {
  const navigate = useNavigate();
  const { results, loadingResults, resultsError, fetchResults } = useStudent();
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  const filteredResults = results.filter((res) => {
    const title = res.exam?.title || res.exam_title || res.title || '';
    return title.toLowerCase().includes(searchTerm.toLowerCase());
  });

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 text-uppercase tracking-wider">
              Academic Transcripts
            </span>
            <span className="badge bg-light text-secondary border">{results.length} Completed Assessments</span>
          </div>
          <h1 className="h4 mb-0 fw-bold">Exam History</h1>
          <p className="text-muted mb-0 small">Review past attempts, score summaries, question-level breakdown, and performance ranks.</p>
        </div>
        <button className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1.5 rounded-3" onClick={fetchResults}>
          <i className="bi bi-arrow-clockwise"></i> Refresh Results
        </button>
      </header>

      {/* Results Table */}
      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-header bg-white border-bottom p-3 d-flex justify-content-between align-items-center">
          <h6 className="mb-0 fw-bold">All Completed Examinations</h6>
          <div className="input-group input-group-sm" style={{ maxWidth: '280px' }}>
            <span className="input-group-text bg-light border-end-0"><i className="bi bi-search text-muted"></i></span>
            <input
              type="text"
              className="form-control border-start-0 bg-light"
              placeholder="Filter by exam title..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>

        <div className="card-body p-0">
          {loadingResults ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status"></div>
              <p className="text-muted mt-2 small">Loading exam transcripts...</p>
            </div>
          ) : resultsError ? (
            <div className="p-4">
              <div className="alert alert-danger rounded-3 mb-0"><i className="bi bi-exclamation-triangle-fill me-2"></i>{resultsError}</div>
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="text-center py-5 text-muted p-4">
              <div className="display-4 text-muted mb-2"><i className="bi bi-award"></i></div>
              <h6 className="fw-bold">No Completed Results</h6>
              <p className="small mb-0">You haven't completed any assessments yet. When you complete an exam, your scorecards and rankings will appear here.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="px-4 py-3 border-0">Exam Name</th>
                    <th className="py-3 border-0">Date Completed</th>
                    <th className="py-3 border-0">Score Obtained</th>
                    <th className="py-3 border-0">Percentage</th>
                    <th className="py-3 border-0">Pass / Fail Status</th>
                    <th className="py-3 border-0">Rank</th>
                    <th className="px-4 py-3 border-0 text-end">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResults.map((item, idx) => {
                    const score = item.score_obtained !== undefined ? item.score_obtained : item.score ?? 0;
                    const maxMarks = item.total_marks || item.exam?.total_marks || 100;
                    const pct = item.percentage !== undefined ? item.percentage : maxMarks ? ((score / maxMarks) * 100).toFixed(1) : 0;
                    const isPassed = item.is_passed !== undefined ? item.is_passed : pct >= (item.passing_percentage || 40);
                    const rank = item.rank || `#${idx + 1}`;
                    const attemptId = item.attempt_id || item.id;

                    return (
                      <tr key={item.id || idx}>
                        <td className="px-4 py-3">
                          <div className="fw-bold text-dark">{item.exam?.title || item.exam_title || `Exam #${item.exam_id || idx + 1}`}</div>
                          <small className="text-muted">{item.exam?.subject || item.subject || 'General Assessment'}</small>
                        </td>
                        <td className="py-3 small text-muted">
                          {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : 'Recent'}
                        </td>
                        <td className="py-3 fw-bold text-dark">
                          {score} / {maxMarks}
                        </td>
                        <td className="py-3">
                          <span className="fw-bold text-primary">{pct}%</span>
                        </td>
                        <td className="py-3">
                          {isPassed ? (
                            <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25">
                              <i className="bi bi-check-circle-fill me-1"></i> PASSED
                            </span>
                          ) : (
                            <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25">
                              <i className="bi bi-x-circle-fill me-1"></i> FAILED
                            </span>
                          )}
                        </td>
                        <td className="py-3">
                          <span className="badge bg-light text-dark border fw-bold">{rank}</span>
                        </td>
                        <td className="px-4 py-3 text-end">
                          <button
                            className="btn btn-sm btn-outline-primary rounded-3 d-inline-flex align-items-center gap-1"
                            onClick={() => navigate(`/results/${attemptId}`)}
                          >
                            <i className="bi bi-clipboard2-data"></i> Full Scorecard
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyResultsPage;
