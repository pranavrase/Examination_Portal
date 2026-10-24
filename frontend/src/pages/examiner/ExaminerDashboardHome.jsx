import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ExaminerProvider, useExaminer } from '../../context/ExaminerContext';
import { useAuth } from '../../context/AuthContext';
import AppLayout from '../../layouts/AppLayout';
import ExaminerStatsCards from '../../components/examiner/ExaminerStatsCards';
import ExamListTable from '../../components/examiner/ExamListTable';
import ExamFormModal from '../../components/examiner/ExamFormModal';
import QuestionBankPanel from '../../components/examiner/QuestionBankPanel';
import CandidateManagementPanel from '../../components/examiner/CandidateManagementPanel';
import LiveMonitoringPanel from '../../components/examiner/LiveMonitoringPanel';
import ExaminerActivityLogsPanel from '../../components/examiner/ExaminerActivityLogsPanel';
import ExaminerResultsPanel from '../../components/examiner/ExaminerResultsPanel';
import PerformanceReportsPanel from '../../components/examiner/PerformanceReportsPanel';
import ExaminerRankingsPanel from '../../components/examiner/ExaminerRankingsPanel';
import ExaminerNotificationsPanel from '../../components/examiner/ExaminerNotificationsPanel';
import ExaminerProfilePanel from '../../components/examiner/ExaminerProfilePanel';
import SubmissionsTable from '../../components/examiner/SubmissionsTable';

// ─── View Enum ──────────────────────────────────────────────────────────────────
export const VIEW = {
  DASHBOARD: 'dashboard',
  EXAMS: 'exams',
  QUESTIONS: 'questions',
  CANDIDATES: 'candidates',
  MONITORING: 'monitoring',
  LOGS: 'logs',
  RESULTS: 'results',
  REPORTS: 'reports',
  RANKINGS: 'rankings',
  NOTIFICATIONS: 'notifications',
  PROFILE: 'profile',
};

