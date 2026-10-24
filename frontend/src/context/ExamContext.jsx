import React, { createContext, useContext, useState, useCallback } from 'react';
import * as api from '../api/examApi';

const ExamContext = createContext(null);

export const ExamProvider = ({ children }) => {
  const [exams, setExams] = useState([]);
  const [currentExam, setCurrentExam] = useState(null);
  
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  
  const [error, setError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const clearMessages = useCallback(() => {
    setActionError(null);
    setSuccessMsg(null);
  }, []);

  const fetchExams = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getExams(params);
      setExams(Array.isArray(data) ? data : data?.exams || data?.items || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load exams');
      setExams([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchExamById = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getExamById(id);
      setCurrentExam(data);
      return data;
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load exam details');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const createExam = async (examData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const newExam = await api.createExam(examData);
      setExams((prev) => [newExam, ...prev]);
      setSuccessMsg('Exam created successfully');
      return newExam;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to create exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const updateExam = async (id, examData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.updateExam(id, examData);
      setExams((prev) => prev.map((e) => (e.id === id ? updated : e)));
      if (currentExam?.id === id) {
        setCurrentExam(updated);
      }
      setSuccessMsg('Exam updated successfully');
      return updated;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const deleteExam = async (id) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await api.deleteExam(id);
      setExams((prev) => prev.filter((e) => e.id !== id));
      if (currentExam?.id === id) {
        setCurrentExam(null);
      }
      setSuccessMsg('Exam deleted successfully');
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to delete exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const publishExam = async (id) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await api.publishExam(id);
      setExams((prev) => prev.map((e) => (e.id === id ? updated : e)));
      if (currentExam?.id === id) {
        setCurrentExam(updated);
      }
      setSuccessMsg('Exam published successfully');
      return updated;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to publish exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const assignExam = async (id, assignmentData) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const result = await api.assignExam(id, assignmentData);
      setSuccessMsg('Exam assigned successfully');
      return result;
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to assign exam';
      setActionError(msg);
      throw new Error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const value = {
    exams,
    currentExam,
    loading,
    error,
    actionLoading,
    actionError,
    successMsg,
    setCurrentExam,
    clearMessages,
    fetchExams,
    fetchExamById,
    createExam,
    updateExam,
    deleteExam,
    publishExam,
    assignExam,
  };

  return <ExamContext.Provider value={value}>{children}</ExamContext.Provider>;
};

export const useExam = () => {
  const ctx = useContext(ExamContext);
  if (!ctx) throw new Error('useExam must be used within ExamProvider');
  return ctx;
};

export default ExamContext;
