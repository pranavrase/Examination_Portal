import React, { useEffect, useState, useCallback } from 'react';
import { AdminProvider, useAdmin } from '../../context/AdminContext';
import SystemStatsCards from '../../components/admin/SystemStatsCards';
import UserManagementTable from '../../components/admin/UserManagementTable';
import RoleAssignmentModal from '../../components/admin/RoleAssignmentModal';
import CreateExaminerModal from '../../components/admin/CreateExaminerModal';

const AdminDashboardContent = () => {
  const {
    stats,
    users,
    loadingStats,
    loadingUsers,
    actionLoading,
    statsError,
    usersError,
    actionError,
    successMessage,
    fetchStats,
    fetchUsers,
    updateRole,
    deactivateUser,
    createExaminer,
    deleteExaminer,
    clearMessages,
  } = useAdmin();

  // Role Assignment Modal State
  const [selectedUserForRole, setSelectedUserForRole] = useState(null);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);

  // Create Examiner Modal State
  const [isCreateExaminerModalOpen, setIsCreateExaminerModalOpen] = useState(false);

  // Initial load with AbortController for clean cancellation on unmount
  useEffect(() => {
    const controller = new AbortController();
    fetchStats(controller.signal);
    fetchUsers('', '', '', controller.signal);

    return () => {
      controller.abort();
    };
  }, [fetchStats, fetchUsers]);

  // Handle Role Modal open
  const handleOpenRoleModal = useCallback((user) => {
    setSelectedUserForRole(user);
    setIsRoleModalOpen(true);
  }, []);

  const handleCloseRoleModal = useCallback(() => {
    setIsRoleModalOpen(false);
    setSelectedUserForRole(null);
  }, []);

  const handleOpenCreateExaminerModal = useCallback(() => {
    setIsCreateExaminerModalOpen(true);
  }, []);

  const handleCloseCreateExaminerModal = useCallback(() => {
    setIsCreateExaminerModalOpen(false);
  }, []);

  const handleCreateExaminer = useCallback(async (data) => {
    await createExaminer(data);
    handleCloseCreateExaminerModal();
  }, [createExaminer, handleCloseCreateExaminerModal]);

  const handleSaveRole = useCallback(async (userId, newRole) => {
    try {
      await updateRole(userId, newRole);
      handleCloseRoleModal();
    } catch (err) {
      // Error handled in context actionError
    }
  }, [updateRole, handleCloseRoleModal]);

  const handleSearchUsers = useCallback((query) => {
    fetchUsers(query);
  }, [fetchUsers]);

  const handleFilterUsers = useCallback((role, status) => {
    fetchUsers('', role, status);
  }, [fetchUsers]);

  const handleRetryUsers = useCallback(() => {
    fetchUsers();
  }, [fetchUsers]);

  return (
    <div className="container-fluid px-0">
      {/* Page Header */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
        <div>
          <span className="badge bg-danger mb-1 text-uppercase tracking-wider">Administrator Workspace</span>
          <h2 className="fw-bold mb-1 text-dark">System Administration Dashboard</h2>
          <p className="text-muted mb-0">Monitor examination statistics, manage user access, and inspect security audit logs</p>
        </div>
        <div className="d-flex align-items-center gap-2">
          <button
            className="btn btn-primary d-flex align-items-center gap-2 rounded-3"
            onClick={() => {
              fetchStats();
              fetchUsers();
            }}
          >
            <i className="bi bi-arrow-clockwise"></i>
            <span>Refresh Dashboard</span>
          </button>
        </div>
      </div>

      {/* Success Notification Alert */}
      {successMessage && (
        <div className="alert alert-success alert-dismissible fade show shadow-sm border-0 rounded-3 mb-4" role="alert">
          <i className="bi bi-check-circle-fill me-2 fs-5"></i>
          <span>{successMessage}</span>
          <button
            type="button"
            className="btn-close"
            aria-label="Close"
            onClick={clearMessages}
          ></button>
        </div>
      )}

      {/* Global Action Error Alert */}
      {actionError && (
        <div className="alert alert-danger alert-dismissible fade show shadow-sm border-0 rounded-3 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill me-2 fs-5"></i>
          <span>{actionError}</span>
          <button
            type="button"
            className="btn-close"
            aria-label="Close"
            onClick={clearMessages}
          ></button>
        </div>
      )}

      {/* 1. System Statistics Section */}
      <SystemStatsCards
        stats={stats}
        loading={loadingStats}
        error={statsError}
        onRefresh={fetchStats}
      />

      {/* 2. User Management Directory Section */}
      <UserManagementTable
        users={users}
        loading={loadingUsers}
        error={usersError}
        onOpenRoleModal={handleOpenRoleModal}
        onDeactivateUser={deactivateUser}
        onOpenCreateExaminer={handleOpenCreateExaminerModal}
        onDeleteExaminer={deleteExaminer}
        onSearchChange={handleSearchUsers}
        onFilterChange={handleFilterUsers}
        onRetry={handleRetryUsers}
      />

      {/* Role Assignment Modal */}
      <RoleAssignmentModal
        user={selectedUserForRole}
        isOpen={isRoleModalOpen}
        onClose={handleCloseRoleModal}
        onSave={handleSaveRole}
        loading={actionLoading}
        error={actionError}
      />

      {/* Create Examiner Modal */}
      <CreateExaminerModal
        isOpen={isCreateExaminerModalOpen}
        onClose={handleCloseCreateExaminerModal}
        onSave={handleCreateExaminer}
        loading={actionLoading}
        error={actionError}
      />
    </div>
  );
};

const AdminDashboardHome = () => {
  return (
    <AdminProvider>
      <AdminDashboardContent />
    </AdminProvider>
  );
};

export default AdminDashboardHome;
