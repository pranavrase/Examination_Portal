import React, { useMemo } from 'react';

/**
 * SessionMonitorPanel
 *
 * Displays a summary of session-related activity records derived from
 * the main activity log (passed as `sessions` prop). This component
 * does NOT make its own API calls — the parent page passes filtered data.
 *
 * Props:
 *   sessions   {Array}   – activity log rows filtered to session-type events
 *   loading    {boolean} – show skeleton while parent is fetching
 */

// ─── Helpers ─────────────────────────────────────────────────────────────────
const SESSION_TYPES = new Set([
  'login', 'logout', 'login_failed', 'session_start', 'session_end',
  'session_expired', 'token_refresh',
]);

const STATUS_MAP = {
  login:           { label: 'Active',    cls: 'bg-success' },
  session_start:   { label: 'Active',    cls: 'bg-success' },
  logout:          { label: 'Ended',     cls: 'bg-secondary' },
  session_end:     { label: 'Ended',     cls: 'bg-secondary' },
  session_expired: { label: 'Expired',   cls: 'bg-warning text-dark' },
  login_failed:    { label: 'Failed',    cls: 'bg-danger' },
};

const getStatus = (type) => {
  const key = (type || '').toLowerCase();
  return STATUS_MAP[key] || { label: type || 'Unknown', cls: 'bg-light text-dark border' };
};

const fmtTime = (ts) => {
  if (!ts) return '—';
  return new Date(ts).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
};

// ─── Skeleton ─────────────────────────────────────────────────────────────────
const Skeleton = ({ h = '1rem', cls = '' }) => (
  <div className={`placeholder-glow ${cls}`} style={{ height: h }}>
    <span className="placeholder rounded d-block w-100 h-100" />
  </div>
);

