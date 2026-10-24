import React, { useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useStudent } from '../../context/StudentContext';
import UpcomingExamCard from '../../components/student/UpcomingExamCard';
import AssignedExamsList from '../../components/student/AssignedExamsList';

const StudentDashboardHome = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { 
    exams, upcomingExams, activeExams, results, 
    loadingExams, loadingResults, 
    examsError, resultsError, 
    fetchExams, fetchResults 
  } = useStudent();

  useEffect(() => {
    fetchExams();
    fetchResults();
  }, [fetchExams, fetchResults]);

  // Derived calculations
  const completedExamIds = new Set(
    results.map(r => r.exam_id || r.exam?.id).filter(Boolean)
  );

  // Filter exams that are assigned and NOT completed
  const pendingAssignedExams = exams.filter(e => {
    const isCompleted =
      e.status === 'completed' ||
      Boolean(e.attempt_id) ||
      completedExamIds.has(e.id);
    const isClosed = e.status === 'closed' || e.status === 'expired';
    return !isCompleted && !isClosed;
  });

  const pendingCount = pendingAssignedExams.length;
  const completedCount = Math.max(
    results.length,
    exams.filter(e => e.status === 'completed' || Boolean(e.attempt_id)).length
  );
  const avgScore = results.length > 0
    ? (results.reduce((acc, curr) => {
        const score = curr.score_obtained !== undefined ? curr.score_obtained : (curr.score ?? curr.total_marks_obtained ?? 0);
        const total = curr.total_marks || curr.total_marks_possible || curr.exam?.total_marks || 100;
        return acc + (total ? (score / total) * 100 : 0);
      }, 0) / results.length).toFixed(1)
    : '0.0';

  const recentResult = results.length > 0 ? results[0] : null;
  const overallRank = recentResult?.rank ? `#${recentResult.rank}` : (results.length > 0 ? '#1' : 'N/A');

  const sortedUpcoming = [...upcomingExams]
    .filter(e => !completedExamIds.has(e.id) && e.status !== 'completed' && !e.attempt_id)
    .sort((a, b) => {
      if (!a.scheduled_start) return 1;
      if (!b.scheduled_start) return -1;
      return new Date(a.scheduled_start) - new Date(b.scheduled_start);
    });
  
  const featuredExam = sortedUpcoming.length > 0 ? sortedUpcoming[0] : null;

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* ── 1. DASHBOARD HEADER ──────────────────────────────────────────────── */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-2">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 text-uppercase tracking-wider">Candidate Portal</span>
            {activeExams.length > 0 && (
              <span className="badge bg-success">
                <i className="bi bi-circle-fill me-1 small text-white" style={{ animation: 'pulse 2s infinite' }}></i>
                {activeExams.length} Active Now
              </span>
            )}
          </div>
          <h1 className="h4 mb-0 fw-bold">Welcome, {user?.full_name || user?.name || user?.email?.split('@')[0] || 'Student'} 👋</h1>
          <p className="text-muted mb-0 small">Track your assigned exams, academic performance, real-time ranks, and recent results.</p>
        </div>
        <div className="d-flex align-items-center gap-2">
          <button
            className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1.5 rounded-3"
            onClick={() => {
              fetchExams();
              fetchResults();
            }}
            title="Refresh dashboard"
          >
            <i className="bi bi-arrow-clockwise"></i>
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* ── 2. SUMMARY METRIC CARDS ─────────────────────────────────────────── */}
      <div className="row g-3 mb-4">
        {/* Assigned */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 h-100 p-3">
            <div className="d-flex align-items-center gap-3">
              <div className="p-2.5 bg-primary bg-opacity-10 text-primary rounded-3 fs-4">
                <i className="bi bi-journal-text"></i>
              </div>
              <div>
                <div className="text-muted small">Assigned</div>
                <h4 className="mb-0 fw-bold">{pendingCount}</h4>
              </div>
            </div>
          </div>
        </div>

        {/* Completed */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 h-100 p-3">
            <div className="d-flex align-items-center gap-3">
              <div className="p-2.5 bg-success bg-opacity-10 text-success rounded-3 fs-4">
                <i className="bi bi-check2-circle"></i>
              </div>
              <div>
                <div className="text-muted small">Completed</div>
                <h4 className="mb-0 fw-bold">{completedCount}</h4>
              </div>
            </div>
          </div>
        </div>

        {/* Overall Score */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 h-100 p-3">
            <div className="d-flex align-items-center gap-3">
              <div className="p-2.5 bg-info bg-opacity-10 text-info rounded-3 fs-4">
                <i className="bi bi-percent"></i>
              </div>
              <div>
                <div className="text-muted small">Overall Score</div>
                <h4 className="mb-0 fw-bold text-primary">{avgScore}%</h4>
              </div>
            </div>
          </div>
        </div>

        {/* Overall Rank */}
        <div className="col-6 col-lg-3">
          <div className="card border-0 shadow-sm rounded-4 h-100 p-3">
            <div className="d-flex align-items-center gap-3">
              <div className="p-2.5 bg-warning bg-opacity-10 text-warning rounded-3 fs-4">
                <i className="bi bi-trophy-fill"></i>
              </div>
              <div>
                <div className="text-muted small">Overall Rank</div>
                <h4 className="mb-0 fw-bold text-dark">{overallRank}</h4>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── 3. RECENT EXAMINATION RESULTS STRIP ─────────────────────────── */}
      {recentResult && (
        <div className="card shadow-sm border-0 rounded-4 mb-4" style={{ background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(14, 165, 233, 0.08) 100%)', border: '1px solid rgba(79, 70, 229, 0.15)' }}>
          <div className="card-body p-3 p-md-4">
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div className="d-flex align-items-center gap-3">
                <div className="p-3 bg-primary bg-opacity-20 text-primary rounded-circle fs-4">
                  <i className="bi bi-award-fill"></i>
                </div>
                <div>
                  <span className="badge bg-primary text-uppercase tracking-wider mb-1" style={{ fontSize: '0.65rem' }}>Recent Result</span>
                  <h5 className="fw-bold mb-0 text-dark">{recentResult.title || recentResult.exam?.title || 'Examination Assessment'}</h5>
                </div>
              </div>

              <div className="d-flex align-items-center gap-4 flex-wrap">
                <div>
                  <div className="text-muted small">Score</div>
                  <div className="fw-bold fs-5 text-dark">
                    {recentResult.percentage !== undefined 
                      ? recentResult.percentage 
                      : (recentResult.total_marks_possible ? ((recentResult.total_marks_obtained / recentResult.total_marks_possible) * 100).toFixed(1) : '0.0')}%
                  </div>
                </div>
                <div>
                  <div className="text-muted small">Rank</div>
                  <div className="fw-bold fs-5 text-primary">{recentResult.rank ? `#${recentResult.rank}` : '#1'}</div>
                </div>
                <div>
                  <div className="text-muted small">Status</div>
                  <span className={`badge bg-${recentResult.is_passed || recentResult.pass_fail ? 'success' : 'danger'} bg-opacity-10 text-${recentResult.is_passed || recentResult.pass_fail ? 'success' : 'danger'} border border-${recentResult.is_passed || recentResult.pass_fail ? 'success' : 'danger'} border-opacity-25 px-2.5 py-1.5 fw-bold`}>
                    <i className={`bi bi-${recentResult.is_passed || recentResult.pass_fail ? 'check-circle-fill' : 'x-circle-fill'} me-1`}></i>
                    {recentResult.is_passed || recentResult.pass_fail ? 'PASS' : 'FAIL'}
                  </span>
                </div>
                <Link to="/student/results" className="btn btn-sm btn-outline-primary rounded-3 px-3">
                  View Exam History <i className="bi bi-arrow-right"></i>
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 4. MAIN WORKSPACE (Upcoming & Assigned) ────────────────────────── */}
      <div className="row g-4">
        {/* Main Column: Upcoming & Assigned */}
        <div className="col-12">
          {featuredExam && (
            <div className="mb-4">
              <UpcomingExamCard exam={featuredExam} />
            </div>
          )}
          
          <div className="mb-4">
            <AssignedExamsList exams={pendingAssignedExams} loading={loadingExams} error={examsError} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentDashboardHome;
