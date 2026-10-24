import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCodingExam } from '../context/CodingExamContext';
import { useExamAttempt } from '../context/ExamAttemptContext';
import ProblemStatementPanel from '../components/coding/ProblemStatementPanel';
import MonacoEditorWrapper from '../components/coding/MonacoEditorWrapper';
import LanguageSelector from '../components/coding/LanguageSelector';
import RunButton from '../components/coding/RunButton';
import SubmitButton from '../components/coding/SubmitButton';
import TestCaseResultPanel from '../components/coding/TestCaseResultPanel';
import QuestionNavigatorSidebar from '../components/coding/QuestionNavigatorSidebar';
import ExamTimerBar from '../components/exam/ExamTimerBar';
import TimeWarningModal from '../components/exam/TimeWarningModal';
import AutoSaveIndicator from '../components/exam/AutoSaveIndicator';
import useAutoSave from '../hooks/useAutoSave';

const CodingExamLayout = ({ attemptId: propAttemptId }) => {
  const navigate = useNavigate();
  const [showNavigator, setShowNavigator] = useState(false);
  const { attemptId: contextAttemptId } = useExamAttempt();
  
  // Use the prop attemptId if provided, otherwise fall back to context
  const actualAttemptId = propAttemptId || contextAttemptId;

  const {
    questions,
    currentQuestionIndex,
    currentQuestion,
    loading,
    error,
    isRunning,
    isSubmitting,
    runResults,
    submissionResults,
    questionStatuses,
    questionCodes,
    questionLanguages,
    getCurrentCode,
    getCurrentLanguage,
    setCode,
    setLanguage,
    executeRunCode,
    executeSubmitCode,
  } = useCodingExam();

  const { attemptId, isExpired, isSubmitted: examSubmitted } = useExamAttempt();

  const code = getCurrentCode();
  const language = getCurrentLanguage();
  const currentQId = currentQuestion?.id;

  const currentRunResult = currentQId ? runResults[currentQId] : null;
  const currentSubmissionResult = currentQId ? submissionResults[currentQId] : null;
  const isSubmitted = currentQId ? questionStatuses[currentQId] === 'submitted' : false;

  // ── Auto-Save Setup ─────────────────────────────────────────────────────────
  // Build the payload from current in-memory coding state
  const buildAutoSavePayload = useCallback(() => {
    const coding_drafts = {};
    if (questionCodes) {
      Object.entries(questionCodes).forEach(([qId, langMap]) => {
        const lang = questionLanguages?.[qId] || 'python';
        const draft = langMap?.[lang];
        if (draft && draft.trim()) {
          coding_drafts[qId] = { language: lang, code: draft };
        }
      });
    }
    return {
      mcq_answers: {}, // Coding exam — no MCQ answers
      coding_drafts,
    };
  }, [questionCodes, questionLanguages]);

  const {
    status: saveStatus,
    lastSavedAt,
    errorMsg: saveErrorMsg,
    saveNow,
    triggerDirtySave,
  } = useAutoSave(attemptId, buildAutoSavePayload, {
    intervalMs: 30_000,
    debounceMs: 2_000,
    enabled: !isExpired && !examSubmitted,
  });

  // Wrap setCode to additionally trigger the debounced dirty save
  const handleCodeChange = useCallback((newCode) => {
    setCode(newCode);
    triggerDirtySave();
  }, [setCode, triggerDirtySave]);

  if (loading) {
    return (
      <div className="vh-100 bg-dark text-white d-flex flex-column align-items-center justify-content-center">
        <div className="spinner-border text-primary mb-3" role="status" style={{ width: '3rem', height: '3rem' }}></div>
        <h5 className="fw-bold">Loading Coding Environment...</h5>
        <p className="text-secondary small">Preparing problem statements and editor configurations</p>
      </div>
    );
  }

  if (error && questions.length === 0) {
    return (
      <div className="vh-100 bg-dark text-white d-flex align-items-center justify-content-center p-4">
        <div className="card bg-black border-danger border-opacity-50 text-white p-4 rounded-4 text-center" style={{ maxWidth: '500px' }}>
          <i className="bi bi-exclamation-triangle-fill text-danger fs-1 mb-2"></i>
          <h4 className="fw-bold">Unable to Load Assessment</h4>
          <p className="text-secondary small">{error}</p>
          <button className="btn btn-outline-light rounded-3 mt-2" onClick={() => navigate('/student')}>
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="coding-exam-layout vh-100 d-flex flex-column bg-dark text-white overflow-hidden font-sans-serif">
      {/* ── IDE Header Navigation ────────────────────────────────────────────── */}
      <header className="navbar navbar-dark bg-black px-3 border-bottom border-secondary border-opacity-25" style={{ height: '56px' }}>
        <div className="d-flex align-items-center gap-3">
          <button
            className="btn btn-dark btn-sm text-secondary d-flex align-items-center gap-1 border-secondary border-opacity-25"
            onClick={() => navigate('/student')}
            title="Exit to Student Dashboard"
          >
            <i className="bi bi-arrow-left"></i>
            <span className="d-none d-sm-inline">Dashboard</span>
          </button>

          <div className="border-end border-secondary border-opacity-25 pe-3">
            <span className="fw-bold text-white d-block lead mb-0" style={{ fontSize: '0.95rem' }}>
              Coding Assessment Hub
            </span>
          </div>

          <div className="d-none d-md-flex align-items-center gap-2">
            <span className="badge bg-primary">
              Question {currentQuestionIndex + 1} of {questions.length}
            </span>
            {isSubmitted && <span className="badge bg-success"><i className="bi bi-check-lg"></i> Submitted</span>}
          </div>
        </div>

        {/* Action Controls Header Right */}
        <div className="d-flex align-items-center gap-3">
          {/* Auto-Save Status Indicator */}
          <AutoSaveIndicator
            status={saveStatus}
            lastSavedAt={lastSavedAt}
            errorMsg={saveErrorMsg}
          />

          {/* Exam Synchronized Timer Bar */}
          <ExamTimerBar />

          {/* Question Palette Drawer Toggle */}
          <button
            className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1 text-light border-opacity-50"
            onClick={() => setShowNavigator(!showNavigator)}
          >
            <i className="bi bi-grid-3x3-gap-fill text-warning"></i>
            <span className="d-none d-sm-inline">Questions</span>
          </button>

          {/* Finish Exam Button - triggers a final save before exit */}
          <button
            className="btn btn-outline-danger btn-sm rounded-3"
            onClick={async () => {
              if (window.confirm('Are you sure you want to finish the coding exam?')) {
                await saveNow();
                navigate('/student');
              }
            }}
          >
            Finish Exam
          </button>
        </div>
      </header>

      {/* Warning Alert Modal */}
      <TimeWarningModal />

      {/* ── Main Split View Body ──────────────────────────────────────────────── */}
      <div className="flex-grow-1 d-flex overflow-hidden position-relative">
        <div className="row g-0 flex-grow-1 w-100 overflow-hidden">
          {/* Left Panel: Problem Statement */}
          <div className="col-12 col-lg-5 h-100 border-end border-secondary border-opacity-25 overflow-hidden">
            <ProblemStatementPanel
              question={currentQuestion}
              index={currentQuestionIndex}
              totalQuestions={questions.length}
            />
          </div>

          {/* Right Panel: Code Editor & Execution Results */}
          <div className="col-12 col-lg-7 h-100 d-flex flex-column bg-dark overflow-hidden">
            {/* Editor Action Toolbar */}
            <div
              className="d-flex flex-wrap justify-content-between align-items-center p-2 px-3 bg-black bg-opacity-40 border-bottom border-secondary border-opacity-25 gap-2"
              style={{ minHeight: '48px' }}
            >
              <LanguageSelector
                selectedLanguage={language}
                allowedLanguages={currentQuestion?.allowed_languages}
                onSelectLanguage={setLanguage}
              />

              <div className="d-flex align-items-center gap-2">
                <RunButton onRun={executeRunCode} isRunning={isRunning} />
                <SubmitButton
                  onSubmit={executeSubmitCode}
                  isSubmitting={isSubmitting}
                  isSubmitted={isSubmitted}
                  attemptId={actualAttemptId}
                />
              </div>
            </div>

            {/* Monaco Editor Container */}
            <div className="flex-grow-1 position-relative p-2 bg-dark overflow-hidden">
              <MonacoEditorWrapper
                value={code}
                onChange={handleCodeChange}
                language={language}
                readOnly={isSubmitted}
              />
            </div>

            {/* Bottom Test Case Result Panel */}
            <div className="border-top border-secondary border-opacity-25" style={{ height: '220px' }}>
              <TestCaseResultPanel
                runResult={currentRunResult}
                submissionResult={currentSubmissionResult}
                isRunning={isRunning}
                isSubmitting={isSubmitting}
              />
            </div>
          </div>
        </div>

        {/* Slide-out Question Navigator Sidebar */}
        <QuestionNavigatorSidebar
          isOpen={showNavigator}
          onClose={() => setShowNavigator(false)}
        />
      </div>
    </div>
  );
};

export default CodingExamLayout;
