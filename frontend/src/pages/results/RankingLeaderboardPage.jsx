import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getExamRankings } from '../../api/resultApi';

// ── Helpers ──────────────────────────────────────────────────────────────────
const pct = (score, total) => {
  if (!total || total === 0) return null;
  return ((score / total) * 100).toFixed(1);
};

const getRankMedal = (rank) => {
  if (rank === 1) return { icon: 'bi-trophy-fill', color: '#f59e0b' };
  if (rank === 2) return { icon: 'bi-award-fill', color: '#94a3b8' };
  if (rank === 3) return { icon: 'bi-award-fill', color: '#b45309' };
  return null;
};

// ── Skeleton Loader ───────────────────────────────────────────────────────────
const SkeletonRow = () => (
  <tr>
    {[1, 2, 3, 4].map((i) => (
      <td key={i}>
        <div className="placeholder-glow">
          <span className="placeholder col-10 rounded" />
        </div>
      </td>
    ))}
  </tr>
);

// ── Error State ───────────────────────────────────────────────────────────────
const ErrorState = ({ code, message, onRetry }) => {
  const messages = {
    401: 'You must be logged in to view rankings.',
    403: 'You are not authorized to view rankings for this exam.',
    404: 'Exam or rankings not found.',
    500: 'A server error occurred. Please try again later.',
  };
  return (
    <div className="d-flex flex-column align-items-center justify-content-center py-5 text-center">
      <i className="bi bi-exclamation-triangle-fill text-warning fs-1 mb-3" />
      <h5 className="fw-bold mb-2">{code ? `Error ${code}` : 'Something went wrong'}</h5>
      <p className="text-muted mb-4" style={{ maxWidth: 380 }}>
        {messages[code] || message || 'Failed to load rankings.'}
      </p>
      {onRetry && (
        <button className="btn btn-primary rounded-3" onClick={onRetry}>
          <i className="bi bi-arrow-clockwise me-2" />Retry
        </button>
      )}
    </div>
  );
};

// ── Empty State ───────────────────────────────────────────────────────────────
const EmptyState = () => (
  <div className="d-flex flex-column align-items-center justify-content-center py-5 text-center text-muted">
    <i className="bi bi-people fs-1 mb-3 opacity-40" />
    <h5 className="fw-semibold mb-1">No Rankings Available</h5>
    <p className="small mb-0">Rankings haven't been generated for this exam yet.</p>
  </div>
);

// ── Rank Badge ────────────────────────────────────────────────────────────────
const RankBadge = ({ rank }) => {
  const medal = getRankMedal(rank);
  if (medal) {
    return (
      <span className="d-flex align-items-center gap-1 fw-bold" style={{ color: medal.color }}>
        <i className={`bi ${medal.icon}`} />
        {rank}
      </span>
    );
  }
  return <span className="fw-semibold text-muted">{rank}</span>;
};

