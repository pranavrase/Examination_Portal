import { useEffect, useRef, useCallback, useState } from 'react';
import { autoSaveAnswers } from '../api/examAttemptApi';

/**
 * useAutoSave – Periodically persists exam answers to the backend.
 *
 * Triggers:
 *  1. Every `intervalMs` (default 30 s) regardless of changes.
 *  2. After `debounceMs` (default 2 s) of inactivity once the payload is dirty.
 *
 * @param {string|number} attemptId      - Active exam attempt ID.
 * @param {Function}      getPayload     - () => { mcq_answers, coding_drafts }
 * @param {Object}        [options]
 * @param {number}        [options.intervalMs=30000]   Periodic save interval
 * @param {number}        [options.debounceMs=2000]    Debounce after dirty change
 * @param {boolean}       [options.enabled=true]       Pause saving when false
 *
 * @returns {{ status, lastSavedAt, errorMsg, saveNow }}
 */
const useAutoSave = (attemptId, getPayload, options = {}) => {
  const {
    intervalMs = 30_000,
    debounceMs = 2_000,
    enabled = true,
  } = options;

  // 'idle' | 'saving' | 'saved' | 'error'
  const [status, setStatus] = useState('idle');
  const [lastSavedAt, setLastSavedAt] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const debounceRef = useRef(null);
  const intervalRef = useRef(null);
  const isSavingRef = useRef(false);

  // Core save function – captures the current payload and sends it.
  const performSave = useCallback(async () => {
    if (!attemptId || !enabled || isSavingRef.current) return;

    const payload = typeof getPayload === 'function' ? getPayload() : {};
    const hasContent =
      Object.keys(payload?.mcq_answers || {}).length > 0 ||
      Object.keys(payload?.coding_drafts || {}).length > 0;

    // Skip empty saves
    if (!hasContent) return;

    isSavingRef.current = true;
    setStatus('saving');
    setErrorMsg(null);

    try {
      await autoSaveAnswers(attemptId, payload);
      setStatus('saved');
      setLastSavedAt(new Date());
    } catch (err) {
      console.warn('[AutoSave] Save failed:', err?.response?.data?.detail || err.message);
      setStatus('error');
      setErrorMsg(err?.response?.data?.detail || 'Auto-save failed. Retrying…');
    } finally {
      isSavingRef.current = false;
    }
  }, [attemptId, enabled, getPayload]);

  // Expose an imperative save trigger (e.g. for "Finish Exam" button)
  const saveNow = useCallback(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    return performSave();
  }, [performSave]);

  // Debounced dirty-change trigger – call this whenever answer state changes.
  const triggerDirtySave = useCallback(() => {
    if (!enabled) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      performSave();
    }, debounceMs);
  }, [enabled, debounceMs, performSave]);

  // Periodic interval save
  useEffect(() => {
    if (!enabled || !attemptId) return;

    intervalRef.current = setInterval(() => {
      performSave();
    }, intervalMs);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [enabled, attemptId, intervalMs, performSave]);

  // Clean up debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return {
    status,
    lastSavedAt,
    errorMsg,
    saveNow,
    triggerDirtySave,
  };
};

export default useAutoSave;
