import React, { createContext, useContext, useState, useCallback } from 'react';
import { getStudentExams, getStudentResults, getStudentLeaderboard } from '../api/studentApi';
import { getNotifications as apiGetNotifications, markAllRead as apiMarkAllRead, getUnreadCount } from '../api/notificationsApi';
import { useAuth } from './AuthContext';

const StudentContext = createContext(null);

export const StudentProvider = ({ children }) => {
  const { user } = useAuth();
  
  const [exams, setExams] = useState([]);
  const [results, setResults] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [leaderboard, setLeaderboard] = useState(null);
  
  const [loadingExams, setLoadingExams] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);
  
  const [examsError, setExamsError] = useState(null);
  const [resultsError, setResultsError] = useState(null);
  const [leaderboardError, setLeaderboardError] = useState(null);

  // Derived state — "available" means active/published exams ready to start
  const upcomingExams = exams.filter(e => (e.status === 'upcoming' || e.status === 'assigned') && e.status !== 'completed' && !e.attempt_id);
  const activeExams = exams.filter(e => (e.status === 'active' || e.status === 'available') && e.status !== 'completed' && !e.attempt_id);

  // Resolve user id from various possible shapes: { id } or { user: { id } }
  const getUserId = () => {
    return user?.id || user?.user?.id || user?.sub || null;
  };

  const fetchExams = useCallback(async () => {
    const studentId = getUserId();
    if (!studentId) {
      // If no user ID available, still show demo exams rather than blank dashboard
      setExams([]);
      setExamsError(null);
      return;
    }
    setLoadingExams(true);
    setExamsError(null);
    try {
      const data = await getStudentExams(studentId);
      const list = Array.isArray(data) ? data : data?.exams || data?.items || [];
      setExams(list);
    } catch (err) {
      console.warn('fetchExams error:', err?.response?.status, err?.response?.data?.detail);
      // On 404/403/500, don't show error — just show empty state gracefully
      setExamsError(null);
      setExams([]);
    } finally {
      setLoadingExams(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, user?.user?.id]);

  const fetchResults = useCallback(async () => {
    const studentId = getUserId();
    if (!studentId) {
      setResults([]);
      setResultsError(null);
      return;
    }
    setLoadingResults(true);
    setResultsError(null);
    try {
      const data = await getStudentResults(studentId);
      const list = Array.isArray(data) ? data : data?.results || data?.items || [];
      setResults(list);
    } catch (err) {
      console.warn('fetchResults error:', err?.response?.status, err?.response?.data?.detail);
      setResultsError(null);
      setResults([]);
    } finally {
      setLoadingResults(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id, user?.user?.id]);

  const fetchLeaderboard = useCallback(async (examId = null) => {
    setLoadingLeaderboard(true);
    setLeaderboardError(null);
    try {
      const data = await getStudentLeaderboard(examId);
      setLeaderboard(data);
    } catch (err) {
      console.warn('fetchLeaderboard error:', err?.response?.status, err?.response?.data?.detail);
      setLeaderboardError('Failed to load leaderboard data');
      setLeaderboard(null);
    } finally {
      setLoadingLeaderboard(false);
    }
  }, []);

  const fetchNotifications = useCallback(async () => {
    setLoadingNotifications(true);
    try {
      const data = await apiGetNotifications({ page: 1, page_size: 50 });
      const list = Array.isArray(data) ? data : data?.items || [];
      // Filter to only show EXAM_PUBLISHED and RESULT_AVAILABLE notifications
      const relevantList = list.filter(n => 
        n.notification_type === 'EXAM_PUBLISHED' || 
        n.notification_type === 'RESULT_AVAILABLE'
      );
      setNotifications(relevantList);
      setUnreadCount(relevantList.filter(n => !n.is_read).length);
    } catch {
      setNotifications([]);
    } finally {
      setLoadingNotifications(false);
    }
  }, []);

  const markAllNotificationsRead = useCallback(async () => {
    try {
      await apiMarkAllRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // silently ignore
    }
  }, []);

  const value = {
    exams,
    upcomingExams,
    activeExams,
    results,
    notifications,
    unreadCount,
    leaderboard,
    loadingExams,
    loadingResults,
    loadingNotifications,
    loadingLeaderboard,
    examsError,
    resultsError,
    leaderboardError,
    fetchExams,
    fetchResults,
    fetchNotifications,
    fetchLeaderboard,
    markAllNotificationsRead,
  };

  return <StudentContext.Provider value={value}>{children}</StudentContext.Provider>;
};

export const useStudent = () => {
  const ctx = useContext(StudentContext);
  if (!ctx) throw new Error('useStudent must be used within StudentProvider');
  return ctx;
};

export default StudentContext;
