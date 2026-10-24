import React, { useState } from 'react';
import { getActivityById } from '../../api/activityApi';

// ─── Severity config ─────────────────────────────────────────────────────────
const SEVERITY_MAP = {
  tab_switch:      { label: 'Tab Switch',       cls: 'bg-warning text-dark',  icon: 'bi-arrow-left-right' },
  page_refresh:    { label: 'Page Refresh',     cls: 'bg-warning text-dark',  icon: 'bi-arrow-clockwise' },
  window_blur:     { label: 'Window Blur',      cls: 'bg-warning text-dark',  icon: 'bi-eye-slash' },
  login:           { label: 'Login',            cls: 'bg-success text-white', icon: 'bi-box-arrow-in-right' },
  logout:          { label: 'Logout',           cls: 'bg-secondary text-white',icon: 'bi-box-arrow-right' },
  login_failed:    { label: 'Login Failed',     cls: 'bg-danger text-white',  icon: 'bi-x-circle' },
  exam_start:      { label: 'Exam Started',     cls: 'bg-info text-white',    icon: 'bi-play-fill' },
  exam_submit:     { label: 'Exam Submitted',   cls: 'bg-primary text-white', icon: 'bi-send-fill' },
  suspicious:      { label: 'Suspicious',       cls: 'bg-danger text-white',  icon: 'bi-exclamation-triangle-fill' },
};

const getSeverity = (type) => {
  const key = (type || '').toLowerCase().replace(/[\s-]/g, '_');
  return SEVERITY_MAP[key] || { label: type || 'Activity', cls: 'bg-light text-dark border', icon: 'bi-circle' };
};

// ─── Skeleton ────────────────────────────────────────────────────────────────
const Skeleton = ({ h = '2.2rem', cls = '' }) => (
  <div className={`placeholder-glow mb-2 ${cls}`}>
    <span className="placeholder rounded d-block w-100" style={{ height: h }} />
  </div>
);

