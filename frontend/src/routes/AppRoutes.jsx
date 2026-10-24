import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AuthLayout from '../layouts/AuthLayout';
import AppLayout from '../layouts/AppLayout';
import LoginPage from '../pages/auth/LoginPage';
import RegisterPage from '../pages/auth/RegisterPage';
import ForgotPasswordPage from '../pages/auth/ForgotPasswordPage';
import ResetPasswordPage from '../pages/auth/ResetPasswordPage';
import ProtectedRoute from '../components/common/ProtectedRoute';
import RoleBasedRedirect from '../components/common/RoleBasedRedirect';
import AdminDashboardHome from '../pages/admin/AdminDashboardHome';
import ExaminerDashboardHome, { VIEW } from '../pages/examiner/ExaminerDashboardHome';
import StudentDashboardHome from '../pages/student/StudentDashboardHome';
import StudentExamLobbyPage from '../pages/student/StudentExamLobbyPage';
import MyExamsPage from '../pages/student/MyExamsPage';
import MyResultsPage from '../pages/student/MyResultsPage';
import StudentPerformancePage from '../pages/student/StudentPerformancePage';
import StudentLeaderboardPage from '../pages/student/StudentLeaderboardPage';
import StudentProfilePage from '../pages/student/StudentProfilePage';
import NotificationsPage from '../pages/student/NotificationsPage';
import LiveExamSessionPage from '../pages/exam/LiveExamSessionPage';
import { StudentProvider } from '../context/StudentContext';
import ExamListPage from '../pages/exam/ExamListPage';
import ExamEditPage from '../pages/exam/ExamEditPage';
import QuestionBankPage from '../pages/examiner/QuestionBankPage';
import CodingExamPage from '../pages/exam/CodingExamPage';
import { ExamProvider } from '../context/ExamContext';
import ResultScorecardPage from '../pages/results/ResultScorecardPage';
import RankingLeaderboardPage from '../pages/results/RankingLeaderboardPage';
import TopicWiseReportPage from '../pages/reports/TopicWiseReportPage';
import CandidateWiseReportPage from '../pages/reports/CandidateWiseReportPage';
import ActivityMonitoringPage from '../pages/admin/ActivityMonitoringPage';

import NotFoundPage from '../pages/NotFoundPage';

const AppRoutes = () => {
  return (
    <Routes>
      {/* Root Path - Automatically redirects authenticated users to their respective dashboard or unauthenticated to login */}
      <Route path="/" element={<RoleBasedRedirect />} />

      {/* Public Authentication Routes */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* ── 1. ADMIN EXCLUSIVE ROUTES ────────────────────────────────────── */}
      <Route
        path="/admin/*"
        element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AppLayout>
              <AdminDashboardHome />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* ── 2. EXAMINER & ADMIN WORKSPACE ROUTES ─────────────────────────── */}
      <Route
        path="/examiner"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.DASHBOARD} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/exams"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.EXAMS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/exams/create"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.EXAMS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/question-bank"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <QuestionBankPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/candidates"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.CANDIDATES} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/monitoring"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.MONITORING} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/live-monitoring"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.MONITORING} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/activity-logs"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.LOGS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/results"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.RESULTS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/reports"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.REPORTS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/rankings"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.RANKINGS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/notifications"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.NOTIFICATIONS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/examiner/profile"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.PROFILE} />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Legacy Exam Routes */}
      <Route
        path="/exams"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.EXAMS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/exams/create"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ExaminerDashboardHome initialView={VIEW.EXAMS} />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/exams/:id/edit"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <ExamProvider>
              <AppLayout>
                <ExamEditPage isCreate={false} />
              </AppLayout>
            </ExamProvider>
          </ProtectedRoute>
        }
      />

      {/* ── 3. STUDENT EXCLUSIVE CANDIDATE PORTAL ────────────────────────── */}
      <Route
        path="/student"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <StudentDashboardHome />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/exams"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <MyExamsPage />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/results"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <MyResultsPage />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/performance"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <StudentPerformancePage />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/leaderboard"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <StudentLeaderboardPage />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/profile"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <StudentProfilePage />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/notifications"
        element={
          <ProtectedRoute allowedRoles={['student']}>
            <StudentProvider>
              <AppLayout>
                <NotificationsPage />
              </AppLayout>
            </StudentProvider>
          </ProtectedRoute>
        }
      />

      {/* ── 4. EXAM SESSION & SCORING (Student, Examiner & Admin) ─────────── */}
      <Route
        path="/student/exam/:examId"
        element={
          <ProtectedRoute allowedRoles={['student', 'examiner', 'admin']}>
            <AppLayout>
              <StudentExamLobbyPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/exam/:examId/live"
        element={
          <ProtectedRoute allowedRoles={['student', 'examiner', 'admin']}>
            <LiveExamSessionPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/student/exam/:examId/coding"
        element={
          <ProtectedRoute allowedRoles={['student', 'examiner', 'admin']}>
            <LiveExamSessionPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/coding-exam/:examId"
        element={
          <ProtectedRoute allowedRoles={['student', 'examiner', 'admin']}>
            <LiveExamSessionPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/results/:attemptId"
        element={
          <ProtectedRoute allowedRoles={['student', 'examiner', 'admin']}>
            <AppLayout>
              <ResultScorecardPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/exams/:examId/rankings"
        element={
          <ProtectedRoute allowedRoles={['student', 'examiner', 'admin']}>
            <AppLayout>
              <RankingLeaderboardPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/topic-wise"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <TopicWiseReportPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports/candidate-wise"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <CandidateWiseReportPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/activity-monitoring"
        element={
          <ProtectedRoute allowedRoles={['examiner', 'admin']}>
            <AppLayout>
              <ActivityMonitoringPage />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Catch-all 404 Route */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default AppRoutes;
