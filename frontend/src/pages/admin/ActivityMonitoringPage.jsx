import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getActivityLogs } from '../../api/activityApi';
import ActivityLogTable from '../../components/activity/ActivityLogTable';
import SessionMonitorPanel from '../../components/activity/SessionMonitorPanel';
import AuditLogViewer from '../../components/admin/AuditLogViewer';

// ─── Constants ────────────────────────────────────────────────────────────────
const POLL_INTERVAL_MS = 30_000; // 30 seconds

// ════════════════════════════════════════════════════════════════════════════
// Main Page
// ════════════════════════════════════════════════════════════════════════════
const ActivityMonitoringPage = () => {
  const [data, setData]           = useState([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [pollError, setPollError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Polling ref — holds the active interval ID
  const intervalRef = useRef(null);
  // Track whether a fetch is already in progress to avoid duplicates
  const fetchingRef = useRef(false);

  // ── Core fetch ─────────────────────────────────────────────────────────────
  const fetchData = useCallback(async (isPoll = false) => {
    if (fetchingRef.current) return; // skip if already in flight
    fetchingRef.current = true;
    if (!isPoll) {
      setLoading(true);
      setError(null);
      setPollError(false);
    }
    try {
      const res = await getActivityLogs();
      const list = Array.isArray(res)
        ? res
        : res?.items || res?.logs || res?.activities || res?.data || res?.results || [];
      setData(list);
      setLastUpdated(new Date());
      if (isPoll) setPollError(false);
    } catch (err) {
      if (isPoll) {
        // Don't wipe existing data — just flag the poll failure
        setPollError(true);
      } else {
        setError(err?.response?.data?.detail || err.message || 'Failed to load activity logs.');
      }
    } finally {
      if (!isPoll) setLoading(false);
      fetchingRef.current = false;
    }
  }, []);

  // ── Start polling ──────────────────────────────────────────────────────────
  const startPolling = useCallback(() => {
    // Clear any existing interval before starting a new one
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = setInterval(() => {
      fetchData(true);
    }, POLL_INTERVAL_MS);
  }, [fetchData]);

  // ── Initial load + polling setup ───────────────────────────────────────────
  useEffect(() => {
    fetchData();
    startPolling();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData, startPolling]);

  // ── Manual refresh ─────────────────────────────────────────────────────────
  const handleRefresh = () => {
    fetchData();
    startPolling();
  };

  return (
    <div className="bg-light min-vh-100">
      <div className="container-fluid py-4 px-lg-5">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-start gap-3 mb-4">
          <div>
            <nav aria-label="breadcrumb" className="mb-1">
              <ol className="breadcrumb small mb-0">
                <li className="breadcrumb-item">
                  <Link to="/admin" className="text-decoration-none">Dashboard</Link>
                </li>
                <li className="breadcrumb-item active">System Activity Logs</li>
              </ol>
            </nav>
            <h2 className="fw-bold mb-0 d-flex align-items-center gap-2">
              <i className="bi bi-activity text-primary" />
              System Activity Logs
            </h2>
            <p className="text-muted small mb-0">
              Real-time exam activity, audit logs, and session monitoring
              {lastUpdated && (
                <span className="ms-2">
                  · Last updated: {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
            </p>
          </div>

          {/* Manual refresh + poll indicator */}
          <div className="d-flex align-items-center gap-2">
            <span className="d-flex align-items-center gap-1 text-muted small">
              <span
                className="rounded-circle d-inline-block"
                style={{
                  width: 8, height: 8,
                  background: pollError ? '#ef4444' : '#22c55e',
                  boxShadow: pollError ? 'none' : '0 0 0 3px rgba(34,197,94,0.25)',
                  animation: pollError ? 'none' : 'pulse 2s infinite',
                }}
              />
              {pollError ? 'Reconnecting…' : 'Live'}
            </span>
            <button
              className="btn btn-sm btn-outline-secondary rounded-3 d-flex align-items-center gap-1"
              onClick={handleRefresh}
              disabled={loading}
              title="Refresh now"
            >
              <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* ── System Activity Audit Logs ─────────────────────────────────── */}
        <AuditLogViewer
          logs={data}
          loading={loading}
          error={error}
          onRefresh={handleRefresh}
        />

        {/* ── Main content grid: table + session panel ─────────────────────── */}
        <div className="row g-4">

          {/* ── Activity Log Table ──────────────────────────────────────── */}
          <div className="col-12 col-xl-8">
            <div className="card border-0 shadow-sm rounded-4">
              <div className="card-header bg-white border-0 px-4 pt-4 pb-0">
                <h6 className="fw-bold mb-0">
                  <i className="bi bi-table me-2 text-primary" />
                  Activity Log
                </h6>
              </div>
              <div className="card-body p-0">
                <ActivityLogTable
                  data={data}
                  loading={loading}
                  error={error}
                  pollError={pollError}
                  onRetry={handleRefresh}
                />
              </div>
            </div>
          </div>

          {/* ── Session Monitor ──────────────────────────────────────────── */}
          <div className="col-12 col-xl-4">
            <SessionMonitorPanel sessions={data} loading={loading} />
          </div>

        </div>
      </div>

      {/* ── Pulse animation + spin ────────────────────────────────────────── */}
      <style>{`
        @keyframes pulse {
          0%   { box-shadow: 0 0 0 0   rgba(34,197,94,0.5); }
          70%  { box-shadow: 0 0 0 6px rgba(34,197,94,0);   }
          100% { box-shadow: 0 0 0 0   rgba(34,197,94,0);   }
        }
        @keyframes spin {
          from { transform: rotate(0deg);   }
          to   { transform: rotate(360deg); }
        }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
};

export default ActivityMonitoringPage;