// ─── Detail Modal ─────────────────────────────────────────────────────────────
const DetailModal = ({ activityId, onClose }) => {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  React.useEffect(() => {
    if (!activityId) return;
    setLoading(true);
    setError(null);
    getActivityById(activityId)
      .then(setDetail)
      .catch(err => setError(err?.response?.data?.detail || 'Failed to load detail.'))
      .finally(() => setLoading(false));
  }, [activityId]);

  const sev = detail ? getSeverity(detail.activity_type || detail.action_type) : null;

  return (
    <div
      className="modal d-flex align-items-center justify-content-center"
      style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1055 }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="modal-dialog modal-dialog-centered modal-md w-100 mx-3" style={{ maxWidth: 560 }}>
        <div className="modal-content border-0 rounded-4 shadow-lg">
          <div className="modal-header border-0 pb-0 px-4 pt-4">
            <h5 className="modal-title fw-bold d-flex align-items-center gap-2">
              <i className="bi bi-journal-text text-primary" />
              Activity Detail
            </h5>
            <button type="button" className="btn-close" onClick={onClose} />
          </div>
          <div className="modal-body px-4 pb-4">
            {loading ? (
              <div className="text-center py-4">
                <span className="spinner-border text-primary" />
              </div>
            ) : error ? (
              <div className="alert alert-danger rounded-3">{error}</div>
            ) : detail ? (
              <div>
                {sev && (
                  <span className={`badge ${sev.cls} mb-3 d-inline-flex align-items-center gap-1 px-3 py-2`} style={{ fontSize: '0.82rem' }}>
                    <i className={`bi ${sev.icon}`} />
                    {sev.label}
                  </span>
                )}
                <table className="table table-sm table-borderless mb-0">
                  <tbody>
                    {[
                      ['Activity ID',   detail.id || detail.activity_id],
                      ['Action Type',   detail.activity_type || detail.action_type],
                      ['Description',   detail.description || detail.message],
                      ['User / Student',detail.student_name || detail.username || detail.user_id],
                      ['Exam',          detail.exam_name || detail.exam_id],
                      ['Attempt ID',    detail.attempt_id],
                      ['Timestamp',     detail.timestamp || detail.created_at
                        ? new Date(detail.timestamp || detail.created_at).toLocaleString('en-IN')
                        : null],
                      ['IP Address',    detail.ip_address],
                      ['User Agent',    detail.user_agent],
                    ].map(([label, value]) =>
                      value != null && value !== '' ? (
                        <tr key={label}>
                          <td className="text-muted small pe-3 py-1" style={{ width: '38%', whiteSpace: 'nowrap' }}>{label}</td>
                          <td className="small fw-semibold py-1 text-break">{String(value)}</td>
                        </tr>
                      ) : null
                    )}
                    {/* Metadata */}
                    {detail.metadata && typeof detail.metadata === 'object' && (
                      <tr>
                        <td className="text-muted small pe-3 py-1 align-top">Metadata</td>
                        <td className="py-1">
                          <pre className="bg-light rounded-2 p-2 mb-0 small" style={{ fontSize: '0.72rem', maxHeight: 120, overflow: 'auto' }}>
                            {JSON.stringify(detail.metadata, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── Sort icon ────────────────────────────────────────────────────────────────
const SortIcon = ({ col, sortCol, sortDir }) => {
  if (col !== sortCol)
    return <i className="bi bi-chevron-expand text-muted opacity-30 ms-1" style={{ fontSize: '0.65rem' }} />;
  return sortDir === 'asc'
    ? <i className="bi bi-chevron-up ms-1 text-primary" style={{ fontSize: '0.65rem' }} />
    : <i className="bi bi-chevron-down ms-1 text-primary" style={{ fontSize: '0.65rem' }} />;
};

// ════════════════════════════════════════════════════════════════════════════
// ActivityLogTable
// ════════════════════════════════════════════════════════════════════════════
const PAGE_SIZE = 20;

const SUSPICIOUS_TYPES = new Set(['tab_switch', 'page_refresh', 'window_blur', 'login_failed', 'suspicious']);

const ActivityLogTable = ({
  data = [],
  loading = false,
  error = null,
  pollError = false,
  onRetry,
}) => {
  const [search, setSearch]     = useState('');
  const [typeFilter, setType]   = useState('');
  const [sortCol, setSortCol]   = useState('timestamp');
  const [sortDir, setSortDir]   = useState('desc');
  const [page, setPage]         = useState(1);
  const [selectedId, setSelectedId] = useState(null);

  const handleSort = (col) => {
    if (col === sortCol) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
    setPage(1);
  };

  // Unique activity types for quick filter dropdown
  const activityTypes = [...new Set(data.map(r => r.activity_type || r.action_type).filter(Boolean))];

  // Filter + sort
  const processed = React.useMemo(() => {
    let rows = [...data];
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(r =>
        (r.student_name || r.username || r.user_id || '').toString().toLowerCase().includes(q) ||
        (r.description || r.message || '').toLowerCase().includes(q) ||
        (r.activity_type || r.action_type || '').toLowerCase().includes(q) ||
        String(r.attempt_id || '').toLowerCase().includes(q)
      );
    }
    if (typeFilter) {
      rows = rows.filter(r => (r.activity_type || r.action_type) === typeFilter);
    }
    rows.sort((a, b) => {
      let va = a[sortCol] ?? 0;
      let vb = b[sortCol] ?? 0;
      if (sortCol === 'timestamp' || sortCol === 'created_at') {
        va = new Date(a.timestamp || a.created_at || 0).getTime();
        vb = new Date(b.timestamp || b.created_at || 0).getTime();
      }
      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return rows;
  }, [data, search, typeFilter, sortCol, sortDir]);

  const totalPages = Math.max(1, Math.ceil(processed.length / PAGE_SIZE));
  const pageData   = processed.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const COLS = [
    { key: 'id',             label: 'ID',          sortable: true,  width: '60px' },
    { key: 'activity_type',  label: 'Type',        sortable: true  },
    { key: 'student_name',   label: 'Student',     sortable: true  },
    { key: 'description',    label: 'Description', sortable: false },
    { key: 'exam_name',      label: 'Exam',        sortable: true  },
    { key: 'attempt_id',     label: 'Attempt',     sortable: true  },
    { key: 'timestamp',      label: 'Time',        sortable: true  },
  ];

  // Only show columns with at least one value
  const activeCols = COLS.filter(c =>
    ['activity_type', 'student_name', 'description', 'timestamp'].includes(c.key) ||
    data.some(r => r[c.key] != null || r[c.key.replace('student_name', 'username')] != null)
  );

  if (loading && data.length === 0) {
    return (
      <div className="p-4">
        {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );
  }

  if (error && data.length === 0) {
    return (
      <div className="d-flex flex-column align-items-center justify-content-center py-5 text-center">
        <i className="bi bi-exclamation-triangle-fill text-warning fs-1 mb-3" />
        <h6 className="fw-bold mb-1">Failed to Load Activity</h6>
        <p className="text-muted small mb-3" style={{ maxWidth: 360 }}>{error}</p>
        {onRetry && (
          <button className="btn btn-primary btn-sm rounded-3" onClick={onRetry}>
            <i className="bi bi-arrow-clockwise me-2" />Retry
          </button>
        )}
      </div>
    );
  }

  return (
    <>
      {/* ── Poll error banner (non-destructive) ──────────────────────────── */}
      {pollError && (
        <div className="alert alert-warning d-flex align-items-center gap-2 mx-4 mt-3 mb-0 rounded-3 py-2 small border-0">
          <i className="bi bi-wifi-off flex-shrink-0" />
          Live refresh failed — showing last known data. Retrying automatically…
        </div>
      )}

      {/* ── Table controls ───────────────────────────────────────────────── */}
      <div className="d-flex flex-wrap gap-2 px-4 py-3 align-items-center border-bottom">
        <div className="input-group input-group-sm" style={{ maxWidth: 240 }}>
          <span className="input-group-text bg-white border-end-0">
            <i className="bi bi-search text-muted" />
          </span>
          <input
            id="activity-table-search"
            type="text"
            className="form-control border-start-0"
            placeholder="Search student, type, description…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>

        {activityTypes.length > 0 && (
          <select
            id="activity-type-filter"
            className="form-select form-select-sm rounded-3"
            style={{ maxWidth: 180 }}
            value={typeFilter}
            onChange={e => { setType(e.target.value); setPage(1); }}
          >
            <option value="">All Activity Types</option>
            {activityTypes.map(t => (
              <option key={t} value={t}>{getSeverity(t).label}</option>
            ))}
          </select>
        )}

        <span className="ms-auto text-muted small">
          {processed.length} record{processed.length !== 1 ? 's' : ''}
          {loading && (
            <span className="spinner-border spinner-border-sm ms-2 opacity-50" style={{ width: 12, height: 12 }} />
          )}
        </span>
      </div>

      {/* ── Table ───────────────────────────────────────────────────────── */}
      {processed.length === 0 ? (
        <div className="text-center py-5 text-muted">
          <i className="bi bi-clipboard-x fs-2 d-block mb-3 opacity-30" />
          <h6 className="fw-semibold mb-1">No Activity Found</h6>
          <p className="small mb-0">Try changing the filters or date range.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light">
              <tr>
                {activeCols.map(c => (
                  <th
                    key={c.key}
                    className={`py-3 text-uppercase text-muted fw-semibold ${c.sortable ? 'user-select-none' : ''}`}
                    style={{
                      fontSize: '0.67rem', letterSpacing: '0.06em',
                      whiteSpace: 'nowrap', width: c.width,
                      cursor: c.sortable ? 'pointer' : 'default',
                    }}
                    onClick={() => c.sortable && handleSort(c.key)}
                  >
                    {c.label}
                    {c.sortable && <SortIcon col={c.key} sortCol={sortCol} sortDir={sortDir} />}
                  </th>
                ))}
                <th className="py-3" style={{ width: '48px' }} />
              </tr>
            </thead>
            <tbody>
              {pageData.map((row, idx) => {
                const type = row.activity_type || row.action_type;
                const sev  = getSeverity(type);
                const isSuspicious = SUSPICIOUS_TYPES.has((type || '').toLowerCase().replace(/[\s-]/g, '_'));
                const ts   = row.timestamp || row.created_at;

                return (
                  <tr
                    key={row.id || row.activity_id || idx}
                    className={isSuspicious ? 'table-warning' : ''}
                    style={{ transition: 'background 0.15s' }}
                  >
                    {activeCols.map(c => (
                      <td key={c.key} className="py-2 small">
                        {c.key === 'id' ? (
                          <span className="text-muted font-monospace" style={{ fontSize: '0.72rem' }}>
                            #{row.id || row.activity_id || idx + 1}
                          </span>
                        ) : c.key === 'activity_type' ? (
                          <span className={`badge ${sev.cls} d-inline-flex align-items-center gap-1 px-2 py-1`} style={{ fontSize: '0.7rem' }}>
                            <i className={`bi ${sev.icon}`} />
                            {sev.label}
                          </span>
                        ) : c.key === 'student_name' ? (
                          <span className="fw-semibold">{row.student_name || row.username || row.user_id || '—'}</span>
                        ) : c.key === 'description' ? (
                          <span className="text-secondary" style={{ maxWidth: 280, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {row.description || row.message || '—'}
                          </span>
                        ) : c.key === 'exam_name' ? (
                          row.exam_name || row.exam_id || '—'
                        ) : c.key === 'attempt_id' ? (
                          row.attempt_id ? (
                            <span className="badge bg-light text-secondary border" style={{ fontSize: '0.68rem' }}>
                              #{row.attempt_id}
                            </span>
                          ) : '—'
                        ) : c.key === 'timestamp' ? (
                          ts ? (
                            <span title={new Date(ts).toLocaleString('en-IN')} style={{ fontSize: '0.72rem' }}>
                              {new Date(ts).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                            </span>
                          ) : '—'
                        ) : '—'}
                      </td>
                    ))}
                    {/* View detail */}
                    <td>
                      <button
                        className="btn btn-sm btn-outline-secondary rounded-3 py-0 px-2"
                        style={{ fontSize: '0.7rem' }}
                        onClick={() => setSelectedId(row.id || row.activity_id)}
                        title="View detail"
                      >
                        <i className="bi bi-eye" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Pagination ───────────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="d-flex justify-content-center align-items-center gap-2 p-3 border-top">
          <button className="btn btn-sm btn-outline-secondary rounded-3" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
            <i className="bi bi-chevron-left" /> Prev
          </button>
          <span className="text-muted small">Page {page} of {totalPages}</span>
          <button className="btn btn-sm btn-outline-secondary rounded-3" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>
            Next <i className="bi bi-chevron-right" />
          </button>
        </div>
      )}

      {/* ── Detail Modal ─────────────────────────────────────────────────── */}
      {selectedId && <DetailModal activityId={selectedId} onClose={() => setSelectedId(null)} />}
    </>
  );
};

export default ActivityLogTable;
