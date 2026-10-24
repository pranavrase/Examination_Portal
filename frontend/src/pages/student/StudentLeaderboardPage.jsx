import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useStudent } from '../../context/StudentContext';

const StudentLeaderboardPage = () => {
  const { user } = useAuth();
  const { leaderboard, loadingLeaderboard, leaderboardError, fetchLeaderboard, exams, fetchExams } = useStudent();
  const [anonymize, setAnonymize] = useState(false);
  const [selectedExam, setSelectedExam] = useState('all');

  const currentUserName = user?.full_name || user?.name || 'Current Student';

  useEffect(() => {
    fetchExams();
    fetchLeaderboard();
  }, [fetchExams, fetchLeaderboard]);

  useEffect(() => {
    if (selectedExam === 'all' || selectedExam === '') {
      fetchLeaderboard(null);
    } else {
      const examId = parseInt(selectedExam);
      if (!isNaN(examId)) {
        fetchLeaderboard(examId);
      }
    }
  }, [selectedExam, fetchLeaderboard]);

  // Use real leaderboard data or empty array if loading/error
  const leaderboardData = leaderboard?.rankings || [];
  const totalCandidates = leaderboard?.total_candidates || 0;
  const examTitle = leaderboard?.exam_title || 'Overall Rankings';

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-warning text-dark text-uppercase tracking-wider">Honor Roll</span>
            <span className="badge bg-light text-secondary border">Academic Leaderboard</span>
          </div>
          <h1 className="h4 mb-0 fw-bold">Rankings & Merit Leaderboard</h1>
          <p className="text-muted mb-0 small">Compare performance metrics across cohorts, view percentiles, and track your class standing.</p>
        </div>

        {/* Anonymity Toggle */}
        <div className="form-check form-switch bg-white p-2 px-3 rounded-3 border shadow-sm d-flex align-items-center gap-2">
          <input
            className="form-check-input ms-0"
            type="checkbox"
            id="anonSwitch"
            checked={anonymize}
            onChange={(e) => setAnonymize(e.target.checked)}
          />
          <label className="form-check-label small fw-semibold text-dark user-select-none mb-0" htmlFor="anonSwitch">
            <i className="bi bi-incognito me-1"></i> Anonymize Peer Names
          </label>
        </div>
      </header>

      {/* Current Student Standing Banner */}
      {(() => {
        const myRanking = leaderboardData.find(item => item.is_me);
        if (!myRanking) return null;
        
        const percentile = myRanking.percentile || 0;
        const tier = percentile >= 90 ? 'Top 10% Tier' : percentile >= 75 ? 'Top 25% Tier' : percentile >= 50 ? 'Top 50% Tier' : 'Keep Improving';
        
        return (
          <div className="card shadow-sm border-0 rounded-4 mb-4" style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)', color: '#ffffff' }}>
            <div className="card-body p-4">
              <div className="row align-items-center g-3">
                <div className="col-12 col-md-4">
                  <div className="d-flex align-items-center gap-3">
                    <div className="p-3 bg-white bg-opacity-10 rounded-circle text-warning fs-3">
                      <i className="bi bi-trophy-fill"></i>
                    </div>
                    <div>
                      <div className="text-white-50 small">Your Standing</div>
                      <h4 className="fw-bold mb-0 text-white">Rank #{myRanking.rank} of {totalCandidates}</h4>
                    </div>
                  </div>
                </div>
                <div className="col-6 col-md-3 text-md-center">
                  <div className="text-white-50 small">Percentile Score</div>
                  <div className="fw-bold fs-4 text-warning">{percentile.toFixed(1)}%</div>
                </div>
                <div className="col-6 col-md-3 text-md-center">
                  <div className="text-white-50 small">Score</div>
                  <div className="fw-bold fs-4 text-success">{myRanking.score.toFixed(0)}</div>
                </div>
                <div className="col-12 col-md-2 text-md-end">
                  <span className="badge bg-success bg-opacity-25 text-white border border-success px-3 py-2">
                    {tier}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Leaderboard Table */}
      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-header bg-white border-bottom p-3 d-flex justify-content-between align-items-center">
          <h6 className="mb-0 fw-bold">{examTitle}</h6>
          <select
            className="form-select form-select-sm bg-light"
            style={{ maxWidth: '250px' }}
            value={selectedExam}
            onChange={(e) => setSelectedExam(e.target.value)}
          >
            <option value="all">All Examinations</option>
            {exams.filter(e => e.status === 'completed' || e.status === 'available').map(exam => (
              <option key={exam.id} value={exam.id}>{exam.title}</option>
            ))}
          </select>
        </div>

        <div className="card-body p-0">
          {loadingLeaderboard ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status"></div>
              <p className="text-muted mt-2 small">Loading leaderboard data...</p>
            </div>
          ) : leaderboardError ? (
            <div className="p-4">
              <div className="alert alert-danger rounded-3 mb-0">
                <i className="bi bi-exclamation-triangle-fill me-2"></i>
                {leaderboardError}
              </div>
            </div>
          ) : leaderboardData.length === 0 ? (
            <div className="text-center py-5 text-muted p-4">
              <div className="display-4 text-muted mb-2"><i className="bi bi-trophy"></i></div>
              <h6 className="fw-bold">No Rankings Available</h6>
              <p className="small mb-0">Leaderboard data will appear once students complete examinations.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="px-4 py-3 border-0" style={{ width: '80px' }}>Rank</th>
                    <th className="py-3 border-0">Candidate</th>
                    <th className="py-3 border-0">Roll / ID</th>
                    <th className="py-3 border-0">Score</th>
                    <th className="py-3 border-0">Percentile</th>
                    <th className="py-3 border-0">Accuracy</th>
                    <th className="px-4 py-3 border-0 text-end">Completion Time</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboardData.map((row) => {
                    const isGold = row.rank === 1;
                    const isSilver = row.rank === 2;
                    const isBronze = row.rank === 3;
                    const displayName = row.is_me ? `${row.name} (You)` : anonymize ? `Candidate #${row.roll.slice(-3)}` : row.name;

                    return (
                      <tr key={`${row.rank}-${row.student_id}`} className={row.is_me ? 'table-primary bg-opacity-25 fw-semibold' : ''}>
                        <td className="px-4 py-3">
                          {isGold && <span className="badge bg-warning text-dark"><i className="bi bi-trophy-fill me-1"></i> #1</span>}
                          {isSilver && <span className="badge bg-secondary text-white"><i className="bi bi-award-fill me-1"></i> #2</span>}
                          {isBronze && <span className="badge bg-danger bg-opacity-75 text-white"><i className="bi bi-award-fill me-1"></i> #3</span>}
                          {!isGold && !isSilver && !isBronze && <span className="text-muted fw-bold">#{row.rank}</span>}
                        </td>
                        <td className="py-3">
                          <div className={`fw-bold ${row.is_me ? 'text-primary' : 'text-dark'}`}>{displayName}</div>
                        </td>
                        <td className="py-3 font-monospace small text-muted">
                          {anonymize && !row.is_me ? '***' + row.roll.slice(-4) : row.roll}
                        </td>
                        <td className="py-3 fw-bold text-dark">{row.score.toFixed(0)}</td>
                        <td className="py-3"><span className="badge bg-info bg-opacity-10 text-info border border-info border-opacity-25">{row.percentile.toFixed(1)}%ile</span></td>
                        <td className="py-3 text-success fw-bold">{row.accuracy || 'N/A'}</td>
                        <td className="px-4 py-3 text-end text-muted small">{row.time || 'N/A'}</td>
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

export default StudentLeaderboardPage;
