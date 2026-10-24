import React from 'react';

const AuditLogViewer = ({ logs = [], loading, error, onRefresh }) => {
  const getActionBadge = (action) => {
    const act = (action || '').toUpperCase();
    if (act.includes('ROLE')) return 'bg-warning text-dark';
    if (act.includes('DEACTIVATE') || act.includes('DELETE')) return 'bg-danger';
    if (act.includes('LOGIN') || act.includes('AUTH')) return 'bg-info text-dark';
    if (act.includes('EXAM') || act.includes('CREATE')) return 'bg-primary';
    return 'bg-secondary';
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Just now';
    try {
      return new Date(ts).toLocaleString(undefined, {
        dateStyle: 'short',
        timeStyle: 'medium',
      });
    } catch (e) {
      return ts;
    }
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="audit-logs">
      <div className="card-header bg-white border-bottom border-light p-4 rounded-top-4 d-flex align-items-center justify-content-between">
        <div>
          <h5 className="fw-bold mb-0 text-dark d-flex align-items-center gap-2">
            <i className="bi bi-journal-text text-primary"></i>
            <span>System Activity Audit Logs</span>
            {loading && logs.length > 0 && (
              <span
                className="spinner-border spinner-border-sm text-primary ms-2"
                role="status"
                aria-label="Updating logs..."
                title="Refreshing activity logs..."
              ></span>
            )}
          </h5>
          <p className="text-muted fs-7 mb-0">Track administrative, role assignment, and security events</p>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 rounded-pill px-3"
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
            <span>Refresh Logs</span>
          </button>
        )}
      </div>

      {error && (
        <div className="px-4 pt-3">
          <div className="alert alert-warning border-0 rounded-3 mb-0 d-flex align-items-center justify-content-between">
            <div className="d-flex align-items-center">
              <i className="bi bi-exclamation-circle me-2 fs-5"></i>
              <span>{error || 'Unable to load audit logs. Please try again.'}</span>
            </div>
            {onRefresh && (
              <button
                type="button"
                className="btn btn-outline-dark btn-sm rounded-pill px-3 ms-3 d-flex align-items-center gap-1"
                onClick={onRefresh}
                disabled={loading}
              >
                <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
                <span>Retry</span>
              </button>
            )}
          </div>
        </div>
      )}

      <div className="card-body p-0">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light text-muted fs-7 text-uppercase tracking-wider">
              <tr>
                <th className="ps-4">Timestamp</th>
                <th>User / Actor</th>
                <th>Action Type</th>
                <th>Description</th>
                <th className="pe-4">Details</th>
              </tr>
            </thead>
            <tbody>
              {/* Show skeleton placeholders ONLY on initial load before any logs exist */}
              {loading && logs.length === 0 ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={idx}>
                    <td className="ps-4">
                      <span className="placeholder col-8 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-10 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-6 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td>
                      <span className="placeholder col-10 bg-secondary opacity-25 rounded"></span>
                    </td>
                    <td className="pe-4">
                      <span className="placeholder col-6 bg-secondary opacity-25 rounded"></span>
                    </td>
                  </tr>
                ))
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-5 text-muted">
                    <i className="bi bi-clipboard-check fs-1 d-block mb-2 text-secondary opacity-50"></i>
                    No activity logs recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log, index) => (
                  <tr key={log.id || log._id || index}>
                    <td className="ps-4 text-muted fs-7 fw-mono">
                      {formatTimestamp(log.timestamp || log.created_at || log.occurred_at)}
                    </td>
                    <td>
                      <span className="fw-semibold text-dark fs-7">
                        {log.user_email || (typeof log.user === 'object' ? log.user?.email || log.user?.full_name : log.user) || log.username || log.student_name || log.actor || (log.user_id ? `User #${log.user_id}` : 'System')}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${getActionBadge(log.action || log.action_type)} px-2 py-1 fs-8 text-uppercase`}>
                        {log.action || log.action_type || 'ACTIVITY'}
                      </span>
                    </td>
                    <td className="text-dark fs-7">{log.description || log.message || log.details || 'N/A'}</td>
                    <td className="pe-4 text-muted fs-8 font-monospace">
                      {log.ip_address ? `IP: ${log.ip_address}` : log.metadata ? JSON.stringify(log.metadata) : (log.entity_type ? `${log.entity_type}${log.entity_id ? ` #${log.entity_id}` : ''}` : '-')}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AuditLogViewer;
