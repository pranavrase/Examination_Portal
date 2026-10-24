import React from 'react';

const StatCard = ({ title, value, icon, colorClass = 'primary', loading }) => {
  return (
    <div className="col-12 col-sm-6 col-lg-3">
      <div className="card border-0 shadow-sm rounded-4 h-100 p-3 transition-hover">
        <div className="card-body p-0 d-flex align-items-center justify-content-between">
          <div>
            <h6 className="text-muted fw-semibold text-uppercase fs-7 mb-1 tracking-wide">{title}</h6>
            {loading ? (
              <div className="placeholder-glow">
                <span className="placeholder col-6 bg-secondary opacity-25 rounded" style={{ height: '28px' }}></span>
              </div>
            ) : (
              <h3 className="fw-bold mb-0 text-dark">{value !== undefined && value !== null ? value : 0}</h3>
            )}
          </div>
          <div className={`p-3 bg-${colorClass} bg-opacity-10 text-${colorClass} rounded-4 fs-3 d-flex align-items-center justify-content-center`} style={{ width: '56px', height: '56px' }}>
            <i className={`bi ${icon}`}></i>
          </div>
        </div>
      </div>
    </div>
  );
};

const SystemStatsCards = ({ stats, loading, error, onRefresh }) => {
  // Normalize stats response keys whether object, array, or nested
  const normalizedStats = {
    totalUsers: stats?.total_users ?? stats?.totalUsers ?? stats?.users_count ?? 0,
    students: stats?.students_count ?? stats?.students ?? stats?.totalStudents ?? 0,
    examiners: stats?.examiners_count ?? stats?.examiners ?? stats?.totalExaminers ?? 0,
    admins: stats?.admins_count ?? stats?.admins ?? stats?.totalAdmins ?? 0,
    activeUsers: stats?.active_users ?? stats?.activeUsers ?? stats?.active_count ?? 0,
    totalExams: stats?.total_exams ?? stats?.totalExams ?? stats?.exams_count ?? 0,
    publishedExams: stats?.published_exams ?? stats?.publishedExams ?? 0,
    totalAttempts: stats?.total_attempts ?? stats?.totalAttempts ?? stats?.attempts_count ?? 0,
  };

  return (
    <div className="mb-4">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h5 className="fw-bold text-dark mb-0 d-flex align-items-center gap-2">
          <i className="bi bi-graph-up-arrow text-primary"></i> System Statistics Overview
        </h5>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 rounded-pill px-3"
            disabled={loading}
          >
            <i className={`bi bi-arrow-clockwise ${loading ? 'spin' : ''}`}></i>
            <span>Refresh Stats</span>
          </button>
        )}
      </div>

      {error && (
        <div className="alert alert-warning border-0 shadow-sm rounded-3 d-flex align-items-center mb-3">
          <i className="bi bi-exclamation-triangle-fill flex-shrink-0 me-2 fs-5"></i>
          <div>
            <strong>Unable to load real-time statistics:</strong> {error}
          </div>
        </div>
      )}

      <div className="row g-3">
        <StatCard
          title="Total Users"
          value={normalizedStats.totalUsers}
          icon="bi-people-fill"
          colorClass="primary"
          loading={loading}
        />
        <StatCard
          title="Students Enrolled"
          value={normalizedStats.students}
          icon="bi-mortarboard-fill"
          colorClass="info"
          loading={loading}
        />
        <StatCard
          title="Examiners"
          value={normalizedStats.examiners}
          icon="bi-journal-code"
          colorClass="warning"
          loading={loading}
        />
        <StatCard
          title="Administrators"
          value={normalizedStats.admins}
          icon="bi-shield-check"
          colorClass="danger"
          loading={loading}
        />

        <StatCard
          title="Active Accounts"
          value={normalizedStats.activeUsers}
          icon="bi-person-check-fill"
          colorClass="success"
          loading={loading}
        />
        <StatCard
          title="Total Exams"
          value={normalizedStats.totalExams}
          icon="bi-file-earmark-code"
          colorClass="indigo"
          loading={loading}
        />
        <StatCard
          title="Published Exams"
          value={normalizedStats.publishedExams}
          icon="bi-check-all"
          colorClass="teal"
          loading={loading}
        />
        <StatCard
          title="Exam Attempts"
          value={normalizedStats.totalAttempts}
          icon="bi-bar-chart-line-fill"
          colorClass="purple"
          loading={loading}
        />
      </div>
    </div>
  );
};

export default SystemStatsCards;
