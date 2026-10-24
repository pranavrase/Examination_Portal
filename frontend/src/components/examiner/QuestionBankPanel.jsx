import React, { useEffect, useState } from 'react';
import { useExaminer } from '../../context/ExaminerContext';
import QuestionFormModal from './QuestionFormModal';

const DIFFICULTY_COLOR = {
  easy: 'success',
  medium: 'warning',
  hard: 'danger',
};

const TYPE_ICON = {
  mcq: 'bi-ui-radios',
  true_false: 'bi-toggle-on',
  short_answer: 'bi-pencil-square',
  coding: 'bi-code-slash',
};

const QuestionBankPanel = ({ exam, onBack }) => {
  const {
    questions,
    loadingQuestions,
    questionsError,
    actionLoading,
    successMessage,
    clearMessages,
    fetchQuestions,
    removeQuestion,
  } = useExaminer();

  const [showModal, setShowModal] = useState(false);
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    if (exam?.id) fetchQuestions(exam.id);
  }, [exam?.id, fetchQuestions]);

  const handleEdit = (q) => {
    setEditingQuestion(q);
    setShowModal(true);
  };

  const handleDelete = async (qId) => {
    try {
      await removeQuestion(exam.id, qId);
      setConfirmDeleteId(null);
    } catch (_) {}
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingQuestion(null);
    fetchQuestions(exam.id);
  };

  const typeLabel = (type) => {
    const labels = {
      mcq: 'MCQ',
      true_false: 'True/False',
      short_answer: 'Short Answer',
      coding: 'Coding',
    };
    return labels[type] || type;
  };

  return (
    <>
      <div className="card border-0 shadow-sm rounded-4 mb-4" id="question-bank-panel">
        {/* Header */}
        <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
          <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
            <div>
              <button
                id="btn-back-to-exams"
                className="btn btn-sm btn-light rounded-3 mb-2"
                onClick={onBack}
              >
                <i className="bi bi-arrow-left me-1" />
                Back to Exams
              </button>
              <h5 className="fw-bold mb-1">
                <i className="bi bi-patch-question text-primary me-2" />
                Question Bank
              </h5>
              <p className="text-muted small mb-0">
                Exam: <strong>{exam?.title}</strong> &nbsp;·&nbsp; {questions.length} question
                {questions.length !== 1 ? 's' : ''}
              </p>
            </div>
            <button
              id="btn-add-question"
              className="btn btn-primary d-flex align-items-center gap-2 rounded-3 px-4"
              onClick={() => {
                setEditingQuestion(null);
                setShowModal(true);
              }}
            >
              <i className="bi bi-plus-lg" />
              Add Question
            </button>
          </div>
        </div>

        {/* Success Banner */}
        {successMessage && (
          <div className="mx-4 mt-3">
            <div className="alert alert-success alert-dismissible fade show border-0 rounded-3 py-2 small">
              <i className="bi bi-check-circle-fill me-2" />
              {successMessage}
              <button type="button" className="btn-close" onClick={clearMessages} />
            </div>
          </div>
        )}

        <div className="card-body p-0">
          {loadingQuestions ? (
            <div className="p-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="placeholder-glow p-3 rounded-3 border mb-2">
                  <span className="placeholder col-8 mb-2 d-block" />
                  <span className="placeholder col-4" />
                </div>
              ))}
            </div>
          ) : questionsError ? (
            <div className="alert alert-danger m-4 border-0 rounded-3">
              <i className="bi bi-exclamation-triangle-fill me-2" />
              {questionsError}
            </div>
          ) : questions.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <i className="bi bi-patch-question-fill display-4 d-block mb-3 opacity-30" />
              <h6 className="fw-semibold">No questions yet</h6>
              <p className="small mb-3">Add your first question to this exam.</p>
              <button
                className="btn btn-primary rounded-3"
                onClick={() => {
                  setEditingQuestion(null);
                  setShowModal(true);
                }}
              >
                <i className="bi bi-plus me-1" /> Add Question
              </button>
            </div>
          ) : (
            <div className="p-4 pt-3">
              {questions.map((q, index) => (
                <div
                  key={q.id}
                  className="border rounded-4 mb-3 overflow-hidden"
                  id={`question-item-${q.id}`}
                >
                  {/* Question Header Row */}
                  <div
                    className="d-flex align-items-start gap-3 p-3 bg-light cursor-pointer"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setExpandedId(expandedId === q.id ? null : q.id)}
                  >
                    <div
                      className="d-flex align-items-center justify-content-center bg-primary text-white rounded-3 fw-bold flex-shrink-0"
                      style={{ width: 36, height: 36, fontSize: 14 }}
                    >
                      {index + 1}
                    </div>
                    <div className="flex-grow-1 min-w-0">
                      <p className="mb-1 fw-semibold text-dark text-truncate" style={{ maxWidth: '100%' }}>
                        {q.question_text || q.text}
                      </p>
                      <div className="d-flex flex-wrap gap-2">
                        <span className={`badge bg-${DIFFICULTY_COLOR[q.difficulty] || 'secondary'}-subtle text-${DIFFICULTY_COLOR[q.difficulty] || 'secondary'} rounded-pill`}>
                          {q.difficulty || 'medium'}
                        </span>
                        <span className="badge bg-primary-subtle text-primary rounded-pill">
                          <i className={`${TYPE_ICON[q.question_type || q.type] || 'bi-question'} me-1`} />
                          {typeLabel(q.question_type || q.type)}
                        </span>
                        <span className="badge bg-secondary-subtle text-secondary rounded-pill">
                          {q.marks || 1} mark{q.marks !== 1 ? 's' : ''}
                        </span>
                      </div>
                    </div>
                    <div className="d-flex gap-1 flex-shrink-0">
                      <button
                        id={`btn-edit-question-${q.id}`}
                        className="btn btn-sm btn-light rounded-3"
                        title="Edit question"
                        onClick={(e) => { e.stopPropagation(); handleEdit(q); }}
                      >
                        <i className="bi bi-pencil" />
                      </button>
                      <button
                        id={`btn-delete-question-${q.id}`}
                        className="btn btn-sm btn-outline-danger rounded-3"
                        title="Delete question"
                        onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(q.id); }}
                        disabled={actionLoading}
                      >
                        <i className="bi bi-trash" />
                      </button>
                      <button
                        className="btn btn-sm btn-light rounded-3"
                        onClick={(e) => { e.stopPropagation(); setExpandedId(expandedId === q.id ? null : q.id); }}
                      >
                        <i className={`bi ${expandedId === q.id ? 'bi-chevron-up' : 'bi-chevron-down'}`} />
                      </button>
                    </div>
                  </div>

                  {/* Delete Confirmation */}
                  {confirmDeleteId === q.id && (
                    <div className="px-3 pb-3 bg-danger-subtle border-top border-danger-subtle">
                      <p className="small mb-2 text-danger fw-semibold pt-2">
                        <i className="bi bi-exclamation-triangle me-1" />
                        Delete this question?
                      </p>
                      <div className="d-flex gap-2">
                        <button
                          className="btn btn-danger btn-sm rounded-3"
                          onClick={() => handleDelete(q.id)}
                          disabled={actionLoading}
                        >
                          {actionLoading ? <span className="spinner-border spinner-border-sm" /> : 'Delete'}
                        </button>
                        <button
                          className="btn btn-secondary btn-sm rounded-3"
                          onClick={() => setConfirmDeleteId(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Expanded Options */}
                  {expandedId === q.id && q.options?.length > 0 && (
                    <div className="px-4 pb-3 pt-2 bg-white border-top">
                      <p className="small fw-semibold text-muted mb-2">Options:</p>
                      {q.options.map((opt, oi) => (
                        <div
                          key={oi}
                          className={`d-flex align-items-center gap-2 mb-1 small p-2 rounded-3 ${
                            opt.is_correct ? 'bg-success-subtle text-success fw-semibold' : 'bg-light'
                          }`}
                        >
                          <i className={`bi ${opt.is_correct ? 'bi-check-circle-fill' : 'bi-circle'}`} />
                          {opt.text || opt}
                        </div>
                      ))}
                      {q.explanation && (
                        <div className="mt-2 p-2 bg-info-subtle rounded-3 small text-info">
                          <i className="bi bi-lightbulb me-1" />
                          <strong>Explanation:</strong> {q.explanation}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Question Form Modal */}
      {showModal && (
        <QuestionFormModal
          exam={exam}
          question={editingQuestion}
          onClose={handleCloseModal}
        />
      )}
    </>
  );
};

export default QuestionBankPanel;