// ── Main Leaderboard Page ────────────────────────────────────────────────────
const RankingLeaderboardPage = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const { user, role } = useAuth();

  const [rankings, setRankings] = useState([]);
  const [examName, setExamName] = useState('');
  const [loading, setLoading] = useState(true);
  const [errorCode, setErrorCode] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [searchQuery, setSearchQuery] = useState('');

  const ITEMS_PER_PAGE = 20;

  // The current logged-in user's ID or username for highlighting
  const currentUserId = user?.id || user?.user_id;
  const currentUsername = (user?.username || user?.name || user?.email || '').toLowerCase();

  const fetchRankings = useCallback(async (page = 1) => {
    if (!examId) return;
    setLoading(true);
    setErrorCode(null);
    setErrorMsg('');
    try {
      const data = await getExamRankings(examId, { page, limit: ITEMS_PER_PAGE });

      // Handle both array and paginated response formats
      let rankList = [];
      if (Array.isArray(data)) {
        rankList = data;
        setTotalPages(1);
      } else if (data && typeof data === 'object') {
        rankList = data.rankings || data.items || data.data || [];
        setTotalPages(data.total_pages || data.totalPages || 1);
        setExamName(data.exam_name || data.exam_title || '');
      }

      setRankings(rankList);
    } catch (err) {
      const status = err?.response?.status;
      setErrorCode(status || null);
      setErrorMsg(err?.response?.data?.detail || err.message || 'Failed to load rankings.');
    } finally {
      setLoading(false);
    }
  }, [examId]);

  useEffect(() => {
    fetchRankings(currentPage);
  }, [fetchRankings, currentPage]);

  // ── Identify whether a row is the current user ──────────────────────────
  const isCurrentUser = (entry) => {
    if (!entry) return false;
    if (currentUserId && (entry.student_id === currentUserId || entry.user_id === currentUserId)) return true;
    const entryName = (entry.student_name || entry.username || entry.name || '').toLowerCase();
    return entryName && entryName === currentUsername;
  };

  // ── Client-side search filter ────────────────────────────────────────────
  const filtered = rankings.filter((entry) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (entry.student_name || entry.username || entry.name || '').toLowerCase().includes(q) ||
      String(entry.rank || '').includes(q)
    );
  });

  // ── Current user rank lookup ─────────────────────────────────────────────
  const myEntry = rankings.find(isCurrentUser);

  return (
    <div className="bg-light min-vh-100">
      <div className="container py-5" style={{ maxWidth: 900 }}>

        {/* ── Breadcrumb ──────────────────────────────────────────────────── */}
        <nav aria-label="breadcrumb" className="mb-3">
          <ol className="breadcrumb small">
            <li className="breadcrumb-item">
              <Link to={`/${role || 'student'}`} className="text-decoration-none">Dashboard</Link>
            </li>
            <li className="breadcrumb-item active" aria-current="page">Leaderboard</li>
          </ol>
        </nav>

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="card border-0 shadow rounded-4 mb-4 overflow-hidden">
          <div style={{ height: 6, background: 'linear-gradient(90deg,#f59e0b,#ef4444,#8b5cf6)' }} />
          <div className="card-body p-4">
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div>
                <span className="badge bg-warning bg-opacity-10 text-warning fw-semibold mb-2" style={{ fontSize: '0.7rem', letterSpacing: '0.08em' }}>
                  <i className="bi bi-trophy me-1" />LEADERBOARD
                </span>
                <h2 className="fw-bold mb-1">
                  {examName || `Exam #${examId}`} Rankings
                </h2>
                {!loading && (
                  <p className="text-muted mb-0 small">
                    {rankings.length} student{rankings.length !== 1 ? 's' : ''} ranked
                  </p>
                )}
              </div>

              {/* ── My Rank Highlight ───────────────────────────────────── */}
              {myEntry && (
                <div className="card border-0 rounded-4 text-center px-4 py-3"
                  style={{ background: 'linear-gradient(135deg,#6366f115,#8b5cf615)', border: '1px solid #6366f125', minWidth: 140 }}>
                  <p className="text-muted small mb-0 fw-semibold">YOUR RANK</p>
                  <h2 className="fw-bold mb-0" style={{ color: '#6366f1' }}>
                    #{myEntry.rank}
                  </h2>
                  {typeof myEntry.score === 'number' && (
                    <p className="text-muted small mb-0">{myEntry.score} pts</p>
                  )}
                </div>
              )}
            </div>

            {/* ── Refresh + Search Controls ───────────────────────────── */}
            <div className="d-flex flex-wrap gap-2 mt-3 align-items-center">
              <div className="input-group input-group-sm" style={{ maxWidth: 280 }}>
                <span className="input-group-text bg-white border-end-0">
                  <i className="bi bi-search text-muted" />
                </span>
                <input
                  type="text"
                  className="form-control border-start-0"
                  placeholder="Search student…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <button
                className="btn btn-sm btn-outline-secondary rounded-3 ms-auto d-flex align-items-center gap-1"
                onClick={() => fetchRankings(currentPage)}
                disabled={loading}
              >
                <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* ── Main Leaderboard Card ────────────────────────────────────────── */}
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-body p-0">
            {loading ? (
              <div className="table-responsive p-3">
                <table className="table table-hover mb-0">
                  <thead className="table-light">
                    <tr>
                      <th>#</th>
                      <th>Student</th>
                      <th>Score</th>
                      <th>%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}
                  </tbody>
                </table>
              </div>
            ) : errorCode || (!rankings.length && !loading && errorMsg) ? (
              <ErrorState code={errorCode} message={errorMsg} onRetry={() => fetchRankings(currentPage)} />
            ) : filtered.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead>
                    <tr className="table-light">
                      <th className="ps-4 py-3 text-uppercase text-muted fw-semibold" style={{ fontSize: '0.7rem', letterSpacing: '0.06em', width: '60px' }}>#</th>
                      <th className="py-3 text-uppercase text-muted fw-semibold" style={{ fontSize: '0.7rem', letterSpacing: '0.06em' }}>Student</th>
                      <th className="py-3 text-uppercase text-muted fw-semibold" style={{ fontSize: '0.7rem', letterSpacing: '0.06em' }}>Score</th>
                      <th className="py-3 text-uppercase text-muted fw-semibold d-none d-md-table-cell" style={{ fontSize: '0.7rem', letterSpacing: '0.06em' }}>Percentage</th>
                      <th className="py-3 text-uppercase text-muted fw-semibold d-none d-lg-table-cell" style={{ fontSize: '0.7rem', letterSpacing: '0.06em' }}>Time Taken</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((entry, idx) => {
                      const isMine = isCurrentUser(entry);
                      const rank = entry.rank ?? idx + 1;
                      const score = entry.score ?? entry.marks_obtained ?? entry.total_score;
                      const total = entry.total_marks ?? entry.max_score;
                      const entryPct = pct(score, total);
                      const name = entry.student_name || entry.username || entry.name || `Student #${rank}`;
                      const timeTaken = entry.time_taken || entry.duration;

                      return (
                        <tr
                          key={entry.student_id || entry.user_id || idx}
                          className={isMine ? 'table-primary' : ''}
                          style={isMine ? { fontWeight: 600 } : {}}
                        >
                          {/* Rank */}
                          <td className="ps-4">
                            <RankBadge rank={rank} />
                          </td>

                          {/* Student name + You badge */}
                          <td>
                            <div className="d-flex align-items-center gap-2">
                              <div
                                className={`rounded-circle d-flex align-items-center justify-content-center text-white fw-bold flex-shrink-0 ${isMine ? 'bg-primary' : 'bg-secondary bg-opacity-50'}`}
                                style={{ width: 36, height: 36, fontSize: '0.85rem' }}
                              >
                                {name.charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <div className={`fw-semibold ${isMine ? 'text-primary' : ''}`}>
                                  {isMine ? 'You' : name}
                                </div>
                                {isMine && (
                                  <span className="badge bg-primary bg-opacity-15 text-primary" style={{ fontSize: '0.65rem' }}>
                                    Your position
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>

                          {/* Score */}
                          <td>
                            <span className="fw-bold">{score ?? '—'}</span>
                            {total != null && (
                              <span className="text-muted small"> / {total}</span>
                            )}
                          </td>

                          {/* Percentage */}
                          <td className="d-none d-md-table-cell">
                            {entryPct !== null ? (
                              <div className="d-flex align-items-center gap-2">
                                <div className="progress flex-grow-1" style={{ height: 6, maxWidth: 80 }}>
                                  <div
                                    className={`progress-bar ${parseFloat(entryPct) >= 60 ? 'bg-success' : 'bg-danger'}`}
                                    style={{ width: `${entryPct}%` }}
                                  />
                                </div>
                                <span className="small fw-semibold">{entryPct}%</span>
                              </div>
                            ) : '—'}
                          </td>

                          {/* Time taken */}
                          <td className="d-none d-lg-table-cell text-muted small">
                            {timeTaken ?? '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* ── Pagination ───────────────────────────────────────────────── */}
            {!loading && totalPages > 1 && (
              <div className="d-flex justify-content-center align-items-center gap-2 p-4 border-top">
                <button
                  className="btn btn-sm btn-outline-secondary rounded-3"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => p - 1)}
                >
                  <i className="bi bi-chevron-left" /> Prev
                </button>
                <span className="text-muted small">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  className="btn btn-sm btn-outline-secondary rounded-3"
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage((p) => p + 1)}
                >
                  Next <i className="bi bi-chevron-right" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── Bottom Actions ──────────────────────────────────────────────── */}
        <div className="d-flex flex-wrap gap-2 justify-content-center mt-4">
          <button className="btn btn-outline-secondary rounded-3" onClick={() => navigate(-1)}>
            <i className="bi bi-arrow-left me-2" />Go Back
          </button>
          <Link to={`/${role || 'student'}`} className="btn btn-primary rounded-3">
            <i className="bi bi-house me-2" />Dashboard
          </Link>
        </div>
      </div>

      {/* Spin animation for refresh icon */}
      <style>{`
        @keyframes spin { from { transform:rotate(0deg); } to { transform:rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
};

export default RankingLeaderboardPage;
