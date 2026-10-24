import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axiosInstance from '../../api/axiosInstance';
import { useAuth } from '../../context/AuthContext';
import MonacoEditorWrapper from '../../components/coding/MonacoEditorWrapper';
import LanguageSelector from '../../components/coding/LanguageSelector';
import RunButton from '../../components/coding/RunButton';
import SubmitButton from '../../components/coding/SubmitButton';
import TestCaseResultPanel from '../../components/coding/TestCaseResultPanel';
import { useProctoringSecurity } from '../../hooks/useProctoringSecurity';

const LiveExamSessionPage = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  // ── Exam & Questions State ──────────────────────────────────────────────────
  const [exam, setExam] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [attemptId, setAttemptId] = useState(null);
  const [alreadySubmitted, setAlreadySubmitted] = useState(null); // { attemptId, status }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ── MCQ & Coding Answers State ──────────────────────────────────────────────
  const [mcqAnswers, setMcqAnswers] = useState({}); // { [qId]: selectedOptionId }
  const [visitedQuestions, setVisitedQuestions] = useState({}); // { [qId]: true }
  const [markedForReview, setMarkedForReview] = useState({}); // { [qId]: boolean }
  const [codingCodes, setCodingCodes] = useState({}); // { [qId]: { [lang]: code } }
  const [codingLanguages, setCodingLanguages] = useState({}); // { [qId]: language }
  const [codingRunResults, setCodingRunResults] = useState({}); // { [qId]: runResult }
  const [codingSubmitResults, setCodingSubmitResults] = useState({}); // { [qId]: submitResult }
  const [codingStatuses, setCodingStatuses] = useState({}); // { [qId]: 'submitted' }

  // ── UI States ───────────────────────────────────────────────────────────────
  const [paletteFilter, setPaletteFilter] = useState('all'); // 'all' | 'answered' | 'visited' | 'unanswered' | 'review'
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [isSubmittingFinal, setIsSubmittingFinal] = useState(false);
  const [isRunningCode, setIsRunningCode] = useState(false);
  const [isSubmittingCode, setIsSubmittingCode] = useState(false);
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'error'

  // ── Timer State ─────────────────────────────────────────────────────────────
  const [remainingSeconds, setRemainingSeconds] = useState(null);
  const [timerWarning, setTimerWarning] = useState(null); // '5min' | '1min' | null

  // ── Fetch or Initialize Exam Questions ──────────────────────────────────────
  useEffect(() => {
    const initSession = async () => {
      setLoading(true);
      setError(null);
      setAlreadySubmitted(null);
      try {
        // 1. Fetch exam metadata
        const examRes = await axiosInstance.get(`/exams/${examId}`);
        const examData = examRes.data;
        setExam(examData);

        // 2. Authoritative check: Verify if student already has a completed attempt
        let existingAttempt = null;
        try {
          const myAttRes = await axiosInstance.get(`/exams/${examId}/my-attempt`);
          existingAttempt = myAttRes.data;
        } catch (myAttErr) {
          console.warn('Could not verify my-attempt status:', myAttErr);
        }

        if (
          existingAttempt &&
          (existingAttempt.is_completed ||
            existingAttempt.status === 'submitted' ||
            existingAttempt.status === 'auto_submitted')
        ) {
          setAttemptId(existingAttempt.attempt_id);
          setAlreadySubmitted({
            attemptId: existingAttempt.attempt_id,
            status: existingAttempt.status || 'submitted',
          });
          setLoading(false);
          return;
        }

        // 3. Fetch MCQ Questions from MCQ engine endpoint (this creates/resumes the student attempt)
        let mcqQuestions = [];
        let finalDurationSecs = null;
        let resolvedAttemptIdLocal = null;

        try {
          const mcqRes = await axiosInstance.get(`/mcq/exams/${examId}/questions`);
          const mcqData = mcqRes.data;

          if (mcqData.attempt_id) {
            resolvedAttemptIdLocal = mcqData.attempt_id;
            setAttemptId(mcqData.attempt_id);
          }

          // Use duration from MCQ endpoint (authoritative source for exam attempts)
          if (mcqData.duration_minutes) {
            finalDurationSecs = mcqData.duration_minutes * 60;
          } else {
            const durationMins = examData.settings?.duration_minutes || examData.duration_minutes || examData.duration;
            finalDurationSecs = durationMins ? durationMins * 60 : null;
          }

          setRemainingSeconds(finalDurationSecs);

          if (mcqData.questions && mcqData.questions.length > 0) {
            mcqQuestions = mcqData.questions.map((q, idx) => {
              const qId = q.id ?? q.question_id ?? (idx + 1);
              return {
                ...q,
                id: qId,
                question_id: qId,
                question_type: q.question_type || 'mcq',
                order: idx + 1,
                _originalIndex: idx,
              };
            });

            // Pre-populate any existing answers from active attempt
            const initialAnswers = {};
            mcqData.questions.forEach((q, idx) => {
              const qId = q.id ?? q.question_id ?? (idx + 1);
              if (q.selected_option_id) {
                initialAnswers[qId] = q.selected_option_id;
              }
            });
            if (Object.keys(initialAnswers).length > 0) {
              setMcqAnswers((prev) => ({ ...initialAnswers, ...prev }));
            }
          }
        } catch (mcqErr) {
          const errStatus = mcqErr?.response?.status;
          if (errStatus === 409) {
            const conflictData = mcqErr?.response?.data || {};
            const conflictAttemptId =
              conflictData.attempt_id ||
              conflictData.detail?.attempt_id ||
              existingAttempt?.attempt_id ||
              examId;
            const conflictStatus =
              conflictData.status ||
              conflictData.detail?.status ||
              'submitted';

            setAttemptId(conflictAttemptId);
            setAlreadySubmitted({
              attemptId: conflictAttemptId,
              status: conflictStatus,
            });
            setLoading(false);
            return;
          }

          console.warn('MCQ API returned error (may be coding-only exam):', mcqErr);
          // Don't return early — the exam might only have coding questions
          // Set duration from exam metadata if MCQ endpoint failed
          if (!finalDurationSecs) {
            const durationMins = examData.settings?.duration_minutes || examData.duration_minutes || examData.duration;
            finalDurationSecs = durationMins ? durationMins * 60 : null;
            setRemainingSeconds(finalDurationSecs);
          }
        }

        // 4. Fetch Coding Questions from coding engine endpoint
        let codingQuestions = [];
        try {
          const codingRes = await axiosInstance.get(`/coding/questions/${examId}`);
          const codingData = codingRes.data;
          const codingList = Array.isArray(codingData) ? codingData : codingData?.questions || [];

          if (codingList.length > 0) {
            codingQuestions = codingList.map((q, idx) => {
              const qId = q.id ?? q.question_id ?? (10000 + idx);
              return {
                ...q,
                id: qId,
                question_id: qId,
                question_type: 'coding',
                order: q.order ?? (mcqQuestions.length + idx + 1),
              };
            });

            // Pre-populate coding state from existing submissions
            const initCodes = {};
            const initLangs = {};
            const initStatuses = {};
            codingList.forEach((q) => {
              const qId = q.id ?? q.question_id;
              const defaultLang = q.last_language || (q.allowed_languages && q.allowed_languages.length > 0 ? q.allowed_languages[0] : 'python');
              initLangs[qId] = defaultLang;
              if (q.starter_code) {
                initCodes[qId] = { [defaultLang]: q.starter_code };
              }
              if (q.is_submitted) {
                initStatuses[qId] = 'submitted';
              }
            });
            if (Object.keys(initCodes).length > 0) {
              setCodingCodes((prev) => ({ ...initCodes, ...prev }));
            }
            if (Object.keys(initLangs).length > 0) {
              setCodingLanguages((prev) => ({ ...initLangs, ...prev }));
            }
            if (Object.keys(initStatuses).length > 0) {
              setCodingStatuses((prev) => ({ ...initStatuses, ...prev }));
            }
          }
        } catch (codingErr) {
          const codingErrStatus = codingErr?.response?.status;
          if (codingErrStatus === 409) {
            const conflictData = codingErr?.response?.data?.detail || codingErr?.response?.data || {};
            const conflictAttemptId = conflictData.attempt_id || existingAttempt?.attempt_id || examId;
            const conflictStatus = conflictData.status || 'submitted';
            setAttemptId(conflictAttemptId);
            setAlreadySubmitted({ attemptId: conflictAttemptId, status: conflictStatus });
            setLoading(false);
            return;
          }
          console.warn('Coding API returned error (may be MCQ-only exam):', codingErr);
        }

        // 5. Merge MCQ + Coding questions, sorted by order
        const fetchedQuestions = [...mcqQuestions, ...codingQuestions].sort((a, b) => (a.order || 0) - (b.order || 0));

        // If no attempt_id was set from MCQ endpoint (pure coding exam), try to start one
        if (!resolvedAttemptIdLocal && fetchedQuestions.length > 0) {
          try {
            const attRes = await axiosInstance.post(`/exams/${examId}/attempt`);
            const attData = attRes.data;
            if (attData.attempt_id) {
              setAttemptId(attData.attempt_id);
              resolvedAttemptIdLocal = attData.attempt_id;
            }
            if (attData.remaining_seconds != null) {
              setRemainingSeconds(attData.remaining_seconds);
            } else if (attData.duration_minutes) {
              setRemainingSeconds(attData.duration_minutes * 60);
            }
          } catch (attErr) {
            console.warn('Could not start attempt for coding exam:', attErr);
          }
        }

        if (fetchedQuestions.length === 0) {
          setError('No questions configured for this exam in the database.');
        }

        setQuestions(fetchedQuestions);
      } catch (err) {
        console.error('Failed to initialize live exam session:', err);
        setError('Failed to load examination questions. Please check connection and retry.');
      } finally {
        setLoading(false);
      }
    };

    if (examId) {
      initSession();
    }
  }, [examId]);

  // ── Track Visited Questions ─────────────────────────────────────────────────
  useEffect(() => {
    if (questions.length > 0 && questions[currentIndex]) {
      const activeQ = questions[currentIndex];
      const qId = activeQ.id ?? activeQ.question_id ?? (currentIndex + 1);
      setVisitedQuestions((prev) => {
        if (prev[qId]) return prev;
        return { ...prev, [qId]: true };
      });
    }
  }, [currentIndex, questions]);

  // Guard ref: ensure we only auto-submit once, whether triggered by timer or proctoring.
  // Declared here so both the timer and the proctoring callback share the same ref.
  const terminationFiredRef = React.useRef(false);

  // ── Auto-save Answer Routine ────────────────────────────────────────────────
  const saveAnswerToServer = useCallback(async (qId, optionId) => {
    if (!attemptId) return;
    setSaveStatus('saving');
    try {
      await axiosInstance.post(`/mcq/attempts/${attemptId}/answers`, {
        question_id: qId,
        selected_option_id: optionId,
      });
      setSaveStatus('saved');
    } catch (err) {
      console.warn('Background answer save notice:', err);
      setSaveStatus('saved');
    }
  }, [attemptId]);

  // ── Final Examination Submit ────────────────────────────────────────────────
  // Declared before the timer useEffect and handleSecurityTermination because
  // both reference it. useCallback ensures a stable reference that captures the
  // latest attemptId without causing stale-closure bugs.
  const handleFinalSubmit = useCallback(async (auto = false) => {
    setIsSubmittingFinal(true);
    let resolvedAttemptId = attemptId;
    try {
      if (attemptId && typeof attemptId === 'number') {
        // Submit the attempt — sets status='submitted' and triggers scoring
        try {
          await axiosInstance.post(`/exam-attempts/${attemptId}/submit`);
        } catch (submitErr) {
          const httpStatus = submitErr?.response?.status;
          // 409 = already submitted (e.g. auto-submitted by timer) — not an error
          if (httpStatus !== 409) {
            console.warn('Exam submission notice:', submitErr?.response?.data?.detail || submitErr.message);
          }
        }
      } else if (examId) {
        // Fallback: no valid numeric attemptId, navigate to exam-level result
        resolvedAttemptId = examId;
      }
    } catch (err) {
      console.warn('Final submit error:', err);
    } finally {
      setIsSubmittingFinal(false);
      setShowSubmitModal(false);
      // replace: true so browser Back cannot reopen the exam
      navigate(`/results/${resolvedAttemptId}`, { replace: true });
    }
  }, [attemptId, examId, navigate]);

  // ── Auto Countdown Timer ────────────────────────────────────────────────
  // NOTE: remainingSeconds is intentionally NOT in deps — including it would
  // restart the interval every second. We use functional setState instead.
  useEffect(() => {
    if (loading || remainingSeconds === null || remainingSeconds <= 0) return;

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          // Guard: only auto-submit if proctoring termination hasn't already fired
          if (!terminationFiredRef.current) {
            terminationFiredRef.current = true;
            handleFinalSubmit(true);
          }
          return 0;
        }

        // Warnings at 5 min (300s) and 1 min (60s)
        if (prev === 301) setTimerWarning('5min');
        else if (prev === 61) setTimerWarning('1min');

        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, handleFinalSubmit]);

  // ── Proctoring Security & Fullscreen Integration ────────────────────────────
  const handleSecurityTermination = useCallback(() => {
    if (terminationFiredRef.current) return;
    terminationFiredRef.current = true;

    // Show a brief alert then submit and lock the exam UI
    alert('Security Violation Limit Reached: Multiple infraction events logged. Your assessment is being submitted automatically.');

    // Mark as auto-submitted in UI state so the page locks immediately
    setAlreadySubmitted({
      attemptId: attemptId || examId,
      status: 'auto_submitted',
    });

    handleFinalSubmit(true);
  }, [handleFinalSubmit, attemptId, examId]);

  const {
    violationCount,
    maxViolations,
    showWarningModal: showSecurityWarning,
    lastViolationType,
    isFullscreen,
    enterFullscreen,
    dismissWarning: dismissSecurityWarning,
  } = useProctoringSecurity({
    attemptId: attemptId || examId,
    maxViolations: 3,
    onTerminate: handleSecurityTermination,
    enabled: !loading && !isSubmittingFinal,
  });

  // Anti-cheating: Prevent right-click context menu and inspect shortcuts
  useEffect(() => {
    const handleContextMenu = (e) => e.preventDefault();
    const handleKeyDown = (e) => {
      // Prevent F12 (Devtools)
      if (e.key === 'F12') {
        e.preventDefault();
      }
    };

    document.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // ── MCQ Selection Handlers ──────────────────────────────────────────────────
  const currentQuestion = questions[currentIndex] || null;
  const isCurrentMCQ = currentQuestion?.question_type !== 'coding';
  const currentQId = currentQuestion ? (currentQuestion.id ?? currentQuestion.question_id) : null;

  const handleSelectOption = (optionId) => {
    if (!currentQuestion || !currentQId) return;
    setMcqAnswers((prev) => ({ ...prev, [currentQId]: optionId }));
    saveAnswerToServer(currentQId, optionId);
  };

  const handleClearAnswer = () => {
    if (!currentQuestion || !currentQId) return;
    setMcqAnswers((prev) => {
      const copy = { ...prev };
      delete copy[currentQId];
      return copy;
    });
    saveAnswerToServer(currentQId, null);
  };

  const handleToggleReview = () => {
    if (!currentQuestion || !currentQId) return;
    setMarkedForReview((prev) => ({ ...prev, [currentQId]: !prev[currentQId] }));
  };

  // ── Coding Handlers ─────────────────────────────────────────────────────────
  const currentLanguage = currentQuestion ? (codingLanguages[currentQId] || 'python') : 'python';
  const currentCode = currentQuestion
    ? codingCodes[currentQId]?.[currentLanguage] ??
      (currentLanguage === 'python'
        ? '# Write your solution here\ndef solution():\n    pass\n'
        : currentLanguage === 'java'
        ? 'public class Solution {\n    public static void main(String[] args) {\n        // Your code\n    }\n}\n'
        : currentLanguage === 'cpp'
        ? '#include <iostream>\nusing namespace std;\n\nint main() {\n    return 0;\n}\n'
        : '// JavaScript solution\nfunction solution() {\n}\n')
    : '';

  const handleCodeChange = (newCode) => {
    if (!currentQuestion || !currentQId) return;
    setCodingCodes((prev) => ({
      ...prev,
      [currentQId]: {
        ...(prev[currentQId] || {}),
        [currentLanguage]: newCode,
      },
    }));
  };

  const handleLanguageChange = (newLang) => {
    if (!currentQuestion || !currentQId) return;
    setCodingLanguages((prev) => ({ ...prev, [currentQId]: newLang }));
  };

  const handleRunCodingSample = async () => {
    if (!currentQuestion || !currentQId) return;
    setIsRunningCode(true);
    try {
      const res = await axiosInstance.post('/coding/run', {
        question_id: currentQId,
        code: currentCode,
        language: currentLanguage,
        sample_test_cases: currentQuestion.sample_test_cases || [],
      });
      setCodingRunResults((prev) => ({
        ...prev,
        [currentQId]: res.data,
      }));
    } catch (err) {
      console.error('Run code error:', err);
      // Provide a user-visible error result
      setCodingRunResults((prev) => ({
        ...prev,
        [currentQId]: {
          verdict: 'Error',
          status: 'error',
          execution_time: '0ms',
          memory_used: '0 MB',
          test_cases: [],
          compile_error: err?.response?.data?.detail || err.message || 'Code execution failed.',
        },
      }));
    } finally {
      setIsRunningCode(false);
    }
  };

  const handleSubmitCodingQuestion = async () => {
    if (!currentQuestion || !currentQId) return;
    setIsSubmittingCode(true);
    try {
      const res = await axiosInstance.post('/coding/submit', {
        question_id: currentQId,
        code: currentCode,
        language: currentLanguage,
        attempt_id: attemptId || null,
      });
      setCodingSubmitResults((prev) => ({
        ...prev,
        [currentQId]: res.data,
      }));
      // Mark as submitted if evaluation succeeded
      if (res.data.status === 'accepted' || res.data.test_cases_passed > 0 || res.data.status) {
        setCodingStatuses((prev) => ({ ...prev, [currentQId]: 'submitted' }));
      }
    } catch (err) {
      console.error('Submit code error:', err);
      setCodingSubmitResults((prev) => ({
        ...prev,
        [currentQId]: {
          verdict: 'Submission Error',
          status: 'error',
          test_cases: [],
          total_test_cases: 0,
          passed_test_cases: 0,
        },
      }));
    } finally {
      setIsSubmittingCode(false);
    }
  };



  // ── Stats Computations for Palette & Submission Summary ──────────────────────
  const stats = useMemo(() => {
    let answered = 0;
    let visited = 0;
    let unanswered = 0;
    let review = 0;

    questions.forEach((q, idx) => {
      const qId = q.id ?? q.question_id ?? (idx + 1);
      const isAns = q.question_type === 'coding' ? !!codingStatuses[qId] : (mcqAnswers[qId] !== undefined && mcqAnswers[qId] !== null);
      const isRev = !!markedForReview[qId];
      const isVis = !!visitedQuestions[qId];

      if (isAns) {
        answered += 1;
      } else if (isVis) {
        visited += 1;
      } else {
        unanswered += 1;
      }

      if (isRev) {
        review += 1;
      }
    });

    return {
      total: questions.length,
      answered,
      visited,
      unanswered,
      review,
      remaining: questions.length - answered,
    };
  }, [questions, mcqAnswers, codingStatuses, markedForReview, visitedQuestions]);

  // Filtered question palette list
  const filteredQuestions = useMemo(() => {
    return questions.filter((q, idx) => {
      const qId = q.id ?? q.question_id ?? (idx + 1);
      const isAns = q.question_type === 'coding' ? !!codingStatuses[qId] : (mcqAnswers[qId] !== undefined && mcqAnswers[qId] !== null);
      const isRev = !!markedForReview[qId];
      const isVis = !!visitedQuestions[qId];

      if (paletteFilter === 'answered') return isAns;
      if (paletteFilter === 'visited') return isVis && !isAns;
      if (paletteFilter === 'unanswered') return !isAns && !isVis;
      if (paletteFilter === 'review') return isRev;
      return true;
    });
  }, [questions, paletteFilter, mcqAnswers, codingStatuses, markedForReview, visitedQuestions]);

  // Formatter for timer display
  const formatTimer = (secs) => {
    const s = Math.max(0, secs);
    const mins = Math.floor(s / 60);
    const rem = s % 60;
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(mins)}:${pad(rem)}`;
  };

  const studentDisplayName =
    user?.full_name ||
    user?.name ||
    user?.username ||
    (user?.email ? user.email.split('@')[0] : 'Student');

  if (loading) {
    return (
      <div className="vh-100 bg-dark text-white d-flex flex-column align-items-center justify-content-center">
        <div className="spinner-border text-primary mb-3" role="status" style={{ width: '3rem', height: '3rem' }}></div>
        <h5 className="fw-bold">Launching Examination Session...</h5>
        <p className="text-secondary small">Synchronizing questions and proctoring safeguards</p>
      </div>
    );
  }

  if (alreadySubmitted) {
    return (
      <div className="vh-100 bg-dark text-white d-flex align-items-center justify-content-center p-4">
        <div className="card bg-black border-success border-opacity-50 text-white p-4 p-md-5 rounded-4 text-center shadow-lg" style={{ maxWidth: '560px' }}>
          <div
            className="d-inline-flex align-items-center justify-content-center bg-success bg-opacity-20 text-success rounded-circle mb-3 mx-auto p-3"
            style={{ width: 72, height: 72 }}
          >
            <i className="bi bi-shield-check fs-1"></i>
          </div>
          <h3 className="fw-bold text-white mb-2">Exam Already Submitted</h3>
          <p className="text-secondary small mb-4">
            You have already completed and submitted this examination. Re-entering, retaking, or restarting this test is permanently locked. You can review your evaluated answers and scorecard below.
          </p>
          <div className="d-flex flex-wrap justify-content-center gap-2 mb-4">
            <span className="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50 px-3 py-2 rounded-pill small">
              Status: {alreadySubmitted.status === 'auto_submitted' ? 'Auto-Submitted (Timer / Violation)' : 'Submitted & Finalized'}
            </span>
            {alreadySubmitted.attemptId && (
              <span className="badge bg-secondary bg-opacity-25 text-light border border-secondary border-opacity-50 px-3 py-2 rounded-pill small">
                Attempt ID: #{alreadySubmitted.attemptId}
              </span>
            )}
          </div>
          <div className="d-flex flex-column flex-sm-row justify-content-center gap-3">
            <button
              id="btn-view-scorecard-locked"
              className="btn btn-success px-4 py-2 rounded-3 fw-semibold d-inline-flex align-items-center justify-content-center gap-2 shadow-sm"
              onClick={() => navigate(`/results/${alreadySubmitted.attemptId || examId}`, { replace: true })}
            >
              <i className="bi bi-file-earmark-bar-graph-fill"></i>
              <span>View Result / Scorecard</span>
            </button>
            <button
              className="btn btn-outline-light px-3 py-2 rounded-3"
              onClick={() => navigate('/student', { replace: true })}
            >
              <i className="bi bi-arrow-left me-1"></i> Return to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (error || questions.length === 0) {
    return (
      <div className="vh-100 bg-dark text-white d-flex align-items-center justify-content-center p-4">
        <div className="card bg-black border-danger border-opacity-50 text-white p-4 rounded-4 text-center" style={{ maxWidth: '500px' }}>
          <i className="bi bi-exclamation-triangle-fill text-danger fs-1 mb-2"></i>
          <h4 className="fw-bold">Unable to Load Examination</h4>
          <p className="text-secondary small">{error || 'No questions available.'}</p>
          <button className="btn btn-outline-light rounded-3 mt-2" onClick={() => navigate('/student')}>
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="live-exam-page vh-100 d-flex flex-column bg-dark text-white overflow-hidden font-sans-serif">
      {/* ── TOP LIVE EXAM CONTROL BAR ────────────────────────────────────────── */}
      <header className="navbar navbar-dark bg-black px-3 border-bottom border-secondary border-opacity-25" style={{ height: '60px' }}>
        {/* Left Exam Info */}
        <div className="d-flex align-items-center gap-2 gap-md-3">
          <button
            className="btn btn-dark btn-sm text-secondary d-flex align-items-center gap-1 border-secondary border-opacity-25"
            onClick={() => setShowSubmitModal(true)}
            title="Finish Assessment"
          >
            <i className="bi bi-box-arrow-left"></i>
            <span className="d-none d-sm-inline">Exit / Submit</span>
          </button>

          <div className="border-end border-secondary border-opacity-25 pe-3 d-none d-md-block">
            <span className="fw-bold text-white d-block lead mb-0" style={{ fontSize: '0.95rem' }}>
              {exam?.title || 'Online Assessment'}
            </span>
          </div>

          {/* High-Contrast Clear Student Candidate Badge */}
          <div className="d-flex align-items-center gap-1.5 px-3 py-1 rounded-pill bg-dark border border-secondary border-opacity-50 shadow-sm">
            <i className="bi bi-person-badge-fill text-info fs-6"></i>
            <span className="text-secondary small fw-semibold d-none d-sm-inline">Candidate:</span>
            <span className="text-white fw-bold small text-capitalize">{studentDisplayName}</span>
          </div>

          {/* Fullscreen indicator / toggle */}
          <button
            type="button"
            className={`btn btn-sm rounded-pill px-2.5 py-1 d-flex align-items-center gap-1 ${
              isFullscreen ? 'btn-outline-success' : 'btn-outline-warning animate-pulse'
            }`}
            onClick={enterFullscreen}
            title={isFullscreen ? 'Full Screen Active' : 'Click to Enable Full Screen'}
          >
            <i className={`bi ${isFullscreen ? 'bi-arrows-angle-contract' : 'bi-arrows-fullscreen'}`}></i>
            <span className="d-none d-lg-inline small">{isFullscreen ? 'Fullscreen' : 'Go Fullscreen'}</span>
          </button>

          {violationCount > 0 && (
            <span className="badge bg-danger bg-opacity-25 text-danger border border-danger border-opacity-50">
              <i className="bi bi-shield-exclamation me-1"></i>
              Violations: {violationCount}/{maxViolations}
            </span>
          )}
        </div>

        {/* Center Countdown Clock */}
        <div className="d-flex align-items-center gap-2">
          <div
            className={`d-flex align-items-center gap-2 px-3 py-1 rounded-pill border transition-all ${
              remainingSeconds === null
                ? 'bg-secondary bg-opacity-20 border-secondary text-white'
                : remainingSeconds < 300
                ? 'bg-danger bg-opacity-20 border-danger text-white animate-pulse'
                : remainingSeconds < 600
                ? 'bg-warning bg-opacity-20 border-warning text-white'
                : 'bg-dark bg-opacity-75 border-secondary border-opacity-50 text-white'
            }`}
          >
            <i className="bi bi-clock-history fs-5"></i>
            <span className="fw-bold font-monospace fs-5">{formatTimer(remainingSeconds)}</span>
          </div>
        </div>

        {/* Right Action Tools */}
        <div className="d-flex align-items-center gap-2 gap-md-3">
          {/* Auto-Save Indicator */}
          <div className="d-none d-md-flex align-items-center gap-1.5 small text-secondary" style={{ fontSize: '0.75rem' }}>
            <i className={`bi ${saveStatus === 'saving' ? 'bi-arrow-repeat spin text-warning' : 'bi-cloud-check-fill text-success'}`}></i>
            <span>{saveStatus === 'saving' ? 'Saving...' : 'Saved'}</span>
          </div>

          {/* Question Palette Drawer Toggle */}
          <button
            className="btn btn-sm btn-outline-secondary text-white border-opacity-50 d-flex align-items-center gap-1 px-2.5 py-1 rounded-3"
            onClick={() => setPaletteOpen(!paletteOpen)}
            title="Toggle Question Palette"
          >
            <i className="bi bi-grid-3x3-gap-fill text-warning"></i>
            <span className="d-none d-sm-inline small">Palette ({stats.answered}/{stats.total})</span>
          </button>

          {/* Submit Exam Button */}
          <button
            id="btn-submit-exam-header"
            className="btn btn-sm btn-danger px-3 py-1 rounded-3 fw-semibold d-flex align-items-center gap-1.5"
            onClick={() => setShowSubmitModal(true)}
          >
            <i className="bi bi-send-check-fill"></i>
            <span>Submit Exam</span>
          </button>
        </div>
      </header>

      {/* ── MAIN WORKSPACE SPLIT ─────────────────────────────────────────────── */}
      <div className="flex-grow-1 d-flex overflow-hidden position-relative">
        {/* Left Side: Question Statement & Interactive Area */}
        <main className="flex-grow-1 d-flex flex-column overflow-auto p-3 p-md-4" style={{ backgroundColor: '#0f172a' }}>
          {/* Question Header Bar */}
          <div className="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25 gap-2">
            <div className="d-flex align-items-center gap-2">
              <span className="badge bg-primary fs-7">
                Question {currentIndex + 1} of {questions.length}
              </span>
              <span className={`badge ${isCurrentMCQ ? 'bg-info bg-opacity-25 text-info border border-info border-opacity-25' : 'bg-danger bg-opacity-25 text-danger border border-danger border-opacity-25'}`}>
                {isCurrentMCQ ? 'Multiple Choice (MCQ)' : 'Coding Challenge'}
              </span>
              <span className="badge bg-secondary bg-opacity-25 text-secondary border border-secondary border-opacity-25">
                +{currentQuestion?.marks || 1} Marks
              </span>
            </div>

            <div className="d-flex align-items-center gap-2">
              {/* Mark for Review Toggle */}
              <button
                className={`btn btn-sm ${markedForReview[currentQId] ? 'btn-purple text-white bg-indigo' : 'btn-outline-secondary text-light'} rounded-3 d-flex align-items-center gap-1`}
                onClick={handleToggleReview}
                title="Mark this question to review later"
              >
                <i className={`bi ${markedForReview[currentQId] ? 'bi-bookmark-star-fill text-warning' : 'bi-bookmark-star'}`}></i>
                <span className="small">{markedForReview[currentQId] ? 'Marked for Review' : 'Mark for Review'}</span>
              </button>

              {/* Clear Answer Button for MCQ */}
              {isCurrentMCQ && mcqAnswers[currentQId] !== undefined && (
                <button
                  className="btn btn-sm btn-outline-warning rounded-3 small"
                  onClick={handleClearAnswer}
                  title="Clear selected option"
                >
                  Clear Answer
                </button>
              )}
            </div>
          </div>

          {/* ── MCQ MODE ──────────────────────────────────────────────────────── */}
          {isCurrentMCQ ? (
            <div className="card bg-dark border-secondary border-opacity-25 shadow-sm rounded-4 p-4 mb-4 flex-grow-1 d-flex flex-column">
              {/* Question Text */}
              <div className="fs-5 fw-semibold text-white mb-4 lh-base font-monospace" style={{ whiteSpace: 'pre-wrap' }}>
                {currentQuestion?.question_text || currentQuestion?.text || 'No question content available.'}
              </div>

              {/* Options List */}
              <div className="options-container d-flex flex-column gap-2.5 mb-4">
                {currentQuestion?.options && currentQuestion.options.length > 0 ? (
                  currentQuestion.options.map((opt, oIdx) => {
                    const optionId = typeof opt === 'object' ? opt.id : oIdx + 1;
                    const optionText = typeof opt === 'object' ? opt.option_text || opt.text : opt;
                    const isSelected = mcqAnswers[currentQId] === optionId;

                    return (
                      <div
                        key={optionId}
                        className={`p-3 rounded-3 border d-flex align-items-center gap-3 transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-primary bg-opacity-20 border-primary shadow-sm text-white'
                            : 'bg-black bg-opacity-30 border-secondary border-opacity-25 text-light hover-bg-light'
                        }`}
                        onClick={() => handleSelectOption(optionId)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div
                          className={`rounded-circle d-flex align-items-center justify-content-center fw-bold ${
                            isSelected ? 'bg-primary text-white' : 'bg-secondary bg-opacity-25 text-secondary border border-secondary'
                          }`}
                          style={{ width: 28, height: 28, fontSize: '0.8rem', flexShrink: 0 }}
                        >
                          {String.fromCharCode(65 + oIdx)}
                        </div>
                        <div className="flex-grow-1 text-break">{optionText}</div>
                        {isSelected && <i className="bi bi-check-circle-fill text-primary fs-5"></i>}
                      </div>
                    );
                  })
                ) : (
                  <div className="text-secondary small">No options configured for this MCQ question.</div>
                )}
              </div>
            </div>
          ) : (
            /* ── CODING MODE ──────────────────────────────────────────────────── */
            <div className="row g-3 flex-grow-1 overflow-hidden">
              {/* Problem Description & Constraints */}
              <div className="col-12 col-xl-5 h-100 overflow-auto">
                <div className="card bg-dark border-secondary border-opacity-25 rounded-4 p-3 h-100">
                  <h5 className="fw-bold text-white mb-2">{currentQuestion?.title || 'Coding Problem'}</h5>
                  <div className="text-light small mb-3 lh-base" style={{ whiteSpace: 'pre-wrap' }}>
                    {currentQuestion?.question_text || currentQuestion?.text}
                  </div>

                  {currentQuestion?.constraints && (
                    <div className="mb-3">
                      <strong className="text-secondary small text-uppercase">Constraints:</strong>
                      <pre className="bg-black p-2 rounded-3 border border-secondary border-opacity-25 text-warning small mt-1 font-monospace">
                        {currentQuestion.constraints}
                      </pre>
                    </div>
                  )}

                  {currentQuestion?.sample_test_cases && (
                    <div>
                      <strong className="text-secondary small text-uppercase">Sample Test Cases:</strong>
                      <div className="d-flex flex-column gap-2 mt-1">
                        {currentQuestion.sample_test_cases.map((stc, stcIdx) => (
                          <div key={stcIdx} className="bg-black p-2 rounded-3 border border-secondary border-opacity-25 small font-monospace">
                            <div className="text-secondary">Input: <span className="text-white">{stc.input}</span></div>
                            <div className="text-secondary">Output: <span className="text-success">{stc.expected_output}</span></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Code Editor & Test Runner */}
              <div className="col-12 col-xl-7 h-100 d-flex flex-column">
                <div className="card bg-black border-secondary border-opacity-25 rounded-4 overflow-hidden flex-grow-1 d-flex flex-column">
                  {/* Editor Header */}
                  <div className="d-flex justify-content-between align-items-center p-2 px-3 bg-dark border-bottom border-secondary border-opacity-25">
                    <LanguageSelector
                      selectedLanguage={currentLanguage}
                      allowedLanguages={currentQuestion?.allowed_languages || ['python', 'java', 'cpp', 'javascript']}
                      onSelectLanguage={handleLanguageChange}
                    />
                    <div className="d-flex align-items-center gap-2">
                      <RunButton onRun={handleRunCodingSample} isRunning={isRunningCode} />
                      <SubmitButton
                        onSubmit={handleSubmitCodingQuestion}
                        isSubmitting={isSubmittingCode}
                        isSubmitted={!!codingStatuses[currentQId]}
                      />
                    </div>
                  </div>

                  {/* Monaco Editor Container */}
                  <div className="flex-grow-1 position-relative p-2" style={{ minHeight: '260px' }}>
                    <MonacoEditorWrapper
                      value={currentCode}
                      onChange={handleCodeChange}
                      language={currentLanguage}
                      readOnly={!!codingStatuses[currentQId]}
                    />
                  </div>

                  {/* Test Case Output Tray */}
                  <div className="border-top border-secondary border-opacity-25" style={{ height: '180px' }}>
                    <TestCaseResultPanel
                      runResult={codingRunResults[currentQId]}
                      submissionResult={codingSubmitResults[currentQId]}
                      isRunning={isRunningCode}
                      isSubmitting={isSubmittingCode}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── FOOTER NAVIGATION BAR ──────────────────────────────────────────── */}
          <div className="d-flex justify-content-between align-items-center mt-auto pt-3 border-top border-secondary border-opacity-25">
            <button
              className="btn btn-outline-secondary text-white btn-sm px-3 rounded-3 d-flex align-items-center gap-1.5"
              disabled={currentIndex === 0}
              onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            >
              <i className="bi bi-chevron-left"></i> Previous Question
            </button>

            <div className="text-secondary small d-none d-sm-block">
              Question {currentIndex + 1} of {questions.length} • {stats.remaining} Remaining
            </div>

            {currentIndex < questions.length - 1 ? (
              <button
                className="btn btn-primary btn-sm px-4 rounded-3 d-flex align-items-center gap-1.5"
                onClick={() => setCurrentIndex((prev) => Math.min(questions.length - 1, prev + 1))}
              >
                Next Question <i className="bi bi-chevron-right"></i>
              </button>
            ) : (
              <button
                className="btn btn-success btn-sm px-4 rounded-3 d-flex align-items-center gap-1.5 fw-semibold shadow-sm"
                onClick={() => setShowSubmitModal(true)}
              >
                Review & Submit <i className="bi bi-check-circle-fill"></i>
              </button>
            )}
          </div>
        </main>

        {/* ── RIGHT SLIDE-OUT QUESTION PALETTE DRAWER ─────────────────────────── */}
        <aside
          className={`question-palette-drawer bg-black border-start border-secondary border-opacity-25 p-3 d-flex flex-column transition-all ${
            paletteOpen ? 'd-flex' : 'd-none d-xl-flex'
          }`}
          style={{ width: '320px', flexShrink: 0, overflowY: 'auto' }}
        >
          <div className="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary border-opacity-25">
            <h6 className="fw-bold mb-0 text-white">
              <i className="bi bi-grid-3x3-gap-fill text-primary me-2"></i>Question Palette
            </h6>
            <button className="btn-close btn-close-white btn-sm d-xl-none" onClick={() => setPaletteOpen(false)}></button>
          </div>

          {/* Palette Legend */}
          <div className="row g-2 small mb-3 text-secondary" style={{ fontSize: '0.78rem' }}>
            <div className="col-6 d-flex align-items-center gap-1.5">
              <span className="rounded-circle d-inline-block" style={{ width: 11, height: 11, backgroundColor: '#16A34A' }}></span>
              <span className="text-light">Answered ({stats.answered})</span>
            </div>
            <div className="col-6 d-flex align-items-center gap-1.5">
              <span className="rounded-circle d-inline-block" style={{ width: 11, height: 11, backgroundColor: '#F59E0B' }}></span>
              <span className="text-light">Visited ({stats.visited})</span>
            </div>
            <div className="col-6 d-flex align-items-center gap-1.5">
              <span className="rounded-circle d-inline-block" style={{ width: 11, height: 11, backgroundColor: '#374151', border: '1px solid rgba(255,255,255,0.3)' }}></span>
              <span className="text-light">Unanswered ({stats.unanswered})</span>
            </div>
            <div className="col-6 d-flex align-items-center gap-1.5">
              <span className="rounded-circle d-inline-block" style={{ width: 11, height: 11, backgroundColor: '#7C3AED' }}></span>
              <span className="text-light">Review ({stats.review})</span>
            </div>
            <div className="col-12 d-flex align-items-center gap-1.5 pt-1.5 border-top border-secondary border-opacity-25">
              <span className="rounded-circle d-inline-block" style={{ width: 11, height: 11, backgroundColor: '#2563EB', border: '2px solid #93C5FD' }}></span>
              <span className="text-info fw-bold">Current Question: #{currentIndex + 1}</span>
            </div>
          </div>

          {/* Palette Filter Tabs */}
          <div className="btn-group btn-group-sm w-100 mb-3" role="group" aria-label="Question filters">
            {[
              { id: 'all', label: `All (${stats.total})` },
              { id: 'answered', label: `Ans (${stats.answered})` },
              { id: 'visited', label: `Vis (${stats.visited})` },
              { id: 'unanswered', label: `Unans (${stats.unanswered})` },
              { id: 'review', label: `Rev (${stats.review})` },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                className={`btn btn-sm px-1 py-1 ${
                  paletteFilter === f.id ? 'btn-primary fw-bold' : 'btn-outline-secondary text-light'
                }`}
                style={{ fontSize: '0.72rem' }}
                onClick={() => setPaletteFilter(f.id)}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Questions 5-Column Grid Matrix */}
          <div
            className="questions-grid mb-4"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: '8px',
            }}
          >
            {filteredQuestions.map((q) => {
              const originalIndex = q._originalIndex !== undefined
                ? q._originalIndex
                : questions.findIndex((item) => (item.id ?? item.question_id) === (q.id ?? q.question_id));
              const serialNum = originalIndex + 1;
              const qId = q.id ?? q.question_id ?? serialNum;
              const isCurrent = originalIndex === currentIndex;
              const isAns = q.question_type === 'coding' ? !!codingStatuses[qId] : (mcqAnswers[qId] !== undefined && mcqAnswers[qId] !== null);
              const isRev = !!markedForReview[qId];
              const isVis = !!visitedQuestions[qId];

              // Base state styling
              let bgStyle = '#374151'; // Unanswered (gray)
              let borderStyle = '1px solid rgba(255, 255, 255, 0.15)';
              let textStyle = '#F3F4F6';
              let stateLabel = 'Unanswered';

              if (isAns) {
                bgStyle = '#16A34A'; // Green
                borderStyle = isRev ? '2px solid #C084FC' : '1px solid #15803D';
                textStyle = '#FFFFFF';
                stateLabel = isRev ? 'Answered & Marked for Review' : 'Answered';
              } else if (isRev) {
                bgStyle = '#7C3AED'; // Purple
                borderStyle = '1px solid #6D28D9';
                textStyle = '#FFFFFF';
                stateLabel = 'Marked for Review';
              } else if (isVis) {
                bgStyle = '#F59E0B'; // Orange
                borderStyle = '1px solid #D97706';
                textStyle = '#FFFFFF';
                stateLabel = 'Visited (Unanswered)';
              }

              if (isCurrent) {
                stateLabel += ' (Current Question)';
              }

              return (
                <button
                  key={qId}
                  type="button"
                  className="btn p-0 d-flex align-items-center justify-content-center position-relative transition-all"
                  style={{
                    height: '42px',
                    width: '100%',
                    backgroundColor: isCurrent && !isAns && !isRev && !isVis ? '#2563EB' : bgStyle,
                    color: textStyle,
                    border: isCurrent ? '2px solid #60A5FA' : borderStyle,
                    borderRadius: '8px',
                    fontWeight: '700',
                    fontSize: '0.9rem',
                    outline: isCurrent ? '2px solid #93C5FD' : 'none',
                    outlineOffset: isCurrent ? '2px' : '0px',
                    boxShadow: isCurrent ? '0 0 12px rgba(96, 165, 250, 0.75)' : 'none',
                    cursor: 'pointer',
                  }}
                  onClick={() => {
                    setCurrentIndex(originalIndex);
                    setPaletteOpen(false);
                  }}
                  title={`Question ${serialNum} - ${stateLabel}`}
                  aria-label={`Question ${serialNum} - ${stateLabel}`}
                >
                  <span>{serialNum}</span>
                  {isRev && (
                    <span
                      className="position-absolute top-0 end-0 translate-middle p-1 bg-warning border border-dark rounded-circle shadow-sm"
                      style={{ width: 8, height: 8, marginTop: '2px', marginRight: '2px' }}
                      title="Marked for Review"
                    />
                  )}
                </button>
              );
            })}
          </div>

          {/* Finish Button in Palette */}
          <div className="mt-auto pt-3 border-top border-secondary border-opacity-25">
            <button
              className="btn btn-outline-danger w-100 btn-sm rounded-3 py-2 fw-semibold"
              onClick={() => setShowSubmitModal(true)}
            >
              <i className="bi bi-flag-fill me-1"></i> Submit Examination
            </button>
          </div>
        </aside>
      </div>

      {/* ── SUBMIT CONFIRMATION SUMMARY MODAL ─────────────────────────────────── */}
      {showSubmitModal && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.75)', zIndex: 1060 }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content bg-dark text-white border-secondary border-opacity-50 rounded-4 shadow-lg">
              <div className="modal-header border-bottom border-secondary border-opacity-25">
                <h5 className="modal-title fw-bold text-white d-flex align-items-center gap-2">
                  <i className="bi bi-send-check text-success"></i> Confirm Exam Submission
                </h5>
                <button type="button" className="btn-close btn-close-white" onClick={() => setShowSubmitModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                <p className="text-secondary small mb-3">
                  Please review your question completion status before submitting. Once submitted, you will not be able to modify any responses.
                </p>

                <div className="row g-2 mb-4 text-center">
                  <div className="col-3">
                    <div className="p-2.5 bg-success bg-opacity-10 border border-success border-opacity-25 rounded-3">
                      <div className="fs-4 fw-bold text-success">{stats.answered}</div>
                      <div className="text-secondary small" style={{ fontSize: '0.75rem' }}>Answered</div>
                    </div>
                  </div>
                  <div className="col-3">
                    <div className="p-2.5 bg-warning bg-opacity-10 border border-warning border-opacity-25 rounded-3">
                      <div className="fs-4 fw-bold text-warning">{stats.visited}</div>
                      <div className="text-secondary small" style={{ fontSize: '0.75rem' }}>Visited</div>
                    </div>
                  </div>
                  <div className="col-3">
                    <div className="p-2.5 bg-secondary bg-opacity-10 border border-secondary border-opacity-25 rounded-3">
                      <div className="fs-4 fw-bold text-secondary">{stats.unanswered}</div>
                      <div className="text-secondary small" style={{ fontSize: '0.75rem' }}>Unanswered</div>
                    </div>
                  </div>
                  <div className="col-3">
                    <div className="p-2.5 bg-indigo bg-opacity-10 border border-indigo border-opacity-25 rounded-3">
                      <div className="fs-4 fw-bold" style={{ color: '#8B5CF6', zIndex: 1, position: 'relative' }}>{stats.review}</div>
                      <div className="text-secondary small" style={{ fontSize: '0.75rem' }}>Review</div>
                    </div>
                  </div>
                </div>

                {(stats.unanswered > 0 || stats.visited > 0) && (
                  <div className="alert alert-warning bg-warning bg-opacity-10 border-warning border-opacity-25 text-warning small rounded-3 mb-0">
                    <i className="bi bi-exclamation-triangle-fill me-2"></i>
                    You have {stats.unanswered + stats.visited} unanswered question{stats.unanswered + stats.visited > 1 ? 's' : ''} ({stats.visited} visited, {stats.unanswered} unvisited).
                  </div>
                )}
              </div>
              <div className="modal-footer border-top border-secondary border-opacity-25">
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setShowSubmitModal(false)}>
                  Continue Exam
                </button>
                <button
                  type="button"
                  className="btn btn-success btn-sm px-4 fw-semibold"
                  disabled={isSubmittingFinal}
                  onClick={() => handleFinalSubmit(false)}
                >
                  {isSubmittingFinal ? <span className="spinner-border spinner-border-sm me-2"></span> : null}
                  Confirm & Submit
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PROCTORING TAB-SWITCH & FULLSCREEN SECURITY MODAL ────────────────── */}
      {showSecurityWarning && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 1070 }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content bg-black text-white border-danger rounded-4 shadow-lg">
              <div className="modal-header border-bottom border-danger border-opacity-50">
                <h5 className="modal-title fw-bold text-danger d-flex align-items-center gap-2">
                  <i className="bi bi-shield-exclamation fs-4"></i> Anti-Cheating / Security Notice
                </h5>
              </div>
              <div className="modal-body p-4 text-center">
                <div className="display-4 text-danger mb-2">
                  <i className={lastViolationType === 'fullscreen_exit' || lastViolationType === 'fullscreen_required' ? 'bi-arrows-fullscreen' : 'bi-eye-slash-fill'}></i>
                </div>
                <h5 className="fw-bold text-white mb-2">
                  {lastViolationType === 'fullscreen_exit'
                    ? 'Fullscreen Mode Exited'
                    : lastViolationType === 'fullscreen_required'
                    ? 'Fullscreen Mode Required'
                    : 'Window Focus Lost / Tab Switch Detected'}
                </h5>
                <p className="text-secondary small mb-3">
                  {lastViolationType === 'fullscreen_exit' || lastViolationType === 'fullscreen_required'
                    ? 'To maintain integrity and prevent unauthorized external tools, this examination must remain in Full Screen mode at all times.'
                    : 'You have switched tabs or navigated away from the assessment window. This infraction has been logged into your security audit trail.'}
                </p>
                {lastViolationType !== 'fullscreen_required' && (
                  <div className="alert alert-danger bg-danger bg-opacity-10 border-danger border-opacity-25 text-danger small mb-3">
                    Violation {violationCount} of {maxViolations}. Reaching {maxViolations} infractions will automatically submit and terminate your test.
                  </div>
                )}
                <button
                  className="btn btn-primary btn-sm px-4 py-2 rounded-3 fw-semibold d-inline-flex align-items-center gap-2"
                  onClick={dismissSecurityWarning}
                >
                  <i className="bi bi-arrows-fullscreen"></i>
                  <span>Resume Fullscreen Assessment</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveExamSessionPage;
