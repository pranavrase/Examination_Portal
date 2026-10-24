import React, { useEffect, useState } from 'react';
import { getExaminerRankings, getMyExams } from '../../api/examinerApi';

const ExaminerRankingsPanel = () => {
  const [rankings, setRankings] = useState([]);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('score_desc');
  const [search, setSearch] = useState('');
  const [examFilter, setExamFilter] = useState('');

  const fetchRankings = async () => {
    try {
      setLoading(true);
      const params = { sort_by: sortBy };
      if (examFilter) {
        params.exam_id = examFilter;
      }
      const data = await getExaminerRankings(params);
      setRankings(data || []);
    } catch (err) {
      console.error('Failed to load rankings:', err);
      setRankings([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchExams = async () => {
    try {
      const data = await getMyExams();
      setExams(Array.isArray(data) ? data : data?.items || []);
    } catch (err) {
      console.error('Failed to load exams:', err);
      setExams([]);
    }
  };

  useEffect(() => {
    fetchExams();
    fetchRankings();
  }, [sortBy, examFilter]);

  const sortedRankings = [...rankings].sort((a, b) => {
    if (sortBy === 'score_desc') return b.score - a.score;
    if (sortBy === 'score_asc') return a.score - b.score;
    if (sortBy === 'time_asc') return parseInt(a.time_taken) - parseInt(b.time_taken);
    return 0;
  });

  const filtered = sortedRankings.filter((r) => {
    const term = search.toLowerCase();
    return r.candidate_name?.toLowerCase().includes(term) || r.candidate_id?.toLowerCase().includes(term);
  });

  const getRankMedal = (rank) => {
    if (rank === 1) return <span className="badge bg-warning text-dark rounded-pill px-2.5 py-1 fw-bold fs-6">🥇 #1</span>;
    if (rank === 2) return <span className="badge bg-secondary text-white rounded-pill px-2.5 py-1 fw-bold fs-6">🥈 #2</span>;
    if (rank === 3) return <span className="badge bg-danger text-white rounded-pill px-2.5 py-1 fw-bold fs-6">🥉 #3</span>;
    return <span className="badge bg-light text-dark border rounded-pill px-2.5 py-1 fw-semibold">#{rank}</span>;
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="examiner-rankings-panel">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
          <div>
            <span className="badge bg-warning text-dark mb-1 text-uppercase fw-semibold">
              Merit List & Leaderboard
            </span>
            <h5 className="fw-bold mb-0 text-dark">Candidate Rankings & Percentiles</h5>
            <p className="text-muted small mb-0">Live ranked leaderboards with completion speed, accuracy rate, and percentile calculations</p>
          </div>

          <div className="d-flex align-items-center gap-2">
            <select
              className="form-select form-select-sm bg-light rounded-3"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="score_desc">Sort by: Highest Score</option>
              <option value="score_asc">Sort by: Lowest Score</option>
              <option value="time_asc">Sort by: Fastest Completion</option>
            </select>
          </div>
        </div>

        {/* Top 3 Podium Highlights */}
        <div className="row g-3 mb-4">
          {rankings.length > 0 ? (
            rankings.slice(0, 3).map((top, idx) => (
              <div key={top.rank} className="col-md-4">
                <div
                  className={`card border-0 shadow-sm rounded-4 p-3 text-center h-100 ${
                    idx === 0 ? 'bg-warning bg-opacity-10 border-warning border-2' : 'bg-light'
                  }`}
                >
                  <div className="mb-2">{getRankMedal(top.rank)}</div>
                  <h6 className="fw-bold text-dark mb-1">{top.candidate_name}</h6>
                  <div className="text-muted small font-monospace mb-2">{top.candidate_id}</div>
                  <div className="d-flex justify-content-center align-items-baseline gap-2">
                    <span className="fs-4 fw-bold text-primary">{top.score} pts</span>
                    <span className="badge bg-info-subtle text-info rounded-pill">{top.percentile}th %ile</span>
                  </div>
                  <div className="text-muted small mt-1">Time: {top.time_taken}</div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-12">
              <div className="text-center py-4 text-muted">
                <i className="bi bi-trophy display-5 d-block mb-2 opacity-30" />
                <h6 className="fw-semibold">No rankings available</h6>
                <p className="small mb-0">Rankings will appear after candidates complete exams.</p>
              </div>
            </div>
          )}
        </div>

        {/* Search */}
        <div className="row g-2 mb-3">
          <div className="col-12 col-md-6">
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0">
                <i className="bi bi-search text-muted" />
              </span>
              <input
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search candidates on leaderboard..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="col-12 col-md-6">
            <select
              className="form-select bg-light"
              value={examFilter}
              onChange={(e) => setExamFilter(e.target.value)}
            >
              <option value="">All Examinations</option>
              {exams.map((exam) => (
                <option key={exam.id} value={exam.id}>
                  {exam.title}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="card-body p-0">
        {loading ? (
          <div className="p-5 text-center">
            <div className="spinner-border text-warning" role="status" />
            <p className="text-muted small mt-2">Calculating ranks and merit standing...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-trophy display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">No rankings available</h6>
            <p className="small mb-0">Rankings will appear after candidates complete exams.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3 fw-semibold text-muted small">STANDINGS</th>
                  <th className="py-3 fw-semibold text-muted small">CANDIDATE</th>
                  <th className="py-3 fw-semibold text-muted small">ID / ROLL NO</th>
                  <th className="py-3 fw-semibold text-muted small">SCORE</th>
                  <th className="py-3 fw-semibold text-muted small">PERCENTILE</th>
                  <th className="py-3 fw-semibold text-muted small">ACCURACY</th>
                  <th className="py-3 fw-semibold text-muted small">COMPLETION TIME</th>
                  <th className="pe-4 py-3 fw-semibold text-muted small text-end">STATUS</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.rank} className="border-top">
                    <td className="ps-4 py-3">{getRankMedal(r.rank)}</td>
                    <td className="py-3">
                      <div className="fw-semibold text-dark">{r.candidate_name}</div>
                    </td>
                    <td className="text-muted small font-monospace">{r.candidate_id}</td>
                    <td>
                      <span className="fw-bold text-primary">{r.score}</span>
                      {r.total_marks != null ? (
                        <span className="text-muted small"> / {r.total_marks} ({r.percentage}%)</span>
                      ) : (
                        <span className="text-muted small"> ({r.percentage}%)</span>
                      )}
                    </td>
                    <td>
                      <span className="badge bg-info-subtle text-info rounded-pill px-2.5 py-1">
                        {r.percentile}th %ile
                      </span>
                    </td>
                    <td className="text-muted small fw-semibold">{r.accuracy}</td>
                    <td className="text-muted small">
                      <i className="bi bi-clock me-1 text-muted" />
                      {r.time_taken}
                    </td>
                    <td className="pe-4 text-end">
                      <span className={`badge ${r.status === 'Passed' ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'} rounded-pill px-3`}>
                        {r.status}
                      </span>
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

export default ExaminerRankingsPanel;
