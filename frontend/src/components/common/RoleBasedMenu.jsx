import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/**
 * RoleBasedMenu Component
 * Renders navigation sections and links tailored STRICTLY and ISOLATED to the authenticated user's role.
 * Features of respective roles are strictly isolated and never merge with other roles.
 *
 * @param {Object} props
 * @param {Function} [props.onItemClick] - Callback fired when a menu item is clicked
 * @param {boolean} [props.isCollapsed] - Whether the sidebar is in collapsed (icon-only) mode
 */
const RoleBasedMenu = ({ onItemClick, isCollapsed = false }) => {
  const { role } = useAuth();
  const location = useLocation();
  const normalizedRole = role?.toLowerCase();

  const isAdmin = normalizedRole === 'admin';
  const isExaminer = normalizedRole === 'examiner';
  const isStudent = normalizedRole === 'student';



  const handleClick = (e) => {
    if (onItemClick) {
      onItemClick(e);
    }
  };

  return (
    <div className="role-based-menu d-flex flex-column gap-3">
      {/* ── 1. ADMIN ONLY SECTION ────────────────────────────────────────── */}
      {isAdmin && (
        <div className="menu-section">
          {!isCollapsed && (
            <div className="text-uppercase text-danger fw-bold px-3 mb-2 tracking-wider d-flex align-items-center gap-1.5" style={{ fontSize: '0.68rem', letterSpacing: '0.08em' }}>
              <i className="bi bi-shield-shaded" style={{ fontSize: '0.75rem' }} />
              Administration
            </div>
          )}
          <ul className="nav nav-pills flex-column gap-1">
            <li className="nav-item">
              <NavLink
                to="/admin"
                end
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-danger text-white fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-speedometer2 ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Admin Dashboard</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/activity-monitoring"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-danger text-white fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-activity ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>System Activity Logs</span>}
              </NavLink>
            </li>
          </ul>
        </div>
      )}

      {/* ── 2. EXAMINER & ADMIN WORKSPACE SECTION ──────────────────────── */}
      {(isExaminer || isAdmin) && (
        <div className="menu-section">
          {!isCollapsed && (
            <div className="text-uppercase text-warning fw-bold px-3 mb-2 tracking-wider d-flex align-items-center gap-1.5" style={{ fontSize: '0.68rem', letterSpacing: '0.08em' }}>
              <i className="bi bi-shield-lock-fill" style={{ fontSize: '0.75rem' }} />
              Examiner Workspace
            </div>
          )}
          <ul className="nav nav-pills flex-column gap-1">
            {/* Dashboard Overview */}
            <li className="nav-item">
              <NavLink
                to="/examiner"
                end
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-speedometer2 ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Dashboard</span>}
              </NavLink>
            </li>

            {/* All Examinations */}
            <li className="nav-item">
              <NavLink
                to="/examiner/exams"
                end
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-journal-richtext ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>All Examinations</span>}
              </NavLink>
            </li>

            {/* All Questions */}
            <li className="nav-item">
              <NavLink
                to="/examiner/question-bank"
                end
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-collection-play ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>All Questions</span>}
              </NavLink>
            </li>

            {/* All Candidates */}
            <li className="nav-item">
              <NavLink
                to="/examiner/candidates"
                end
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-people-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>All Candidates</span>}
              </NavLink>
            </li>

            {/* Live Monitoring */}
            <li className="nav-item">
              <NavLink
                to="/examiner/monitoring"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center align-items-center' : 'align-items-center justify-content-between'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <div className={`d-flex ${isCollapsed ? '' : 'align-items-center gap-3'}`}>
                  <i className={`bi bi-display ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                  {!isCollapsed && <span>Live Monitoring</span>}
                </div>
                {!isCollapsed && (
                  <span className="badge bg-danger rounded-pill px-2 py-0.5" style={{ fontSize: '0.62rem' }}>
                    LIVE
                  </span>
                )}
              </NavLink>
            </li>

            {/* Activity Logs */}
            <li className="nav-item">
              <NavLink
                to="/examiner/activity-logs"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-activity ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Activity Logs</span>}
              </NavLink>
            </li>

            {/* Results Management */}
            <li className="nav-item">
              <NavLink
                to="/examiner/results"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-award-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Results</span>}
              </NavLink>
            </li>

            {/* Performance Reports */}
            <li className="nav-item">
              <NavLink
                to="/examiner/reports"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-bar-chart-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Performance Reports</span>}
              </NavLink>
            </li>

            {/* Rankings */}
            <li className="nav-item">
              <NavLink
                to="/examiner/rankings"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-trophy-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Rankings</span>}
              </NavLink>
            </li>

            {/* Notifications */}
            <li className="nav-item">
              <NavLink
                to="/examiner/notifications"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-bell-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Notifications</span>}
              </NavLink>
            </li>

            {/* Profile */}
            <li className="nav-item">
              <NavLink
                to="/examiner/profile"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-warning text-dark fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-person-badge-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Profile</span>}
              </NavLink>
            </li>
          </ul>
        </div>
      )}

      {/* ── 3. STUDENT ONLY SECTION ──────────────────────────────────────── */}
      {isStudent && (
        <div className="menu-section">
          {!isCollapsed && (
            <div className="text-uppercase text-primary fw-bold px-3 mb-2 tracking-wider d-flex align-items-center gap-1.5" style={{ fontSize: '0.68rem', letterSpacing: '0.08em' }}>
              <i className="bi bi-mortarboard-fill" style={{ fontSize: '0.75rem' }} />
              Candidate Portal
            </div>
          )}
          <ul className="nav nav-pills flex-column gap-1">
            <li className="nav-item">
              <NavLink
                to="/student"
                end
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-speedometer2 ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Dashboard</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/student/exams"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-journal-text ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>My Exams</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/student/performance"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-pie-chart-fill ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Performance</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/student/leaderboard"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-trophy ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Leaderboard</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/student/results"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-clock-history ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Exam History</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/student/profile"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-person-circle ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Profile</span>}
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink
                to="/student/notifications"
                className={({ isActive }) =>
                  `nav-link d-flex ${isCollapsed ? 'justify-content-center' : 'align-items-center gap-3'} ${isCollapsed ? 'px-1' : 'px-3'} py-2 rounded-3 text-white transition-all ${
                    isActive ? 'active bg-primary fw-semibold shadow-sm' : 'opacity-75 hover-opacity-100'
                  }`
                }
                onClick={handleClick}
              >
                <i className={`bi bi-bell ${isCollapsed ? 'fs-4' : 'fs-5'}`} />
                {!isCollapsed && <span>Notifications</span>}
              </NavLink>
            </li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default RoleBasedMenu;
