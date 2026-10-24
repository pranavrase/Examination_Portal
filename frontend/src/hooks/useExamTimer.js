import { useEffect, useRef } from 'react';
import { useExamAttempt } from '../context/ExamAttemptContext';
import useVisibilityChange from './useVisibilityChange';

/**
 * Custom hook to run the 1-second exam countdown, 30-second server resync, and visibility restoration
 */
export const useExamTimer = () => {
  const {
    remainingSeconds,
    setRemainingSeconds,
    isExpired,
    isSubmitted,
    resyncServerTime,
    checkWarnings,
  } = useExamAttempt();

  const timerIntervalRef = useRef(null);
  const syncIntervalRef = useRef(null);

  // 1. Initial Server Sync on Mount
  useEffect(() => {
    resyncServerTime();
  }, [resyncServerTime]);

  // 2. Client-Side 1-Second Countdown Timer
  useEffect(() => {
    if (isExpired || isSubmitted) {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      return;
    }

    timerIntervalRef.current = setInterval(() => {
      setRemainingSeconds((prev) => {
        const next = prev - 1;
        checkWarnings(next);
        return Math.max(0, next);
      });
    }, 1000);

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [isExpired, isSubmitted, setRemainingSeconds, checkWarnings]);

  // 3. Periodic 30-Second Server Resynchronization
  useEffect(() => {
    if (isExpired || isSubmitted) {
      if (syncIntervalRef.current) clearInterval(syncIntervalRef.current);
      return;
    }

    syncIntervalRef.current = setInterval(() => {
      resyncServerTime();
    }, 30000); // 30 seconds

    return () => {
      if (syncIntervalRef.current) clearInterval(syncIntervalRef.current);
    };
  }, [isExpired, isSubmitted, resyncServerTime]);

  // 4. Tab Visibility Change Resync
  useVisibilityChange(() => {
    if (!isExpired && !isSubmitted) {
      resyncServerTime();
    }
  });

  return { remainingSeconds };
};

export default useExamTimer;