// ─── Session Row ──────────────────────────────────────────────────────────────
const SessionRow = ({ session }) => {
  const type   = session.activity_type || session.action_type || '';
  const status = getStatus(type);
  const name   = session.student_name || session.username || session.user_id || 'Unknown';
  const ts     = session.timestamp || session.created_at;

  return (
    <div className="d-flex align-items-start gap-3 p-3 border-bottom" style={{ fontSize: '0.82rem' }}>
      {/* Status dot */}
      <div className="flex-shrink-0 mt-1">
        <span className={`badge ${status.cls} rounded-pill`} style={{ width: 10, height: 10, padding: 0, display: 'inline-block' }} />
      </div>

      {/* Main info */}
      <div className="flex-grow-1 min-w-0">
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <span className="fw-semibold">{name}</span>
          <span className={`badge ${status.cls} px-2 py-0`} style={{ fontSize: '0.65rem' }}>
            {status.label}
          </span>
          {session.exam_name || session.exam_id ? (
            <span className="badge bg-light text-secondary border" style={{ fontSize: '0.65rem' }}>
              {session.exam_name || `Exam #${session.exam_id}`}
            </span>
          ) : null}
        </div>

        <div className="text-muted mt-1" style={{ fontSize: '0.72rem' }}>
          <span className="me-3">
            <i className="bi bi-clock me-1" />{fmtTime(ts)}
          </span>
          {session.attempt_id && (
            <span className="me-3">
              <i className="bi bi-hash me-1" />Attempt {session.attempt_id}
            </span>
          )}
        </div>

        {/* Sensitive fields — only shown when backend provides them */}
        {session.ip_address && (
          <div className="text-muted" style={{ fontSize: '0.7rem' }}>
            <i className="bi bi-geo me-1" />{session.ip_address}
          </div>
        )}
        {session.user_agent && (
          <div
            className="text-muted text-truncate"
            style={{ fontSize: '0.68rem', maxWidth: 360 }}
            title={session.user_agent}
          >
            <i className="bi bi-browser-chrome me-1" />{session.user_agent}
          </div>
        )}

        {/* Description */}
        {(session.description || session.message) && (
          <div className="text-secondary mt-1" style={{ fontSize: '0.72rem' }}>
            {session.description || session.message}
          </div>
        )}
      </div>
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// SessionMonitorPanel
// ════════════════════════════════════════════════════════════════════════════
const SessionMonitorPanel = ({ sessions = [], loading = false }) => {
  // Derive session-type rows from the provided activity data
  const sessionRows = useMemo(() =>
    sessions
      .filter(r => {
        const t = (r.activity_type || r.action_type || '').toLowerCase();
        return SESSION_TYPES.has(t);
      })
      .sort((a, b) =>
        new Date(b.timestamp || b.created_at || 0) -
        new Date(a.timestamp || a.created_at || 0)
      ),
    [sessions]
  );

  // Summaries
  const activeCount  = sessionRows.filter(r => ['login', 'session_start'].includes((r.activity_type || r.action_type || '').toLowerCase())).length;
  const failedCount  = sessionRows.filter(r => (r.activity_type || r.action_type || '').toLowerCase() === 'login_failed').length;

  // Multiple-login-attempt detection: users with ≥2 login_failed events
  const failedByUser = useMemo(() => {
    const map = {};
    sessionRows
      .filter(r => (r.activity_type || r.action_type || '').toLowerCase() === 'login_failed')
      .forEach(r => {
        const u = r.student_name || r.username || r.user_id || 'unknown';
        map[u] = (map[u] || 0) + 1;
      });
    return Object.entries(map).filter(([, c]) => c >= 2);
  }, [sessionRows]);

  return (
    <div className="card border-0 shadow-sm rounded-4 h-100">
      {/* Card header */}
      <div className="card-header bg-white border-0 px-4 pt-4 pb-3 d-flex align-items-center justify-content-between">
        <h6 className="fw-bold mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-shield-lock-fill text-primary" />
          Session Monitor
        </h6>
        <div className="d-flex gap-2">
          {activeCount > 0 && (
            <span className="badge bg-success bg-opacity-15 text-success d-flex align-items-center gap-1 px-2" style={{ fontSize: '0.7rem' }}>
              <span className="rounded-circle bg-success d-inline-block" style={{ width: 6, height: 6 }} />
              {activeCount} Active
            </span>
          )}
          {failedCount > 0 && (
            <span className="badge bg-danger bg-opacity-15 text-danger d-flex align-items-center gap-1 px-2" style={{ fontSize: '0.7rem' }}>
              <i className="bi bi-x-circle-fill" style={{ fontSize: '0.6rem' }} />
              {failedCount} Failed Login{failedCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Suspicious indicator */}
      {failedByUser.length > 0 && (
        <div className="mx-4 mb-2">
          <div className="alert alert-danger d-flex align-items-center gap-2 rounded-3 py-2 small border-0 mb-0">
            <i className="bi bi-exclamation-triangle-fill flex-shrink-0" />
            <div>
              <strong>Multiple failed logins detected</strong> for:{' '}
              {failedByUser.map(([u, c]) => `${u} (${c}×)`).join(', ')}
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="card-body p-0" style={{ maxHeight: 420, overflowY: 'auto' }}>
        {loading ? (
          <div className="p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} h="56px" cls="mb-2" />
            ))}
          </div>
        ) : sessionRows.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-person-lock fs-2 d-block mb-2 opacity-30" />
            <p className="small mb-0">No session events in current activity log.</p>
          </div>
        ) : (
          sessionRows.map((s, i) => (
            <SessionRow key={s.id || s.activity_id || i} session={s} />
          ))
        )}
      </div>

      {/* Footer count */}
      {!loading && sessionRows.length > 0 && (
        <div className="card-footer bg-white border-0 px-4 py-2 text-muted" style={{ fontSize: '0.72rem' }}>
          Showing {sessionRows.length} session event{sessionRows.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};

export default SessionMonitorPanel;
