import React, { createContext, useState, useContext, useCallback, useMemo } from 'react';
import {
  getAdminStats,
  getUsers,
  updateUserRole,
  deactivateUser as apiDeactivateUser,
  getActivityLogs,
  createExaminer as apiCreateExaminer,
  deleteExaminer as apiDeleteExaminer,
} from '../api/adminApi';

const AdminContext = createContext(null);

export const AdminProvider = ({ children }) => {
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [activityLogs, setActivityLogs] = useState([]);

  // Granular loading states for performance & UI smoothness
  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Flags to distinguish initial load (show skeleton) from background updates (keep data visible)
  const [hasLoadedStatsOnce, setHasLoadedStatsOnce] = useState(false);
  const [hasLoadedUsersOnce, setHasLoadedUsersOnce] = useState(false);
  const [hasLoadedLogsOnce, setHasLoadedLogsOnce] = useState(false);

  // Errors
  const [statsError, setStatsError] = useState(null);
  const [usersError, setUsersError] = useState(null);
  const [logsError, setLogsError] = useState(null);
  const [actionError, setActionError] = useState(null);

  // Success notifications
  const [successMessage, setSuccessMessage] = useState(null);

  const fetchStats = useCallback(async (signal = undefined) => {
    setLoadingStats(true);
    setStatsError(null);
    try {
      const data = await getAdminStats(signal);
      setStats(data);
      setHasLoadedStatsOnce(true);
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return; // Request was cleanly cancelled; ignore
      }
      setStatsError(err?.response?.data?.detail || err?.message || 'Unable to load platform statistics. Please try again.');
      // Preserve previously loaded stats if a background refresh fails
    } finally {
      setLoadingStats(false);
    }
  }, []);

  const fetchUsersList = useCallback(async (searchQuery = '', roleFilter = '', statusFilter = '', signal = undefined) => {
    setLoadingUsers(true);
    setUsersError(null);
    try {
      const params = {};
      // Backend accepts 'email' and 'full_name' as search filters
      if (searchQuery) {
        params.email = searchQuery;
        params.full_name = searchQuery;
      }
      if (roleFilter && roleFilter !== 'all') params.role = roleFilter;
      if (statusFilter && statusFilter !== 'all') params.is_active = statusFilter === 'active';

      const data = await getUsers(params, signal);
      const userList = Array.isArray(data) ? data : data?.users || data?.items || [];
      setUsers(userList);
      setHasLoadedUsersOnce(true);
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return; // Request was cleanly cancelled; ignore
      }
      setUsersError(err?.response?.data?.detail || err?.message || 'Unable to load users. Please try again.');
      // Preserve previously loaded user data if background refresh fails; do not wipe existing users!
      setUsers((prev) => (prev && prev.length > 0 ? prev : []));
    } finally {
      setLoadingUsers(false);
    }
  }, []);

  const fetchLogs = useCallback(async (params = {}, signal = undefined) => {
    setLoadingLogs(true);
    setLogsError(null);
    try {
      const data = await getActivityLogs(params, signal);
      const logList = Array.isArray(data) ? data : data?.logs || data?.items || [];
      setActivityLogs(logList);
      setHasLoadedLogsOnce(true);
    } catch (err) {
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED') {
        return; // Request was cleanly cancelled; ignore
      }
      setLogsError(err?.response?.data?.detail || err?.message || 'Unable to load activity logs. Please try again.');
      // Preserve previously loaded logs; do not wipe existing records on refresh error
      setActivityLogs((prev) => (prev && prev.length > 0 ? prev : []));
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  const updateRole = useCallback(async (userId, newRole) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await updateUserRole(userId, newRole);
      setSuccessMessage(`User role successfully updated to '${newRole}'`);
      await fetchUsersList();
      await fetchStats();
      return true;
    } catch (err) {
      setActionError(err?.response?.data?.detail || err?.message || 'Failed to update user role');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [fetchUsersList, fetchStats]);

  const deactivateUserAccount = useCallback(async (userId) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await apiDeactivateUser(userId);
      setSuccessMessage('User account successfully deactivated');
      await fetchUsersList();
      await fetchStats();
      return true;
    } catch (err) {
      setActionError(err?.response?.data?.detail || err?.message || 'Failed to deactivate user account');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [fetchUsersList, fetchStats]);

  const createExaminerAccount = useCallback(async (data) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await apiCreateExaminer(data);
      setSuccessMessage(`Examiner account '${data.email}' successfully created`);
      await fetchUsersList();
      await fetchStats();
      return res;
    } catch (err) {
      setActionError(err?.response?.data?.detail || err?.message || 'Failed to create examiner account');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [fetchUsersList, fetchStats]);

  const deleteExaminerAccount = useCallback(async (userId) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const res = await apiDeleteExaminer(userId);
      setSuccessMessage('Examiner account successfully deleted');
      await fetchUsersList();
      await fetchStats();
      return res;
    } catch (err) {
      setActionError(err?.response?.data?.detail || err?.message || 'Failed to delete examiner account');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, [fetchUsersList, fetchStats]);

  const clearMessages = useCallback(() => {
    setSuccessMessage(null);
    setActionError(null);
  }, []);

  const value = useMemo(() => ({
    stats,
    users,
    activityLogs,
    loadingStats,
    loadingUsers,
    loadingLogs,
    hasLoadedStatsOnce,
    hasLoadedUsersOnce,
    hasLoadedLogsOnce,
    actionLoading,
    statsError,
    usersError,
    logsError,
    actionError,
    successMessage,
    fetchStats,
    fetchUsers: fetchUsersList,
    fetchActivityLogs: fetchLogs,
    updateRole,
    deactivateUser: deactivateUserAccount,
    createExaminer: createExaminerAccount,
    deleteExaminer: deleteExaminerAccount,
    clearMessages,
  }), [
    stats,
    users,
    activityLogs,
    loadingStats,
    loadingUsers,
    loadingLogs,
    hasLoadedStatsOnce,
    hasLoadedUsersOnce,
    hasLoadedLogsOnce,
    actionLoading,
    statsError,
    usersError,
    logsError,
    actionError,
    successMessage,
    fetchStats,
    fetchUsersList,
    fetchLogs,
    updateRole,
    deactivateUserAccount,
    createExaminerAccount,
    deleteExaminerAccount,
    clearMessages,
  ]);

  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
};

export const useAdmin = () => {
  const context = useContext(AdminContext);
  if (!context) {
    throw new Error('useAdmin must be used within an AdminProvider');
  }
  return context;
};

export default AdminContext;
