import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const ExamHistoryTable = ({ results, loading, error }) => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading results...</span>
        </div>
        <p className="text-muted mt-2">Loading exam history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger rounded-3" role="alert">
        <i className="bi bi-exclamation-triangle-fill me-2"></i> {error}
      </div>
    );
  }

  if (!results || results.length === 0) {
    return (
      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-body p-5 text-center">
          <div className="display-4 text-muted mb-3">
            <i className="bi bi-clipboard2-x"></i>
          </div>
          <h5 className="text-muted">No Exam History</h5>
          <p className="text-secondary mb-0">You have not completed any exams yet.</p>
        </div>
      </div>
    );
  }

  const filteredResults = results.filter(result => 
    result.exam_title?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    result.exam?.title?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="card shadow-sm border-0 rounded-4">
      <div className="card-header bg-white border-bottom p-4 d-flex justify-content-between align-items-center">
        <h5 className="mb-0 fw-bold">Exam History</h5>
        <div className="input-group" style={{ maxWidth: '250px' }}>
          <span className="input-group-text bg-light border-end-0">
            <i className="bi bi-search text-muted"></i>
          </span>
          <input 
            type="text" 
            className="form-control border-start-0 bg-light" 
            placeholder="Search history..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>
      <div className="card-body p-0">
        {filteredResults.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <p className="mb-0">No results match your search.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th className="px-4 py-3 border-0">Exam Name</th>
                  <th className="py-3 border-0">Date Completed</th>
                  <th className="py-3 border-0">Score</th>
                  <th className="py-3 border-0">Percentage</th>
                  <th className="py-3 border-0">Status</th>
                  <th className="px-4 py-3 border-0 text-end">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((result, idx) => {
                  const title = result.exam_title || result.exam?.title || 'Unknown Exam';
                  const date = result.submitted_at || result.completed_at || result.created_at;
                  const score = result.score_obtained !== undefined ? result.score_obtained : result.score;
                  const total = result.total_marks || result.exam?.total_marks || 100;
                  const percentage = result.percentage || (score !== undefined && total ? (score / total) * 100 : 0);
                  const isPass = result.is_pass !== undefined ? result.is_pass : (percentage >= (result.exam?.passing_percentage || 40));
                  
                  return (
                    <tr key={result.id || idx}>
                      <td className="px-4 py-3">
                        <div className="fw-semibold text-dark">{title}</div>
                      </td>
                      <td className="py-3">
                        {date ? new Date(date).toLocaleDateString(undefined, {
                          year: 'numeric', month: 'short', day: 'numeric'
                        }) : '--'}
                      </td>
                      <td className="py-3 fw-semibold">
                        {score !== undefined ? `${score} / ${total}` : 'Pending'}
                      </td>
                      <td className="py-3">
                        {score !== undefined ? (
                          <div className="d-flex align-items-center gap-2">
                            <div className="progress flex-grow-1" style={{ height: '6px', minWidth: '60px' }}>
                              <div 
                                className={`progress-bar ${isPass ? 'bg-success' : 'bg-danger'}`} 
                                role="progressbar" 
                                style={{ width: `${percentage}%` }} 
                                aria-valuenow={percentage} 
                                aria-valuemin="0" 
                                aria-valuemax="100"
                              ></div>
                            </div>
                            <span className="small">{percentage.toFixed(1)}%</span>
                          </div>
                        ) : '--'}
                      </td>
                      <td className="py-3">
                        {score !== undefined ? (
                          isPass ? 
                            <span className="badge bg-success bg-opacity-10 text-success"><i className="bi bi-check-circle me-1"></i> Pass</span> : 
                            <span className="badge bg-danger bg-opacity-10 text-danger"><i className="bi bi-x-circle me-1"></i> Fail</span>
                        ) : (
                          <span className="badge bg-warning bg-opacity-10 text-warning"><i className="bi bi-hourglass me-1"></i> Evaluating</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-end">
                        <button 
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => navigate(`/student/result/${result.id}`)}
                        >
                          <i className="bi bi-eye"></i> View
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
  );
};

export default ExamHistoryTable;