// ─── Inner Component ────────────────────────────────────────────────────────────
const ExaminerDashboardContent = ({ initialView }) => {
  const { user } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const {
    stats,
    loadingStats,
    statsError,
    actionError,
    successMessage,
    clearMessages,
    fetchStats,
    fetchExams,
  } = useExaminer();

  // Determine active view based on route or prop
  const getViewFromPath = () => {
    const path = location.pathname;
    if (path.includes('/examiner/exams/create')) return VIEW.EXAMS;
    if (path.includes('/examiner/exams')) return VIEW.EXAMS;
    if (path.includes('/examiner/question-bank')) return VIEW.QUESTIONS;
    if (path.includes('/examiner/candidates')) return VIEW.CANDIDATES;
    if (path.includes('/examiner/monitoring') || path.includes('/examiner/live-monitoring')) return VIEW.MONITORING;
    if (path.includes('/examiner/activity-logs')) return VIEW.LOGS;
    if (path.includes('/examiner/results')) return VIEW.RESULTS;
    if (path.includes('/examiner/reports')) return VIEW.REPORTS;
    if (path.includes('/examiner/rankings')) return VIEW.RANKINGS;
    if (path.includes('/examiner/notifications')) return VIEW.NOTIFICATIONS;
    if (path.includes('/examiner/profile')) return VIEW.PROFILE;
    return initialView || VIEW.DASHBOARD;
  };

  const [currentView, setCurrentView] = useState(getViewFromPath);
  const [selectedExam, setSelectedExam] = useState(null);
  const [showExamModal, setShowExamModal] = useState(
    location.pathname.includes('/examiner/exams/create')
  );
  const [editingExam, setEditingExam] = useState(null);

  useEffect(() => {
    setCurrentView(getViewFromPath());
    if (location.pathname.includes('/examiner/exams/create')) {
      setEditingExam(null);
      setShowExamModal(true);
    }
  }, [location.pathname]);

  // Initial load
  useEffect(() => {
    fetchStats();
    fetchExams();
  }, [fetchStats, fetchExams]);

  // Auto-dismiss success messages
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => clearMessages(), 4000);
      return () => clearTimeout(timer);
    }
  }, [successMessage, clearMessages]);

  const handleCreateExam = () => {
    setEditingExam(null);
    setShowExamModal(true);
  };

  const handleViewExam = (exam) => {
    setEditingExam(exam);
    setShowExamModal(true);
  };

  const handleManageQuestions = (exam) => {
    setSelectedExam(exam);
    setCurrentView(VIEW.QUESTIONS);
  };

  const handleViewResults = (exam) => {
    setSelectedExam(exam);
    setCurrentView(VIEW.RESULTS);
  };

  const handleBackToDashboard = () => {
    setCurrentView(VIEW.DASHBOARD);
    setSelectedExam(null);
    fetchExams();
    fetchStats();
  };

  const handleCloseExamModal = () => {
    setShowExamModal(false);
    setEditingExam(null);
    fetchExams();
    fetchStats();
  };

  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'Examiner';

  return (
    <div className="container-fluid px-0" id="examiner-workspace-root">
      {/* ── Page Header ───────────────────────────────────────────────────── */}
      <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-warning text-dark text-uppercase tracking-wider fw-bold">
              Examiner Portal
            </span>
            <span className="badge bg-light text-muted border">
              {currentView.toUpperCase()}
            </span>
          </div>
          <h2 className="fw-bold mb-1 text-dark">
            {currentView === VIEW.DASHBOARD && `Welcome back, ${firstName}! 👋`}
            {currentView === VIEW.EXAMS && 'Examinations Workspace'}
            {currentView === VIEW.QUESTIONS && 'Question Bank Management'}
            {currentView === VIEW.CANDIDATES && 'Candidate Management & Assignments'}
            {currentView === VIEW.MONITORING && 'Live Examination Monitoring'}
            {currentView === VIEW.LOGS && 'Examination Activity Logs'}
            {currentView === VIEW.RESULTS && 'Results & Performance Evaluation'}
            {currentView === VIEW.REPORTS && 'Candidate Performance Reports'}
            {currentView === VIEW.RANKINGS && 'Rankings & Leaderboard'}
            {currentView === VIEW.NOTIFICATIONS && 'Announcements & Notifications'}
            {currentView === VIEW.PROFILE && 'Examiner Profile & Security'}
          </h2>
          <p className="text-muted mb-0 small">
            {currentView === VIEW.DASHBOARD && 'Overview of active assessments, upcoming schedules, and candidate progress.'}
            {currentView === VIEW.EXAMS && 'Create, duplicate, schedule, configure, and manage test life-cycles.'}
            {currentView === VIEW.QUESTIONS && (selectedExam ? `Managing questions for: ${selectedExam.title}` : 'Question bank repository with Aptitude, Reasoning, Technical, and Coding problems.')}
            {currentView === VIEW.CANDIDATES && 'Manage candidate directory, batch assignments, and exam progress states.'}
            {currentView === VIEW.MONITORING && 'Real-time proctoring feed tracking candidate status, time left, and tab switches.'}
            {currentView === VIEW.LOGS && 'Audit log trail tracking candidate logins, code submissions, answer saves, and alerts.'}
            {currentView === VIEW.RESULTS && (selectedExam ? `Submissions for: ${selectedExam.title}` : 'Review candidate scores, pass/fail grading, and publish scorecards.')}
            {currentView === VIEW.REPORTS && 'Deep dive into cohort accuracy, topic performance, and question difficulty.'}
            {currentView === VIEW.RANKINGS && 'Merit rankings, percentiles, and completion speed leaderboard.'}
            {currentView === VIEW.NOTIFICATIONS && 'Transmit announcements, reminders, and exam briefings to candidates.'}
            {currentView === VIEW.PROFILE && 'Manage faculty information, department credentials, and security password.'}
          </p>
        </div>

        {/* Action Buttons & View Navigation Pills */}
        <div className="d-flex align-items-center gap-2 flex-wrap">
          {currentView !== VIEW.LOGS && currentView !== VIEW.MONITORING && currentView !== VIEW.RESULTS && currentView !== VIEW.NOTIFICATIONS && currentView !== VIEW.PROFILE && (
            <button
              type="button"
              className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1.5 rounded-3"
              onClick={() => { fetchStats(); fetchExams(); }}
              title="Refresh workspace data"
            >
              <i className="bi bi-arrow-clockwise" />
              <span>Refresh</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Global Alerts ─────────────────────────────────────────────────── */}
      {successMessage && (
        <div className="alert alert-success alert-dismissible fade show shadow-sm border-0 rounded-3 mb-4" role="alert">
          <i className="bi bi-check-circle-fill me-2 fs-5" />
          <span>{successMessage}</span>
          <button type="button" className="btn-close" onClick={clearMessages} />
        </div>
      )}

      {actionError && (
        <div className="alert alert-danger alert-dismissible fade show shadow-sm border-0 rounded-3 mb-4" role="alert">
          <i className="bi bi-exclamation-triangle-fill me-2 fs-5" />
          <span>{actionError}</span>
          <button type="button" className="btn-close" onClick={clearMessages} />
        </div>
      )}

      {/* ── 1. DASHBOARD OVERVIEW VIEW ────────────────────────────────────── */}
      {currentView === VIEW.DASHBOARD && (
        <>
          {/* Summary Cards */}
          <ExaminerStatsCards
            stats={stats}
            loading={loadingStats}
            error={statsError}
          />

          {/* Quick Action Cards */}
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <div
                className="card border-0 shadow-sm rounded-4 p-3.5 text-center h-100 text-white"
                style={{
                  background: 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
                onClick={handleCreateExam}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-3px)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = '')}
              >
                <i className="bi bi-journal-plus fs-2 mb-2 d-block" />
                <h6 className="fw-bold mb-1">Create Exam</h6>
                <p className="text-white-50 small mb-0">Configure new test</p>
              </div>
            </div>

            <div className="col-6 col-md-3">
              <div
                className="card border-0 shadow-sm rounded-4 p-3.5 text-center h-100 text-white"
                style={{
                  background: 'linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
                onClick={() => setCurrentView(VIEW.QUESTIONS)}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-3px)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = '')}
              >
                <i className="bi bi-collection-play fs-2 mb-2 d-block" />
                <h6 className="fw-bold mb-1">Question Bank</h6>
                <p className="text-white-50 small mb-0">MCQ & Coding problems</p>
              </div>
            </div>

            <div className="col-6 col-md-3">
              <div
                className="card border-0 shadow-sm rounded-4 p-3.5 text-center h-100 text-white"
                style={{
                  background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
                onClick={() => {
                  setCurrentView(VIEW.MONITORING);
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-3px)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = '')}
              >
                <i className="bi bi-broadcast fs-2 mb-2 d-block" />
                <h6 className="fw-bold mb-1">Live Monitoring</h6>
                <p className="text-white-50 small mb-0">Real-time proctoring</p>
              </div>
            </div>

            <div className="col-6 col-md-3">
              <div
                className="card border-0 shadow-sm rounded-4 p-3.5 text-center h-100 text-white"
                style={{
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
                onClick={() => {
                  setCurrentView(VIEW.RESULTS);
                }}
                onMouseEnter={(e) => (e.currentTarget.style.transform = 'translateY(-3px)')}
                onMouseLeave={(e) => (e.currentTarget.style.transform = '')}
              >
                <i className="bi bi-award fs-2 mb-2 d-block" />
                <h6 className="fw-bold mb-1">Results & Grading</h6>
                <p className="text-white-50 small mb-0">Scorecards & percentiles</p>
              </div>
            </div>
          </div>

          {/* Schedule & Candidate Activity Grid */}
          <div className="row g-4 mb-4">
            {/* Upcoming Examination Schedule */}
            <div className="col-lg-6">
              <div className="card border-0 shadow-sm rounded-4 p-4 h-100">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h5 className="fw-bold mb-0 text-dark d-flex align-items-center gap-2">
                    <i className="bi bi-calendar-check text-primary" />
                    <span>Upcoming Exam Schedule</span>
                  </h5>
                  <button
                    className="btn btn-sm btn-link text-decoration-none p-0"
                    onClick={() => setCurrentView(VIEW.EXAMS)}
                  >
                    View All
                  </button>
                </div>

                <div className="d-flex flex-column gap-2.5">
                  {(stats?.upcoming_schedule || [
                    { id: 1, title: 'Full Stack Aptitude & Coding Assessment', date: 'Tomorrow', time: '10:00 AM - 12:00 PM', duration: '120 mins', status: 'Scheduled' },
                    { id: 2, title: 'Core Technical Computer Science Exam', date: 'In 3 Days', time: '02:00 PM - 03:30 PM', duration: '90 mins', status: 'Scheduled' },
                    { id: 3, title: 'Verbal & Abstract Reasoning Test', date: 'Next Monday', time: '11:00 AM - 11:45 AM', duration: '45 mins', status: 'Drafted' },
                  ]).map((sch) => (
                    <div key={sch.id} className="p-3 border rounded-3 bg-light d-flex justify-content-between align-items-center">
                      <div>
                        <div className="fw-semibold text-dark small mb-0.5">{sch.title}</div>
                        <div className="text-muted" style={{ fontSize: '0.78rem' }}>
                          <i className="bi bi-clock me-1 text-primary" />
                          {sch.date} • {sch.time} ({sch.duration})
                        </div>
                      </div>
                      <span className="badge bg-primary-subtle text-primary rounded-pill px-2.5 py-1">
                        {sch.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Recent Candidate Activity Stream */}
            <div className="col-lg-6">
              <div className="card border-0 shadow-sm rounded-4 p-4 h-100">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h5 className="fw-bold mb-0 text-dark d-flex align-items-center gap-2">
                    <i className="bi bi-activity text-danger" />
                    <span>Recent Candidate Activity</span>
                  </h5>
                  <button
                    className="btn btn-sm btn-link text-decoration-none p-0"
                    onClick={() => setCurrentView(VIEW.LOGS)}
                  >
                    Full Log Trail
                  </button>
                </div>

                <div className="d-flex flex-column gap-2.5">
                  {(stats?.recent_activity || [
                    { id: 1, student_name: 'Aarav Sharma', action: 'Submitted', exam_title: 'Full Stack Aptitude & Coding', score: '88%', time: '10 mins ago', type: 'success' },
                    { id: 2, student_name: 'Priya Patel', action: 'In Progress', exam_title: 'Core Technical CS Exam', score: 'Progress 75%', time: '25 mins ago', type: 'primary' },
                    { id: 3, student_name: 'Rohan Deshmukh', action: 'Tab Switch Alert', exam_title: 'Aptitude Assessment', score: 'Flagged', time: '32 mins ago', type: 'warning' },
                    { id: 4, student_name: 'Ananya Gupta', action: 'Completed', exam_title: 'Algorithmic Coding Challenge', score: '95%', time: '1 hour ago', type: 'success' },
                  ]).map((act) => (
                    <div key={act.id} className="p-3 border rounded-3 bg-light d-flex justify-content-between align-items-center">
                      <div className="d-flex align-items-center gap-2.5">
                        <div
                          className={`rounded-circle bg-${act.type} bg-opacity-10 text-${act.type} fw-bold d-flex align-items-center justify-content-center`}
                          style={{ width: 34, height: 34, fontSize: '0.8rem' }}
                        >
                          {act.student_name?.charAt(0) || 'C'}
                        </div>
                        <div>
                          <div className="fw-semibold text-dark small">{act.student_name}</div>
                          <div className="text-muted" style={{ fontSize: '0.75rem' }}>{act.exam_title}</div>
                        </div>
                      </div>

                      <div className="text-end">
                        <span className={`badge bg-${act.type}-subtle text-${act.type} rounded-pill px-2.5 py-0.5 small`}>
                          {act.action} ({act.score})
                        </span>
                        <div className="text-muted small mt-0.5" style={{ fontSize: '0.72rem' }}>{act.time}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Examinations List */}
          <ExamListTable
            onCreateNew={handleCreateExam}
            onViewExam={handleViewExam}
            onManageQuestions={handleManageQuestions}
            onViewResults={handleViewResults}
          />
        </>
      )}

      {/* ── 2. EXAMINATIONS VIEW ──────────────────────────────────────────── */}
      {currentView === VIEW.EXAMS && (
        <ExamListTable
          onCreateNew={handleCreateExam}
          onViewExam={handleViewExam}
          onManageQuestions={handleManageQuestions}
          onViewResults={handleViewResults}
        />
      )}

      {/* ── 3. QUESTIONS / QUESTION BANK VIEW ─────────────────────────────── */}
      {currentView === VIEW.QUESTIONS && (
        selectedExam ? (
          <QuestionBankPanel
            exam={selectedExam}
            onBack={handleBackToDashboard}
          />
        ) : (
          <QuestionBankPanel
            onBack={handleBackToDashboard}
          />
        )
      )}

      {/* ── 4. CANDIDATES MANAGEMENT VIEW ─────────────────────────────────── */}
      {currentView === VIEW.CANDIDATES && (
        <CandidateManagementPanel />
      )}

      {/* ── 5. LIVE MONITORING VIEW ───────────────────────────────────────── */}
      {currentView === VIEW.MONITORING && (
        <LiveMonitoringPanel />
      )}

      {/* ── 6. ACTIVITY LOGS VIEW ─────────────────────────────────────────── */}
      {currentView === VIEW.LOGS && (
        <ExaminerActivityLogsPanel />
      )}

      {/* ── 7. RESULTS MANAGEMENT VIEW ────────────────────────────────────── */}
      {currentView === VIEW.RESULTS && (
        selectedExam ? (
          <SubmissionsTable
            exam={selectedExam}
            onBack={handleBackToDashboard}
          />
        ) : (
          <ExaminerResultsPanel />
        )
      )}

      {/* ── 8. PERFORMANCE REPORTS VIEW ───────────────────────────────────── */}
      {currentView === VIEW.REPORTS && (
        <PerformanceReportsPanel />
      )}

      {/* ── 9. RANKINGS VIEW ──────────────────────────────────────────────── */}
      {currentView === VIEW.RANKINGS && (
        <ExaminerRankingsPanel />
      )}

      {/* ── 10. NOTIFICATIONS VIEW ────────────────────────────────────────── */}
      {currentView === VIEW.NOTIFICATIONS && (
        <ExaminerNotificationsPanel />
      )}

      {/* ── 11. PROFILE VIEW ──────────────────────────────────────────────── */}
      {currentView === VIEW.PROFILE && (
        <ExaminerProfilePanel />
      )}

      {/* ── Exam Create/Edit Modal ─────────────────────────────────────────── */}
      {showExamModal && (
        <ExamFormModal
          exam={editingExam}
          onClose={handleCloseExamModal}
        />
      )}
    </div>
  );
};

// ─── Outer Wrapper ────────────────────────────────────────────────────────────
const ExaminerDashboardHome = ({ initialView }) => {
  return (
    <ExaminerProvider>
      <ExaminerDashboardContent initialView={initialView} />
    </ExaminerProvider>
  );
};

export default ExaminerDashboardHome;
