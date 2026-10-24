import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import Sidebar from '../components/common/Sidebar';
import Footer from '../components/common/Footer';

/**
 * AppLayout Component
 * Primary application shell layout combining Navbar, Sidebar, Main Content, and Footer.
 * Supports both children prop and React Router <Outlet /> for nested route rendering.
 *
 * @param {Object} props
 * @param {React.ReactNode} [props.children] - Optional child node(s)
 */
const AppLayout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(260);

  const handleSidebarWidthChange = (width) => {
    setSidebarWidth(width);
  };

  return (
    <div style={{ backgroundColor: 'var(--app-bg)', minHeight: '100vh' }}>
      {/* Top Navigation Bar - Fixed */}
      <Navbar onToggleSidebar={() => setSidebarOpen((prev) => !prev)} />

      {/* Sidebar - Fixed */}
      <Sidebar 
        isOpen={sidebarOpen} 
        onClose={() => setSidebarOpen(false)} 
        onWidthChange={handleSidebarWidthChange}
      />

      {/* Main Content - Scrollable with margins */}
      <div
        className="p-3 p-md-4 overflow-auto"
        style={{ 
          marginLeft: `${sidebarWidth}px`,
          marginTop: '56px',
          height: 'calc(100vh - 56px)',
          transition: 'margin-left 0.3s ease-in-out'
        }}
      >
        <div style={{ minHeight: 'calc(100vh - 56px - 57px)' }}>
          {children ? children : <Outlet />}
        </div>

        {/* Footer at bottom of main content area */}
        <Footer />
      </div>
    </div>
  );
};

export default AppLayout;
