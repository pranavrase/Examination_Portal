import React, { useEffect, useState } from 'react';
import { getExaminerActivityLogs } from '../../api/examinerApi';

const ACTION_TYPES = [
  { value: '', label: 'All Actions' },
  { value: 'login', label: 'Login/Logout' },
  { value: 'login_success', label: 'Login Success' },
  { value: 'login_failed', label: 'Login Failed' },
  { value: 'logout', label: 'Logout' },
  { value: 'exam_start', label: 'Exam Start' },
  { value: 'exam_started', label: 'Exam Started' },
  { value: 'exam_submit', label: 'Exam Submit' },
  { value: 'exam_submitted', label: 'Exam Submitted' },
  { value: 'exam_auto_submitted', label: 'Auto Submitted' },
  { value: 'answer_save', label: 'Answer Saved' },
  { value: 'question_view', label: 'Question View' },
  { value: 'code_draft_saved', label: 'Code Draft Saved' },
  { value: 'password_change', label: 'Password Changed' },
  { value: 'profile_update', label: 'Profile Updated' },
  { value: 'exam_create', label: 'Exam Created' },
  { value: 'exam_created', label: 'Exam Created' },
  { value: 'exam_updated', label: 'Exam Updated' },
  { value: 'exam_publish', label: 'Exam Published' },
  { value: 'exam_published', label: 'Exam Published' },
  { value: 'exam_archived', label: 'Exam Archived' },
  { value: 'question_created', label: 'Question Created' },
  { value: 'question_updated', label: 'Question Updated' },
  { value: 'question_deleted', label: 'Question Deleted' },
  { value: 'result_calculated', label: 'Result Calculated' },
  { value: 'ranking_generated', label: 'Ranking Generated' },
  { value: 'unauthorized_access', label: 'Unauthorized Access' },
  { value: 'permission_denied', label: 'Permission Denied' },
  { value: 'user_created', label: 'User Created' },
  { value: 'user_updated', label: 'User Updated' },
  { value: 'user_role_changed', label: 'User Role Changed' },
  { value: 'user_disabled', label: 'User Disabled' },
  { value: 'system', label: 'System' },
];

const ExaminerActivityLogsPanel = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionType, setActionType] = useState('');
  const [search, setSearch] = useState('');

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await getExaminerActivityLogs({ action: actionType, search });
      setLogs(data || []);
    } catch (err) {
      console.error('Failed to load activity logs:', err);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [actionType]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchLogs();
  };

  const getActionBadge = (type) => {
    switch (type) {
      case 'tab_switch':
        return <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-3"><i className="bi bi-exclamation-octagon me-1" /> Tab Switch</span>;
      case 'answer_save':
        return <span className="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3"><i className="bi bi-check2-circle me-1" /> Answer Saved</span>;
      case 'code_execution':
      case 'code_submission':
        return <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3"><i className="bi bi-code-slash me-1" /> Code Action</span>;
      case 'exam_start':
      case 'exam_started':
        return <span className="badge bg-info-subtle text-info border border-info-subtle rounded-pill px-3"><i className="bi bi-play-circle me-1" /> Exam Start</span>;
      case 'exam_submit':
      case 'exam_submitted':
        return <span className="badge bg-dark text-white rounded-pill px-3"><i className="bi bi-flag-fill me-1" /> Exam Submit</span>;
      case 'login':
      case 'login_success':
        return <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3"><i className="bi bi-box-arrow-in-right me-1" /> Login</span>;
      case 'logout':
        return <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill px-3"><i className="bi bi-box-arrow-right me-1" /> Logout</span>;
      case 'question_view':
        return <span className="badge bg-info-subtle text-info border border-info-subtle rounded-pill px-3"><i className="bi bi-eye me-1" /> Question View</span>;
      default:
        return <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill px-3">{type}</span>;
    }
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="examiner-activity-logs">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
          <div>
            <span className="badge bg-dark text-white mb-1 text-uppercase fw-semibold">
              Security & Audit Trail
            </span>
            <h5 className="fw-bold mb-0 text-dark">Examination Activity Logs</h5>
            <p className="text-muted small mb-0">Detailed event log of student interactions, answer changes, proctoring events, and code submissions</p>
          </div>

          <button
            className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1.5 rounded-3 px-3"
            onClick={fetchLogs}
          >
            <i className="bi bi-arrow-clockwise" />
            <span>Refresh Logs</span>
          </button>
        </div>

        {/* Filter Controls */}
        <form onSubmit={handleSearch} className="row g-2 mb-3">
          <div className="col-12 col-md-6">
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0">
                <i className="bi bi-search text-muted" />
              </span>
              <input
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search candidate name or event description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="col-6 col-md-3">
            <select
              className="form-select bg-light"
              value={actionType}
              onChange={(e) => setActionType(e.target.value)}
            >
              {ACTION_TYPES.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>
          </div>

          <div className="col-6 col-md-3">
            <button type="submit" className="btn btn-outline-dark w-100 rounded-3">
              <i className="bi bi-funnel me-1" />
              Filter Logs
            </button>
          </div>
        </form>
      </div>

      {/* Table Body */}
      <div className="card-body p-0">
        {loading ? (
          <div className="p-5 text-center">
            <div className="spinner-border text-dark" role="status" />
            <p className="text-muted small mt-2">Loading audit activity trail...</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-activity display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">No activity logs recorded</h6>
            <p className="small mb-0">Events will populate in real-time as candidates participate.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3 fw-semibold text-muted small">TIMESTAMP</th>
                  <th className="py-3 fw-semibold text-muted small">CANDIDATE</th>
                  <th className="py-3 fw-semibold text-muted small">EVENT TYPE</th>
                  <th className="pe-4 py-3 fw-semibold text-muted small">DESCRIPTION</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-top">
                    <td className="ps-4 py-3 text-muted small font-monospace">
                      {new Date(log.timestamp).toLocaleString('en-IN', {
                        day: '2-digit',
                        month: 'short',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: true,
                      })}
                    </td>
                    <td className="py-3">
                      <div className="fw-semibold text-dark">{log.candidate_name}</div>
                    </td>
                    <td>{getActionBadge(log.action_type)}</td>
                    <td className="pe-4 py-3 text-dark small" style={{ maxWidth: 360 }}>
                      {log.description}
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

export default ExaminerActivityLogsPanel;
