import React, { useEffect, useState } from 'react';
import { getExaminerNotifications, sendExaminerNotification, getMyExams } from '../../api/examinerApi';

const ExaminerNotificationsPanel = () => {
  const [notifications, setNotifications] = useState([]);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [toast, setToast] = useState(null);

  // Form states
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [type, setType] = useState('announcement');
  const [targetExamId, setTargetExamId] = useState('');

  const fetchData = async () => {
    try {
      setLoading(true);
      const [notifs, examData] = await Promise.all([
        getExaminerNotifications(),
        getMyExams(),
      ]);
      setNotifications(notifs || []);
      setExams(Array.isArray(examData) ? examData : examData?.items || []);
    } catch (err) {
      console.error('Failed to load notifications:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!title.trim() || !message.trim()) return;
    try {
      setSending(true);
      await sendExaminerNotification({
        title,
        message,
        type,
        target_exam_id: targetExamId ? parseInt(targetExamId) : null,
      });
      setToast({ type: 'success', text: 'Announcement broadcast successfully!' });
      setTitle('');
      setMessage('');
      fetchData();
    } catch (err) {
      setToast({ type: 'danger', text: 'Failed to broadcast notification' });
    } finally {
      setSending(false);
    }
  };

  const getTypeBadge = (t) => {
    switch (t) {
      case 'announcement':
        return <span className="badge bg-primary rounded-pill px-2.5 py-1">Announcement</span>;
      case 'reminder':
        return <span className="badge bg-warning text-dark rounded-pill px-2.5 py-1">Exam Reminder</span>;
      case 'schedule_change':
        return <span className="badge bg-danger rounded-pill px-2.5 py-1">Schedule Change</span>;
      case 'result_notice':
        return <span className="badge bg-success rounded-pill px-2.5 py-1">Result Notice</span>;
      case 'instruction':
        return <span className="badge bg-info text-dark rounded-pill px-2.5 py-1">Important Instruction</span>;
      default:
        return <span className="badge bg-secondary rounded-pill px-2.5 py-1">{t}</span>;
    }
  };

  return (
    <div className="row g-4" id="examiner-notifications-panel">
      {/* Broadcast Form */}
      <div className="col-lg-5">
        <div className="card border-0 shadow-sm rounded-4 p-4">
          <span className="badge bg-warning text-dark mb-1 text-uppercase fw-semibold align-self-start">
            Broadcast Notice
          </span>
          <h5 className="fw-bold mb-1 text-dark">Send Candidate Notification</h5>
          <p className="text-muted small mb-3">Push announcements, reminders, and alerts directly to student portals</p>

          {toast && (
            <div className={`alert alert-${toast.type} alert-dismissible fade show py-2 small rounded-3 mb-3`} role="alert">
              <i className={`bi ${toast.type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'} me-2`} />
              <span>{toast.text}</span>
              <button type="button" className="btn-close py-2" onClick={() => setToast(null)} />
            </div>
          )}

          <form onSubmit={handleSend} className="d-flex flex-column gap-3">
            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Notification Type <span className="text-danger">*</span>
              </label>
              <select
                className="form-select rounded-3"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                <option value="announcement">General Announcement</option>
                <option value="reminder">Exam Schedule Reminder</option>
                <option value="schedule_change">Emergency Schedule Change</option>
                <option value="result_notice">Result Scorecard Publication</option>
                <option value="instruction">Important Proctoring Instruction</option>
              </select>
            </div>

            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Notice Title <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                className="form-control rounded-3"
                placeholder="e.g. Mandatory Briefing for Technical Exam"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Target Examination (Optional)
              </label>
              <select
                className="form-select rounded-3"
                value={targetExamId}
                onChange={(e) => setTargetExamId(e.target.value)}
              >
                <option value="">-- All Registered Candidates --</option>
                {exams.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Message Content <span className="text-danger">*</span>
              </label>
              <textarea
                rows={4}
                className="form-control rounded-3"
                placeholder="Write message details for candidate briefing..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary rounded-3 py-2 d-flex align-items-center justify-content-center gap-2 shadow-sm"
              disabled={sending}
            >
              {sending ? (
                <>
                  <span className="spinner-border spinner-border-sm" />
                  Broadcasting...
                </>
              ) : (
                <>
                  <i className="bi bi-send-fill" />
                  Broadcast Notification
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Broadcast History Feed */}
      <div className="col-lg-7">
        <div className="card border-0 shadow-sm rounded-4 p-4 h-100">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <div>
              <h5 className="fw-bold mb-0 text-dark">Notification History</h5>
              <p className="text-muted small mb-0">List of announcements and alerts transmitted</p>
            </div>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary rounded-3"
              onClick={fetchData}
            >
              <i className="bi bi-arrow-clockwise" /> Refresh
            </button>
          </div>

          {loading ? (
            <div className="p-4 text-center">
              <div className="spinner-border text-primary" role="status" />
              <p className="text-muted small mt-2">Loading notification records...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <i className="bi bi-bell-slash display-4 d-block mb-3 opacity-30" />
              <h6 className="fw-semibold">No notifications sent yet</h6>
            </div>
          ) : (
            <div className="d-flex flex-column gap-3">
              {notifications.map((n) => (
                <div key={n.id} className="p-3 border rounded-3 bg-light d-flex flex-column gap-1.5">
                  <div className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center gap-2">
                      {getTypeBadge(n.type)}
                      <h6 className="fw-bold text-dark mb-0">{n.title}</h6>
                    </div>
                    <span className="text-muted small font-monospace">{n.sent_at}</span>
                  </div>
                  <p className="text-muted small mb-1">{n.message}</p>
                  <div className="text-secondary small d-flex align-items-center gap-1">
                    <i className="bi bi-people" />
                    <span>Sent to {n.recipients_count || 48} candidates</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExaminerNotificationsPanel;
