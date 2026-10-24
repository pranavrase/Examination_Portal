import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Loader from './Loader';

export const getRoleDashboardPath = (role) => {
  switch (role?.toLowerCase()) {
    case 'admin':
      return '/admin';
    case 'examiner':
      return '/examiner';
    case 'student':
      return '/student';
    default:
      return '/student';
  }
};

const RoleBasedRedirect = () => {
  const { role, isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Loader text="Redirecting to your dashboard..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const targetPath = getRoleDashboardPath(role);
  return <Navigate to={targetPath} replace />;
};

export default RoleBasedRedirect;
