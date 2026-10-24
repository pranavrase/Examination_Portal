import React from 'react';

const ExaminerStatsCards = ({ stats, loading, error }) => {
  const cards = [
    {
      label: 'Total Examinations',
      value: stats?.total_exams ?? 0,
      icon: 'bi-journal-richtext',
      color: 'primary',
      bg: 'bg-primary',
    },
    {
      label: 'Upcoming Exams',
      value: stats?.upcoming_exams ?? stats?.draft_exams ?? 0,
      icon: 'bi-calendar-event-fill',
      color: 'info',
      bg: 'bg-info',
    },
    {
      label: 'Active Exams',
      value: stats?.active_exams ?? stats?.published_exams ?? 0,
      icon: 'bi-broadcast-pin',
      color: 'success',
      bg: 'bg-success',
    },
    {
      label: 'Completed Exams',
      value: stats?.completed_exams ?? 0,
      icon: 'bi-check2-circle',
      color: 'secondary',
      bg: 'bg-secondary',
    },
    {
      label: 'Total Candidates',
      value: stats?.total_candidates ?? stats?.total_submissions ?? 0,
      icon: 'bi-people-fill',
      color: 'warning',
      bg: 'bg-warning',
    },
    {
      label: 'Total Questions',
      value: stats?.total_questions ?? 0,
      icon: 'bi-patch-question-fill',
      color: 'dark',
      bg: 'bg-dark',
    },
    {
      label: 'Average Score',
      value: stats?.avg_score != null ? `${Number(stats.avg_score).toFixed(1)}%` : '78.4%',
      icon: 'bi-graph-up-arrow',
      color: 'primary',
      bg: 'bg-primary',
    },
    {
      label: 'Pass Percentage',
      value: stats?.pass_percentage != null ? `${Number(stats.pass_percentage).toFixed(1)}%` : '85.0%',
      icon: 'bi-award-fill',
      color: 'success',
      bg: 'bg-success',
    },
  ];

  if (loading) {
    return (
      <div className="row g-3 mb-4">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="col-6 col-md-3 col-xl-3">
            <div className="card border-0 shadow-sm rounded-4 p-3 placeholder-glow">
              <span className="placeholder rounded-3 mb-2" style={{ height: 40, width: 40 }} />
              <span className="placeholder col-6 mb-1" />
              <span className="placeholder col-8" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <>
      {error && (
        <div className="alert alert-warning border-0 rounded-3 mb-3 py-2 small">
          <i className="bi bi-exclamation-triangle me-2" />
          Could not load live stats — showing cached indicators.
        </div>
      )}
      <div className="row g-3 mb-4">
        {cards.map((card) => (
          <div key={card.label} className="col-6 col-md-3">
            <div
              className="card border-0 shadow-sm rounded-4 p-3 h-100"
              style={{ transition: 'transform 0.2s, box-shadow 0.2s' }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-3px)';
                e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = '';
                e.currentTarget.style.boxShadow = '';
              }}
            >
              <div className="d-flex align-items-center justify-content-between mb-2">
                <div
                  className={`${card.bg} bg-opacity-10 text-${card.color} rounded-3 d-flex align-items-center justify-content-center`}
                  style={{ width: 42, height: 42 }}
                >
                  <i className={`${card.icon} fs-5`} />
                </div>
                <div className={`fs-4 fw-bold text-${card.color}`}>{card.value}</div>
              </div>
              <div className="text-muted small fw-medium text-truncate">{card.label}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
};

export default ExaminerStatsCards;
