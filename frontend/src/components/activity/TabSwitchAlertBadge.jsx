import React, { useEffect, useState, useCallback } from 'react';
import { getTabSwitches } from '../../api/activityApi';

/**
 * TabSwitchAlertBadge
 *
 * Shows a compact warning badge with the tab-switch count for a given attempt.
 * Clicking it opens an inline popover listing the individual tab-switch events.
 *
 * Props:
 *   attemptId  {string|number}  – exam attempt to query
 *   inline     {boolean}        – render inline (no absolute positioning); default false
 */
const TabSwitchAlertBadge = ({ attemptId, inline = false }) => {
  const [events, setEvents]   = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [open, setOpen]       = useState(false);

  const fetchEvents = useCallback(async () => {
    if (!attemptId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getTabSwitches(attemptId);
      const list = Array.isArray(data)
        ? data
        : data?.events || data?.tab_switches || data?.results || [];
      setEvents(list);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load tab-switch data.');
    } finally {
      setLoading(false);
    }
  }, [attemptId]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  const count = events.length;

  if (!attemptId) return null;

  // ── Badge ──────────────────────────────────────────────────────────────────
  const badge = (
    <button
      id={`tab-switch-badge-${attemptId}`}
      className={`btn btn-sm d-inline-flex align-items-center gap-1 border-0 rounded-pill px-2 py-1 ${
        loading
          ? 'btn-outline-secondary'
          : count === 0
          ? 'btn-outline-success'
          : count <= 2
          ? 'btn-warning'
          : 'btn-danger'
      }`}
      style={{ fontSize: '0.72rem', fontWeight: 600 }}
      onClick={() => !loading && setOpen(o => !o)}
      title={`${count} tab-switch event${count !== 1 ? 's' : ''} for attempt #${attemptId}`}
    >
      {loading ? (
        <span className="spinner-border spinner-border-sm" style={{ width: 10, height: 10 }} />
      ) : count === 0 ? (
        <><i className="bi bi-shield-check" /> No Tab Switches</>
      ) : (
        <><i className="bi bi-exclamation-triangle-fill" /> {count} Tab Switch{count !== 1 ? 'es' : ''}</>
      )}
    </button>
  );

  // ── Popover list ───────────────────────────────────────────────────────────
  const popover = open && (
    <div
      className="card border shadow rounded-4 p-0 mt-1"
      style={{
        position: inline ? 'relative' : 'absolute',
        zIndex: 1050,
        minWidth: 300,
        maxWidth: 420,
        maxHeight: 320,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div className="d-flex align-items-center justify-content-between px-3 py-2 border-bottom bg-light rounded-top-4">
        <span className="fw-bold small d-flex align-items-center gap-2">
          <i className="bi bi-arrow-left-right text-warning" />
          Tab-Switch Events — Attempt #{attemptId}
        </span>
        <button className="btn-close" style={{ fontSize: '0.6rem' }} onClick={() => setOpen(false)} />
      </div>

      {/* Body */}
      <div style={{ overflowY: 'auto', maxHeight: 260 }}>
        {error ? (
          <div className="alert alert-danger m-2 rounded-3 py-2 small mb-0">{error}</div>
        ) : events.length === 0 ? (
          <div className="text-center py-4 text-muted small">
            <i className="bi bi-shield-check-fill text-success fs-4 d-block mb-2" />
            No tab-switch events recorded.
          </div>
        ) : (
          <ul className="list-unstyled mb-0">
            {events.map((ev, i) => {
              const ts = ev.timestamp || ev.created_at;
              const evType = ev.activity_type || ev.action_type || 'Tab Switch';
              return (
                <li
                  key={ev.id || i}
                  className="d-flex align-items-start gap-2 px-3 py-2 border-bottom"
                  style={{ fontSize: '0.78rem' }}
                >
                  <span
                    className="badge bg-warning text-dark flex-shrink-0 mt-1 d-flex align-items-center justify-content-center"
                    style={{ width: 22, height: 22, fontSize: '0.65rem' }}
                  >
                    {i + 1}
                  </span>
                  <div className="flex-grow-1">
                    <div className="fw-semibold">{evType.replace(/_/g, ' ')}</div>
                    {ev.description || ev.message ? (
                      <div className="text-muted">{ev.description || ev.message}</div>
                    ) : null}
                    {ts && (
                      <div className="text-muted" style={{ fontSize: '0.68rem' }}>
                        {new Date(ts).toLocaleString('en-IN', {
                          day: 'numeric', month: 'short',
                          hour: '2-digit', minute: '2-digit', second: '2-digit',
                        })}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );

  if (inline) {
    return (
      <div>
        {badge}
        {popover}
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      {badge}
      {popover}
    </div>
  );
};

export default TabSwitchAlertBadge;
