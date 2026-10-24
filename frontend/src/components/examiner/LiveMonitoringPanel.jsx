import React, { useEffect, useState, useRef, useCallback } from 'react';
import { getLiveMonitoring } from '../../api/examinerApi';

// ─── Per-session countdown hook ────────────────────────────────────────────────
// Returns a MM:SS string that ticks every second for in-progress sessions.
// For completed/submitted sessions it always returns '00:00'.
// startedAt  – ISO string from the backend (UTC, no tz suffix)
// durationMinutes – integer from exam settings
// status     – 'In Progress' | 'Completed'
function useTimeLeft(startedAt, durationMinutes, status) {
  const calcSecsLeft = useCallback(() => {
    if (status !== 'In Progress') return 0;
    if (!startedAt || durationMinutes == null) return null; // null = unknown
    // Backend stores naive UTC datetimes (no 'Z'), so we append 'Z' to parse correctly.
    const isoStr = startedAt.endsWith('Z') ? startedAt : startedAt + 'Z';
    const endMs = new Date(isoStr).getTime() + durationMinutes * 60 * 1000;
    return Math.max(0, Math.floor((endMs - Date.now()) / 1000));
  }, [startedAt, durationMinutes, status]);

  const [secsLeft, setSecsLeft] = useState(calcSecsLeft);

  // Recalculate when session data refreshes (new startedAt / durationMinutes)
  useEffect(() => {
    setSecsLeft(calcSecsLeft());
  }, [calcSecsLeft]);

  // Tick every second only for in-progress sessions
  useEffect(() => {
    if (status !== 'In Progress') return;
    const id = setInterval(() => {
      setSecsLeft(calcSecsLeft());
    }, 1000);
    return () => clearInterval(id);
  }, [status, calcSecsLeft]);

  if (secsLeft === null) return null; // insufficient data
  const m = Math.floor(secsLeft / 60);
  const s = secsLeft % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

// ─── Individual session row ────────────────────────────────────────────────────
const SessionRow = ({ s, getActivityBadge }) => {
  const timeLeft = useTimeLeft(s.started_at, s.duration_minutes, s.status);

  // Determine if the timer has expired (shows 00:00 and session should look completed)
  const isExpired = timeLeft === '00:00' && s.status === 'In Progress';
  const effectiveStatus = isExpired ? 'Completed' : s.status;

  return (
    <tr key={s.id} className="border-top">
      <td className="ps-4 py-3">
        <div className="d-flex align-items-center gap-2">
          <div
            className="rounded-circle bg-dark text-white fw-bold d-flex align-items-center justify-content-center"
            style={{ width: 32, height: 32, fontSize: '0.8rem' }}
          >
            {s.candidate_name?.charAt(0) || 'C'}
          </div>
          <div>
            <div className="fw-semibold text-dark">{s.candidate_name}</div>
            <div className="text-muted small font-monospace">{s.roll_number}</div>
          </div>
        </div>
      </td>
      <td className="text-muted small">{s.exam_title}</td>
      <td>
        <span
          className={`badge ${effectiveStatus === 'Completed'
            ? 'bg-success-subtle text-success border border-success-subtle'
            : 'bg-primary-subtle text-primary border border-primary-subtle'
          } rounded-pill px-2.5 py-1`}
        >
          {effectiveStatus}
        </span>
      </td>
      <td>
        <div className="d-flex align-items-center gap-1.5 fw-semibold text-dark small">
          <i className={`bi bi-clock-history ${effectiveStatus === 'Completed' ? 'text-success' : 'text-danger'}`} />
          {effectiveStatus === 'Completed' ? (
            <span className="text-success">00:00</span>
          ) : timeLeft !== null ? (
            <span className={timeLeft === '00:00' ? 'text-success' : timeLeft <= '05:00' ? 'text-warning' : 'text-dark'}>
              {timeLeft}
            </span>
          ) : (
            <span className="text-muted">—</span>
          )}
        </div>
      </td>
      <td>
        <div className="d-flex flex-column gap-1">
          <div className="d-flex justify-content-between small text-muted">
            <span>{s.questions_answered} / {s.total_questions} answered</span>
            <span className="fw-bold text-dark">{s.progress_percentage}%</span>
          </div>
          <div className="progress" style={{ height: 6 }}>
            <div
              className={`progress-bar ${s.progress_percentage === 100 ? 'bg-success' : 'bg-primary'}`}
              role="progressbar"
              style={{ width: `${s.progress_percentage}%` }}
            />
          </div>
        </div>
      </td>
      <td>
        <span className={`badge ${s.tab_switches > 0 ? 'bg-danger text-white' : 'bg-light text-muted border'} px-2.5 py-1 rounded-pill`}>
          {s.tab_switches} events
        </span>
      </td>
      <td className="pe-4 text-end">
        {getActivityBadge(s.activity_status)}
      </td>
    </tr>
  );
};

// ─── Main panel ────────────────────────────────────────────────────────────────
const LiveMonitoringPanel = () => {
  const [data, setData] = useState({ sessions: [], active_candidates_count: 0, completed_count: 0, flagged_count: 0 });
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const fetchMonitoring = async () => {
    try {
      const res = await getLiveMonitoring();
      setData(res || { sessions: [], active_candidates_count: 0, completed_count: 0, flagged_count: 0 });
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch live monitoring:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoring();
    if (!autoRefresh) return;
    const interval = setInterval(fetchMonitoring, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getActivityBadge = (act) => {
    switch (act?.toLowerCase()) {
      case 'normal':
        return <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3"><i className="bi bi-shield-check me-1" /> Normal</span>;
      case 'tab switch alert':
        return <span className="badge bg-warning-subtle text-warning border border-warning-subtle rounded-pill px-3"><i className="bi bi-exclamation-triangle-fill me-1" /> Tab Switch</span>;
      case 'suspicious / multiple blur':
        return <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-3"><i className="bi bi-shield-slash-fill me-1" /> Flagged</span>;
      default:
        return <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill px-3">{act}</span>;
    }
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="live-monitoring-panel">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
          <div>
            <div className="d-flex align-items-center gap-2 mb-1">
              <span className="badge bg-danger text-white rounded-pill px-2.5 py-1 text-uppercase tracking-wider d-flex align-items-center gap-1.5">
                <span className="spinner-grow spinner-grow-sm" style={{ width: '0.45rem', height: '0.45rem' }} />
                Live Proctoring Feed
              </span>
              <span className="text-muted small">Updated: {lastUpdated.toLocaleTimeString()}</span>
            </div>
            <h5 className="fw-bold mb-0 text-dark">Real-time Examination Monitoring</h5>
            <p className="text-muted small mb-0">Track active candidate sessions, progress, remaining time, and proctoring alerts</p>
          </div>

          <div className="d-flex align-items-center gap-2">
            <div className="form-check form-switch mb-0 me-2">
              <input
                className="form-check-input"
                type="checkbox"
                id="auto-refresh-toggle"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              <label className="form-check-label small fw-semibold text-muted" htmlFor="auto-refresh-toggle">
                Auto-Refresh (10s)
              </label>
            </div>

            <button
              className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1.5 rounded-3 px-3"
              onClick={fetchMonitoring}
              title="Refresh monitoring feed"
            >
              <i className="bi bi-arrow-clockwise" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Live Counters — values come directly from backend (no hardcoded fallbacks) */}
        <div className="row g-3 mb-3">
          <div className="col-4">
            <div className="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-10 rounded-3 text-center">
              <div className="fs-4 fw-bold text-primary">{data.active_candidates_count ?? 0}</div>
              <div className="text-muted small fw-medium">Active In-Exam</div>
            </div>
          </div>
          <div className="col-4">
            <div className="p-3 bg-danger bg-opacity-10 border border-danger border-opacity-10 rounded-3 text-center">
              <div className="fs-4 fw-bold text-danger">{data.flagged_count ?? 0}</div>
              <div className="text-muted small fw-medium">Proctoring Warnings</div>
            </div>
          </div>
          <div className="col-4">
            <div className="p-3 bg-success bg-opacity-10 border border-success border-opacity-10 rounded-3 text-center">
              <div className="fs-4 fw-bold text-success">{data.completed_count ?? 0}</div>
              <div className="text-muted small fw-medium">Submissions Received</div>
            </div>
          </div>
        </div>
      </div>

      {/* Monitoring Grid / Table */}
      <div className="card-body p-0">
        {loading ? (
          <div className="p-5 text-center">
            <div className="spinner-border text-danger" role="status" />
            <p className="text-muted small mt-2">Connecting to live examination stream...</p>
          </div>
        ) : data.sessions.length === 0 ? (
          <div className="p-5 text-center text-muted">
            <i className="bi bi-broadcast fs-2 d-block mb-2 text-muted opacity-50" />
            <p className="mb-0">No active examination sessions at this time.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3 fw-semibold text-muted small">CANDIDATE</th>
                  <th className="py-3 fw-semibold text-muted small">EXAM</th>
                  <th className="py-3 fw-semibold text-muted small">STATUS</th>
                  <th className="py-3 fw-semibold text-muted small">TIME LEFT</th>
                  <th className="py-3 fw-semibold text-muted small" style={{ minWidth: 160 }}>PROGRESS</th>
                  <th className="py-3 fw-semibold text-muted small">TAB SWITCHES</th>
                  <th className="pe-4 py-3 fw-semibold text-muted small text-end">ACTIVITY STATE</th>
                </tr>
              </thead>
              <tbody>
                {data.sessions.map((s) => (
                  <SessionRow key={s.id} s={s} getActivityBadge={getActivityBadge} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveMonitoringPanel;
