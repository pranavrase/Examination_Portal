import { useState, useEffect, useCallback, useRef } from 'react';
import axiosInstance from '../api/axiosInstance';

/**
 * useProctoringSecurity Hook
 * Detects tab switching, window blurring, and full-screen exits.
 * Records proctoring violation events and triggers warnings or auto-submission.
 *
 * @param {Object} options
 * @param {string|number} options.attemptId - Current exam attempt ID
 * @param {number} [options.maxViolations=3] - Maximum allowed infractions before termination
 * @param {Function} [options.onTerminate] - Callback fired when violation limit is reached
 * @param {boolean} [options.enabled=true] - Whether proctoring detection is active
 */
export const useProctoringSecurity = ({
  attemptId,
  maxViolations = 3,
  onTerminate,
  enabled = true,
}) => {
  const [violationCount, setViolationCount] = useState(0);
  const [showWarningModal, setShowWarningModal] = useState(false);
  const [lastViolationType, setLastViolationType] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(
    Boolean(
      typeof document !== 'undefined' &&
        (document.fullscreenElement ||
          document.webkitFullscreenElement ||
          document.mozFullScreenElement ||
          document.msFullscreenElement)
    )
  );
  const violationCountRef = useRef(0);
  const hasInitializedRef = useRef(false);
  // Prevents additional violations from being processed after termination
  const terminatedRef = useRef(false);

  const checkFullscreen = useCallback(() => {
    return Boolean(
      typeof document !== 'undefined' &&
        (document.fullscreenElement ||
          document.webkitFullscreenElement ||
          document.mozFullScreenElement ||
          document.msFullscreenElement)
    );
  }, []);

  const enterFullscreen = useCallback(async () => {
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen();
      } else if (elem.webkitRequestFullscreen) {
        await elem.webkitRequestFullscreen();
      } else if (elem.mozRequestFullScreen) {
        await elem.mozRequestFullScreen();
      } else if (elem.msRequestFullscreen) {
        await elem.msRequestFullscreen();
      }
      setIsFullscreen(true);
    } catch (e) {
      console.warn('Fullscreen request blocked or dismissed by user:', e);
    }
  }, []);

  const logViolationEvent = useCallback(
    async (eventType, description) => {
      try {
        if (attemptId) {
          await axiosInstance.post(`/activity/log`, {
            attempt_id: attemptId,
            event_type: eventType,
            description: description || `Proctoring violation detected: ${eventType}`,
            metadata: {
              timestamp: new Date().toISOString(),
              violation_number: violationCountRef.current + 1,
              user_agent: navigator.userAgent,
            },
          });
        }
      } catch (err) {
        console.warn('Failed to log proctoring event to backend:', err);
      }
    },
    [attemptId]
  );

  const handleViolation = useCallback(
    (type) => {
      if (!enabled) return;
      // Stop processing violations if the exam has already been terminated
      if (terminatedRef.current) return;

      violationCountRef.current += 1;
      const newCount = violationCountRef.current;
      setViolationCount(newCount);
      setLastViolationType(type);
      setShowWarningModal(true);

      const readableType =
        type === 'fullscreen_exit'
          ? 'Candidate exited full-screen mode'
          : type === 'tab_switch'
          ? 'Candidate switched away from assessment tab'
          : 'Candidate switched window/app focus';

      logViolationEvent(type, `${readableType}. Violation ${newCount} of ${maxViolations}`);

      if (newCount >= maxViolations) {
        terminatedRef.current = true;
        if (onTerminate) {
          onTerminate(newCount);
        }
      }
    },
    [enabled, maxViolations, onTerminate, logViolationEvent]
  );

  useEffect(() => {
    if (!enabled) return;

    // Small delay on initial mount before checking fullscreen to allow smooth transition
    const initTimer = setTimeout(() => {
      hasInitializedRef.current = true;
      const isFull = checkFullscreen();
      setIsFullscreen(isFull);
      if (!isFull) {
        setShowWarningModal(true);
        setLastViolationType('fullscreen_required');
      }
    }, 800);

    const handleVisibilityChange = () => {
      if (document.hidden) {
        handleViolation('tab_switch');
      }
    };

    const handleWindowBlur = () => {
      handleViolation('window_blur');
    };

    const handleFullscreenChange = () => {
      const isFull = checkFullscreen();
      setIsFullscreen(isFull);
      if (!isFull && hasInitializedRef.current) {
        handleViolation('fullscreen_exit');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleWindowBlur);
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      clearTimeout(initTimer);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleWindowBlur);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, [enabled, handleViolation, checkFullscreen]);

  const dismissWarning = useCallback(() => {
    setShowWarningModal(false);
    if (!checkFullscreen()) {
      enterFullscreen();
    }
  }, [checkFullscreen, enterFullscreen]);

  return {
    violationCount,
    maxViolations,
    showWarningModal,
    lastViolationType,
    isFullscreen,
    enterFullscreen,
    dismissWarning,
  };
};

export default useProctoringSecurity;
