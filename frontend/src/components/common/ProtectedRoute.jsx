import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Loader from './Loader';

/**
 * ProtectedRoute Component
 * Guards routes against unauthenticated access and strictly restricts unauthorized roles,
 * redirecting users to their role-specific dashboard to prevent feature cross-bleed.
 *
 * @param {Object} props
 * @param {React.ReactNode} props.children
 * @param {string[]} [props.allowedRoles]
 */
const ProtectedRoute = ({ children, allowedRoles = [] }) => {
  const { isAuthenticated, loading, role } = useAuth();
  const location = useLocation();

  if (loading) {
    return <Loader text="Checking session authorization..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  const normalizedUserRole = role?.toLowerCase();
  const normalizedAllowedRoles = allowedRoles.map((r) => r.toLowerCase());

  if (normalizedAllowedRoles.length > 0 && !normalizedAllowedRoles.includes(normalizedUserRole)) {
    // Strictly isolate unauthorized role navigation by redirecting to their respective dashboard
    const roleRedirectMap = {
      admin: '/admin',
      examiner: '/examiner',
      student: '/student',
    };

    const targetPath = roleRedirectMap[normalizedUserRole] || '/login';
    return <Navigate to={targetPath} replace />;
  }

  return children;
};

export default ProtectedRoute;
