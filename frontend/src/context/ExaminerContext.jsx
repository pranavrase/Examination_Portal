import React, { createContext, useContext, useState, useCallback } from 'react';
import {
  getMyExams,
  getExamById,
  createExam,
  updateExam,
  deleteExam,
  publishExam,
  getQuestionsByExam,
  createQuestion,
  updateQuestion,
  deleteQuestion,
  getSubmissionsByExam,
  getExaminerStats,
} from '../api/examinerApi';

const ExaminerContext = createContext(null);

export const ExaminerProvider = ({ children }) => {
  // ─── Exams State ────────────────────────────────────────────────────────────
  const [exams, setExams] = useState([]);
  const [selectedExam, setSelectedExam] = useState(null);
  const [loadingExams, setLoadingExams] = useState(false);
  const [examsError, setExamsError] = useState(null);

  // ─── Questions State ─────────────────────────────────────────────────────────
  const [questions, setQuestions] = useState([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [questionsError, setQuestionsError] = useState(null);

  // ─── Submissions State ───────────────────────────────────────────────────────
  const [submissions, setSubmissions] = useState([]);
  const [loadingSubmissions, setLoadingSubmissions] = useState(false);
  const [submissionsError, setSubmissionsError] = useState(null);

  // ─── Stats State ─────────────────────────────────────────────────────────────
  const [stats, setStats] = useState(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsError, setStatsError] = useState(null);

  // ─── Action State ─────────────────────────────────────────────────────────────
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  const clearMessages = useCallback(() => {
    setActionError(null);
    setSuccessMessage(null);
  }, []);

  // ─── Fetch Examiner Stats ─────────────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    setLoadingStats(true);
    setStatsError(null);
    try {
      const data = await getExaminerStats();
      setStats(data);
    } catch (err) {
      setStatsError(err?.response?.data?.detail || 'Failed to load statistics');
      setStats(null);
    } finally {
      setLoadingStats(false);
    }
  }, []);

  // ─── Fetch All Exams ──────────────────────────────────────────────────────────
  const fetchExams = useCallback(async (search = '', status = '') => {
    setLoadingExams(true);
    setExamsError(null);
    try {
      const params = {};
      if (search) params.search = search;
      if (status) params.status = status;
      const data = await getMyExams(params);
      setExams(Array.isArray(data) ? data : data?.exams || data?.items || []);
    } catch (err) {
      setExamsError(err?.response?.data?.detail || 'Failed to load exams');
      setExams([]);
    } finally {
      setLoadingExams(false);
    }
  }, []);

  // ─── Fetch Single Exam ────────────────────────────────────────────────────────
  const fetchExamById = useCallback(async (examId) => {
    setLoadingExams(true);
    setExamsError(null);
    try {
      const data = await getExamById(examId);
      setSelectedExam(data);
      return data;
    } catch (err) {
      setExamsError(err?.response?.data?.detail || 'Failed to load exam details');
      return null;
    } finally {
      setLoadingExams(false);
    }
  }, []);

  // ─── Create Exam ──────────────────────────────────────────────────────────────
  const addExam = useCallback(async (examData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const newExam = await createExam(examData);
      setExams((prev) => [newExam, ...prev]);
      setSuccessMessage(`Exam "${newExam.title}" created successfully!`);
      return newExam;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to create exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, []);

  // ─── Update Exam ──────────────────────────────────────────────────────────────
  const editExam = useCallback(async (examId, examData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await updateExam(examId, examData);
      setExams((prev) => prev.map((e) => (e.id === examId ? updated : e)));
      if (selectedExam?.id === examId) setSelectedExam(updated);
      setSuccessMessage('Exam updated successfully!');
      return updated;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, [selectedExam]);

  // ─── Delete Exam ──────────────────────────────────────────────────────────────
  const removeExam = useCallback(async (examId) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await deleteExam(examId);
      setExams((prev) => prev.filter((e) => e.id !== examId));
      setSuccessMessage('Exam deleted successfully!');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to delete exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, []);

  // ─── Publish Exam ─────────────────────────────────────────────────────────────
  const togglePublishExam = useCallback(async (examId) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await publishExam(examId);
      setExams((prev) => prev.map((e) => (e.id === examId ? updated : e)));
      setSuccessMessage(updated.is_published ? 'Exam published!' : 'Exam unpublished!');
      return updated;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update exam status';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, []);

  // ─── Fetch Questions ──────────────────────────────────────────────────────────
  const fetchQuestions = useCallback(async (examId, params = {}) => {
    setLoadingQuestions(true);
    setQuestionsError(null);
    try {
      const data = await getQuestionsByExam(examId, params);
      setQuestions(Array.isArray(data) ? data : data?.questions || []);
    } catch (err) {
      setQuestionsError(err?.response?.data?.detail || 'Failed to load questions');
      setQuestions([]);
    } finally {
      setLoadingQuestions(false);
    }
  }, []);

  // ─── Add Question ─────────────────────────────────────────────────────────────
  const addQuestion = useCallback(async (examId, questionData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const newQ = await createQuestion(examId, questionData);
      setQuestions((prev) => [...prev, newQ]);
      setSuccessMessage('Question added successfully!');
      return newQ;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to add question';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, []);

  // ─── Edit Question ────────────────────────────────────────────────────────────
  const editQuestion = useCallback(async (examId, questionId, questionData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await updateQuestion(examId, questionId, questionData);
      setQuestions((prev) => prev.map((q) => (q.id === questionId ? updated : q)));
      setSuccessMessage('Question updated successfully!');
      return updated;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update question';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, []);

  // ─── Delete Question ──────────────────────────────────────────────────────────
  const removeQuestion = useCallback(async (examId, questionId) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await deleteQuestion(examId, questionId);
      setQuestions((prev) => prev.filter((q) => q.id !== questionId));
      setSuccessMessage('Question deleted successfully!');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to delete question';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  }, []);

  // ─── Fetch Submissions ────────────────────────────────────────────────────────
  const fetchSubmissions = useCallback(async (examId, params = {}) => {
    setLoadingSubmissions(true);
    setSubmissionsError(null);
    try {
      const data = await getSubmissionsByExam(examId, params);
      setSubmissions(Array.isArray(data) ? data : data?.submissions || []);
    } catch (err) {
      setSubmissionsError(err?.response?.data?.detail || 'Failed to load submissions');
      setSubmissions([]);
    } finally {
      setLoadingSubmissions(false);
    }
  }, []);

  const value = {
    // State
    exams, selectedExam, setSelectedExam,
    loadingExams, examsError,
    questions, loadingQuestions, questionsError,
    submissions, loadingSubmissions, submissionsError,
    stats, loadingStats, statsError,
    actionLoading, actionError, successMessage,
    // Actions
    clearMessages,
    fetchStats,
    fetchExams,
    fetchExamById,
    addExam,
    editExam,
    removeExam,
    togglePublishExam,
    fetchQuestions,
    addQuestion,
    editQuestion,
    removeQuestion,
    fetchSubmissions,
  };

  return <ExaminerContext.Provider value={value}>{children}</ExaminerContext.Provider>;
};

export const useExaminer = () => {
  const ctx = useContext(ExaminerContext);
  if (!ctx) throw new Error('useExaminer must be used within ExaminerProvider');
  return ctx;
};

export default ExaminerContext;
