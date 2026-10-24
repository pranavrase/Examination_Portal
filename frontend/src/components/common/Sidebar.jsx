import React, { useState } from 'react';
import RoleBasedMenu from './RoleBasedMenu';

/**
 * Sidebar Component
 * Collapsible responsive sidebar drawer rendering RoleBasedMenu.
 * Supports desktop fixed placement, icon-only collapse mode, and mobile off-canvas drawer with backdrop overlay.
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Mobile drawer open state
 * @param {Function} props.onClose - Function to close mobile drawer
 * @param {Function} props.onWidthChange - Callback for sidebar width changes
 */
const Sidebar = ({ isOpen, onClose, onWidthChange }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
    // Only notify layout of width change on desktop
    if (onWidthChange && window.innerWidth >= 992) {
      onWidthChange(!isCollapsed ? 70 : 260);
    }
  };

  return (
    <>
      {/* Offcanvas Overlay for Mobile / Tablet */}
      {isOpen && (
        <div
          className="sidebar-overlay d-lg-none"
          onClick={onClose}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1035,
            backdropFilter: 'blur(2px)',
          }}
          aria-hidden="true"
        />
      )}

      {/* Desktop Sidebar - Always Visible */}
      <aside
        className={`sidebar bg-dark text-white border-end border-secondary border-opacity-25 d-none d-lg-block ${
          isCollapsed ? 'sidebar-collapsed' : ''
        }`}
        style={{
          width: isCollapsed ? '70px' : '260px',
          position: 'fixed',
          top: '56px',
          left: 0,
          height: 'calc(100vh - 56px)',
          zIndex: 1040,
          overflow: 'hidden',
          padding: isCollapsed ? '0.5rem' : '1rem',
          transition: 'width 0.3s ease-in-out',
        }}
      >
        {/* Desktop collapse toggle */}
        <div className={`d-flex ${isCollapsed ? 'justify-content-center' : 'justify-content-end'} mb-2`}>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary text-white border-0 p-1"
            onClick={toggleCollapse}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{
              opacity: 0.7,
              transition: 'opacity 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '0.7'}
          >
            <i className={`bi bi-${isCollapsed ? 'arrow-right' : 'arrow-left'}`} />
          </button>
        </div>

        {/* Role-Based Navigation Links */}
        <RoleBasedMenu onItemClick={onClose} isCollapsed={isCollapsed} />
      </aside>

      {/* Mobile Sidebar - Offcanvas Drawer */}
      <aside
        className={`sidebar bg-dark text-white border-end border-secondary border-opacity-25 d-lg-none ${
          isOpen ? 'sidebar-open' : ''
        }`}
        style={{
          width: '260px',
          position: 'fixed',
          top: '56px',
          left: 0,
          height: 'calc(100vh - 56px)',
          zIndex: 1040,
          overflow: 'hidden',
          padding: '1rem',
          transition: 'transform 0.3s ease-in-out',
          transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
        }}
      >
        {/* Mobile close header */}
        <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25">
          <span className="fw-bold text-muted small text-uppercase" style={{ letterSpacing: '0.05em' }}>
            Navigation Menu
          </span>
          <button
            type="button"
            className="btn-close btn-close-white btn-sm"
            onClick={onClose}
            aria-label="Close sidebar"
          />
        </div>

        {/* Role-Based Navigation Links */}
        <RoleBasedMenu onItemClick={onClose} isCollapsed={false} />
      </aside>
    </>
  );
};

export default Sidebar;
