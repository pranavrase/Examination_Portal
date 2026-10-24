import React, { useState, useEffect, useCallback } from 'react';
import {
  getNotifications,
  markAsRead,
  markAllRead,
} from '../../api/notificationsApi';

// Map backend notification_type to Bootstrap icon + color
const TYPE_META = {
  EXAM_PUBLISHED: { icon: 'bi-journal-plus', color: 'primary' },
  RESULT_AVAILABLE: { icon: 'bi-award-fill', color: 'success' },
  EXAM_UPCOMING: { icon: 'bi-clock-history', color: 'warning' },
  SYSTEM: { icon: 'bi-megaphone-fill', color: 'info' },
  SECURITY_ALERT: { icon: 'bi-shield-exclamation', color: 'danger' },
  RANKING_AVAILABLE: { icon: 'bi-trophy-fill', color: 'warning' },
  EXAM_AUTO_SUBMITTED: { icon: 'bi-check2-circle', color: 'success' },
  ANNOUNCEMENT: { icon: 'bi-megaphone-fill', color: 'primary' },
  REMINDER: { icon: 'bi-bell-fill', color: 'warning' },
  SCHEDULE_CHANGE: { icon: 'bi-calendar-x-fill', color: 'danger' },
  RESULT_NOTICE: { icon: 'bi-award-fill', color: 'success' },
  INSTRUCTION: { icon: 'bi-info-circle-fill', color: 'info' },
  default: { icon: 'bi-bell-fill', color: 'secondary' },
};

const getMeta = (type) => {
  // Handle both uppercase (from backend) and lowercase (from frontend)
  const normalizedType = type ? type.toUpperCase() : 'SYSTEM';
  return TYPE_META[normalizedType] || TYPE_META.default;
};

const formatTimestamp = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  
  // Show time for very recent notifications
  if (diff < 60) return 'Just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min${Math.floor(diff / 60) > 1 ? 's' : ''} ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hour${Math.floor(diff / 3600) > 1 ? 's' : ''} ago`;
  
  // Show date and time for older notifications
  const dateOptions = { month: 'short', day: 'numeric', year: 'numeric' };
  const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: true };
  
  const formattedDate = date.toLocaleDateString('en-US', dateOptions);
  const formattedTime = date.toLocaleTimeString('en-US', timeOptions);
  
  return `${formattedDate} at ${formattedTime}`;
};

const NotificationsPage = () => {
  const [filter, setFilter] = useState('all'); // 'all' | 'unread'
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [markingAll, setMarkingAll] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page: 1, page_size: 50 };
      if (filter === 'unread') params.is_read = false;
      const data = await getNotifications(params);
      // Backend returns { items, total, page, page_size, unread_count }
      const list = Array.isArray(data) ? data : data?.items || [];
      // Show all notifications now that examiner can send various types
      setNotifications(list);
      setTotal(list.length);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load notifications');
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await markAllRead();
      // Optimistic local update
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (err) {
      console.warn('markAllRead failed:', err?.response?.data?.detail);
    } finally {
      setMarkingAll(false);
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.warn('markAsRead failed:', err?.response?.data?.detail);
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);



  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-warning text-dark text-uppercase tracking-wider">Candidate Alerts</span>
            {unreadCount > 0 && (
              <span className="badge bg-primary">{unreadCount} Unread</span>
            )}
          </div>
          <h1 className="h4 mb-0 fw-bold">Notifications &amp; Announcements</h1>
          <p className="text-muted mb-0 small">
            Stay informed regarding exam assignments and published results.
          </p>
        </div>
        <button
          className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1 rounded-3"
          onClick={handleMarkAllRead}
          disabled={markingAll || unreadCount === 0}
        >
          {markingAll ? (
            <span className="spinner-border spinner-border-sm me-1" role="status" />
          ) : (
            <i className="bi bi-check2-all" />
          )}
          Mark All as Read
        </button>
      </header>

      {/* Filter Tabs */}
      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-header bg-white border-bottom p-3 d-flex justify-content-between align-items-center">
          <div className="btn-group btn-group-sm">
            <button
              className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-light text-secondary'}`}
              onClick={() => setFilter('all')}
            >
              All Notifications ({notifications.length})
            </button>
            <button
              className={`btn ${filter === 'unread' ? 'btn-primary' : 'btn-light text-secondary'}`}
              onClick={() => setFilter('unread')}
            >
              Unread Only ({unreadCount})
            </button>
          </div>
          <button
            className="btn btn-sm btn-light border rounded-3"
            onClick={fetchNotifications}
            title="Refresh notifications"
          >
            <i className="bi bi-arrow-clockwise" />
          </button>
        </div>

        <div className="card-body p-0">
          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status" />
              <p className="text-muted mt-2 small">Loading notifications...</p>
            </div>
          ) : error ? (
            <div className="p-4">
              <div className="alert alert-danger rounded-3 mb-0">
                <i className="bi bi-exclamation-triangle-fill me-2" />{error}
              </div>
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center py-5 text-muted p-4">
              <div className="display-4 text-muted mb-2">
                <i className="bi bi-bell-slash" />
              </div>
              <h6 className="fw-bold">No Notifications</h6>
              <p className="small mb-0">You're all caught up with your examination notices.</p>
            </div>
          ) : (
            <div className="list-group list-group-flush">
              {notifications.map((item) => {
                const notificationType = item.entity_type || item.notification_type || item.type || 'SYSTEM';
                const { icon, color } = getMeta(notificationType);
                const isUnread = !item.is_read;

                return (
                  <div
                    key={item.id}
                    className={`list-group-item p-3 d-flex align-items-start gap-3 ${
                      isUnread ? 'bg-light bg-opacity-75 border-start border-primary border-3' : ''
                    }`}
                    style={{ cursor: isUnread ? 'pointer' : 'default' }}
                    onClick={() => isUnread && handleMarkRead(item.id)}
                    title={isUnread ? 'Click to mark as read' : ''}
                  >
                    <div className={`p-2 rounded-circle bg-${color} bg-opacity-10 text-${color} fs-5 mt-1 flex-shrink-0`}>
                      <i className={`bi ${icon}`} />
                    </div>
                    <div className="flex-grow-1 min-w-0">
                      <div className="d-flex justify-content-between align-items-start mb-1 gap-2">
                        <h6 className={`mb-0 text-truncate ${isUnread ? 'fw-bold text-dark' : 'text-dark'}`}>
                          {item.title}
                        </h6>
                        <small className="text-muted flex-shrink-0">
                          {formatTimestamp(item.created_at)}
                        </small>
                      </div>
                      <p className="text-secondary small mb-0 lh-base">{item.message}</p>
                      {notificationType && (
                        <span className={`badge bg-${color} bg-opacity-10 text-${color} border border-${color} border-opacity-25 mt-1`} style={{ fontSize: '0.65rem' }}>
                          {notificationType.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())}
                        </span>
                      )}
                    </div>
                    {isUnread && (
                      <div className="flex-shrink-0 mt-1">
                        <span className="badge rounded-pill bg-primary" style={{ width: '8px', height: '8px', padding: 0 }} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationsPage;
