import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { getUnreadCount } from '../../api/notificationsApi';

/**
 * Navbar Component
 * Reusable top navigation bar featuring app branding, role badge, user details,
 * dark/light mode toggle, mobile menu toggle, and logout button.
 * Uses strict role-based destination paths to prevent cross-role feature mixing.
 *
 * @param {Object} props
 * @param {Function} props.onToggleSidebar - Function to toggle responsive sidebar drawer
 */
const Navbar = ({ onToggleSidebar }) => {
  const { user, role, logout, isAuthenticated, loading } = useAuth();
  const { theme, isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  // Poll unread notification count every 60 seconds — only after auth is resolved
  useEffect(() => {
    // Wait for auth initialization to complete before making any API calls
    if (!isAuthenticated || loading) return;
    let cancelled = false;
    const fetchCount = async () => {
      try {
        const data = await getUnreadCount();
        if (!cancelled) setUnreadCount(data?.unread_count ?? 0);
      } catch {
        // Silently ignore — count badge is non-critical
      }
    };
    fetchCount();
    const interval = setInterval(fetchCount, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [isAuthenticated, loading]);


  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  const normalizedRole = role?.toLowerCase();

  const getRoleBadgeStyle = (roleStr) => {
    switch (roleStr?.toLowerCase()) {
      case 'admin':
        return 'bg-danger text-white';
      case 'examiner':
        return 'bg-warning text-dark';
      case 'student':
        return 'bg-primary text-white';
      default:
        return 'bg-secondary text-white';
    }
  };

  const dashboardPath = (() => {
    switch (normalizedRole) {
      case 'admin':
        return '/admin';
      case 'examiner':
        return '/examiner';
      case 'student':
        return '/student';
      default:
        return '/';
    }
  })();

  const notificationsPath = (() => {
    switch (normalizedRole) {
      case 'admin':
        return '/admin';
      case 'examiner':
        return '/examiner/notifications';
      case 'student':
        return '/student/notifications';
      default:
        return '/student/notifications';
    }
  })();

  const profilePath = (() => {
    switch (normalizedRole) {
      case 'admin':
        return '/admin';
      case 'examiner':
        return '/examiner/profile';
      case 'student':
        return '/student/profile';
      default:
        return '/student/profile';
    }
  })();

  const userInitial = user?.full_name?.charAt(0) || user?.name?.charAt(0) || user?.email?.charAt(0) || 'U';
  const userName = user?.full_name || user?.name || user?.email || 'User';

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark px-3 py-2 border-bottom border-secondary border-opacity-25 shadow-sm" style={{ position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1050, height: '56px' }}>
      <div className="container-fluid">
        {/* Mobile / Tablet Toggle Hamburger */}
        <button
          className="btn btn-outline-light btn-sm me-3 d-lg-none"
          onClick={onToggleSidebar}
          aria-label="Toggle Navigation Sidebar"
          type="button"
        >
          <i className="bi bi-list fs-5" />
        </button>

        {/* Branding & Logo */}
        <Link to={dashboardPath} className="navbar-brand d-flex align-items-center gap-2 fw-bold text-white fs-6 me-auto me-lg-4 text-decoration-none">
          <div className="bg-primary bg-gradient rounded-3 p-1 d-flex align-items-center justify-content-center" style={{ width: 30, height: 30 }}>
            <i className="bi bi-journal-code text-white fs-6" />
          </div>
          <span className="tracking-tight">ExamPortal</span>
        </Link>

        {/* User Info & Actions */}
        <div className="d-flex align-items-center gap-2 gap-sm-3">
          {/* Notifications Shortcut — Strictly Role Targeted */}
          <Link
            to={notificationsPath}
            className="btn btn-sm btn-outline-secondary text-white border-opacity-50 position-relative p-1.5 px-2 rounded-pill"
            title="Notifications & Announcements"
          >
            <i className="bi bi-bell-fill text-warning fs-6" />
            {unreadCount > 0 && (
              <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style={{ fontSize: '0.6rem' }}>
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </Link>

          {/* Theme Toggle Button (Dark / Light Mode) */}
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary text-white border-opacity-50 d-flex align-items-center gap-1.5 px-2.5 py-1 rounded-pill"
            onClick={toggleTheme}
            title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle dark / light theme"
            id="theme-toggle-btn"
          >
            {isDark ? (
              <>
                <i className="bi bi-sun-fill text-warning fs-6" />
                <span className="d-none d-md-inline small text-light">Light</span>
              </>
            ) : (
              <>
                <i className="bi bi-moon-stars-fill text-info fs-6" />
                <span className="d-none d-md-inline small text-light">Dark</span>
              </>
            )}
          </button>

          {/* User profile capsule — Strictly Role Targeted */}
          <Link
            to={profilePath}
            className="d-flex align-items-center gap-2 text-white pe-2 pe-sm-3 border-end border-secondary border-opacity-50 text-decoration-none"
            title="View Profile Settings"
          >
            <div
              className="avatar-circle bg-primary bg-opacity-25 text-primary border border-primary border-opacity-25 fw-bold rounded-circle d-flex align-items-center justify-content-center"
              style={{ width: '32px', height: '32px', fontSize: '0.85rem' }}
            >
              {userInitial.toUpperCase()}
            </div>
            <div className="d-none d-sm-flex flex-column text-end">
              <span className="fw-semibold lh-1 text-white" style={{ fontSize: '0.82rem' }}>{userName}</span>
              <span className={`badge ${getRoleBadgeStyle(role)} badge-sm mt-0.5 align-self-end text-uppercase`} style={{ fontSize: '0.62rem' }}>
                {role || 'User'}
              </span>
            </div>
          </Link>

          {/* Sign Out Button */}
          <button
            id="navbar-signout-btn"
            onClick={handleLogout}
            className="btn btn-outline-danger btn-sm d-flex align-items-center gap-1.5 px-2.5 py-1 rounded-pill"
            type="button"
            title="Sign out of your session"
          >
            <i className="bi bi-box-arrow-right" />
            <span className="d-none d-sm-inline small">Sign Out</span>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
