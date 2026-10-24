import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { getRemainingTime, submitExamAttempt } from '../api/examAttemptApi';

const ExamAttemptContext = createContext(null);

export const ExamAttemptProvider = ({ children, attemptId: initialAttemptId, initialDurationMinutes }) => {
  const attemptId = initialAttemptId || 'attempt_101';
  const totalDurationSeconds = initialDurationMinutes * 60;

  const [remainingSeconds, setRemainingSeconds] = useState(totalDurationSeconds);
  const [isExpired, setIsExpired] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState(false);
  const [activeWarning, setActiveWarning] = useState(null); // '5min' | '1min' | null

  // Ref trackers to prevent duplicate warning popups and duplicate submissions
  const warned5Min = useRef(false);
  const warned1Min = useRef(false);
  const submittingRef = useRef(false);

  // Synchronize authoritative remaining time from server
  const resyncServerTime = useCallback(async () => {
    if (!attemptId || isExpired || isSubmitted || submittingRef.current) return;
    setIsSyncing(true);
    setSyncError(false);
    try {
      const data = await getRemainingTime(attemptId);
      const serverSecs = typeof data === 'number' ? data : data?.remaining_seconds ?? data?.remainingSeconds;

      if (typeof serverSecs === 'number') {
        setRemainingSeconds(serverSecs);

        if (serverSecs <= 0) {
          setIsExpired(true);
        }
      }
    } catch (err) {
      console.warn('Server remaining time sync error, falling back to local countdown:', err);
      setSyncError(true);
    } finally {
      setIsSyncing(false);
    }
  }, [attemptId, isExpired, isSubmitted]);

  // Trigger Automatic Submission on Time Expiration
  const autoSubmitExam = useCallback(async () => {
    if (submittingRef.current || isSubmitted) return;
    submittingRef.current = true;
    setIsSubmitting(true);
    setIsExpired(true);

    try {
      await submitExamAttempt(attemptId, { auto_submitted: true, reason: 'time_expired' });
      setIsSubmitted(true);
    } catch (err) {
      console.warn('Auto submit fallback handled:', err);
      setIsSubmitted(true);
    } finally {
      setIsSubmitting(false);
    }
  }, [attemptId, isSubmitted]);

  // Check Warning Thresholds
  const checkWarnings = useCallback((secs) => {
    if (secs <= 0) {
      setIsExpired(true);
      autoSubmitExam();
      return;
    }

    if (secs <= 60 && !warned1Min.current) {
      warned1Min.current = true;
      setActiveWarning('1min');
    } else if (secs <= 300 && secs > 60 && !warned5Min.current) {
      warned5Min.current = true;
      setActiveWarning('5min');
    }
  }, [autoSubmitExam]);

  const dismissWarning = useCallback(() => {
    setActiveWarning(null);
  }, []);

  // Helper formatter
  const formatTime = (secs) => {
    if (secs === null || secs === undefined || isNaN(secs)) {
      return { hours: 0, minutes: 0, seconds: 0, formatted: '--:--' };
    }
    const s = Math.max(0, secs);
    const hours = Math.floor(s / 3600);
    const minutes = Math.floor((s % 3600) / 60);
    const seconds = s % 60;

    const pad = (n) => String(n).padStart(2, '0');
    const formatted = hours > 0
      ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
      : `${pad(minutes)}:${pad(seconds)}`;

    return { hours, minutes, seconds, formatted };
  };

  const value = {
    attemptId,
    totalDurationSeconds,
    remainingSeconds,
    setRemainingSeconds,
    isExpired,
    isSubmitting,
    isSubmitted,
    isSyncing,
    syncError,
    activeWarning,
    resyncServerTime,
    autoSubmitExam,
    checkWarnings,
    dismissWarning,
    formatTime,
  };

  return <ExamAttemptContext.Provider value={value}>{children}</ExamAttemptContext.Provider>;
};

export const useExamAttempt = () => {
  const ctx = useContext(ExamAttemptContext);
  if (!ctx) throw new Error('useExamAttempt must be used within ExamAttemptProvider');
  return ctx;
};

export default ExamAttemptContext;
