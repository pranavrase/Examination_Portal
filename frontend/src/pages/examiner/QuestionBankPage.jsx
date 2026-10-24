import React, { useState, useEffect, useCallback } from 'react';
import CategoryFilterSidebar from '../../components/examiner/questionBank/CategoryFilterSidebar';
import QuestionBankList from '../../components/examiner/questionBank/QuestionBankList';
import MCQQuestionForm from '../../components/examiner/questionBank/MCQQuestionForm';
import CodingQuestionForm from '../../components/examiner/questionBank/CodingQuestionForm';
import BulkImportModal from '../../components/examiner/questionBank/BulkImportModal';

import {
  getQuestions,
  createQuestion,
  updateQuestion,
  deleteQuestion,
  importQuestions,
} from '../../api/questionApi';

const QuestionBankPage = () => {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters & Pagination state
  const [filters, setFilters] = useState({
    category: '',
    topic: '',
    difficulty: '',
    question_type: '',
    search: '',
  });

  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 15,
    totalPages: 1,
  });

  // Modal controls
  const [showMCQModal, setShowMCQModal] = useState(false);
  const [showCodingModal, setShowCodingModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [deletingQuestion, setDeletingQuestion] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Toast notification state
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch Questions from API
  const fetchQuestionBank = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        ...filters,
        page: pagination.page,
        page_size: pagination.page_size,
      };
      const res = await getQuestions(params);

      // Handle backend array or paginated object response structure
      // Backend returns: { items, page, page_size, total }
      if (Array.isArray(res)) {
        setQuestions(res);
        setPagination((prev) => ({ ...prev, totalPages: 1 }));
      } else if (res && typeof res === 'object') {
        const items = res.items || res.questions || res.data || [];
        setQuestions(items);
        const total = res.total || 0;
        const pageSize = res.page_size || pagination.page_size || 15;
        const totalPages = total > 0 ? Math.ceil(total / pageSize) : 1;
        setPagination((prev) => ({
          ...prev,
          totalPages,
        }));
      }
    } catch (err) {
      console.warn('Failed to load question bank from backend:', err);
      setError(err?.response?.data?.detail || 'Failed to connect to question bank API.');
      setQuestions([]);
    } finally {
      setLoading(false);
    }
  }, [filters, pagination.page, pagination.limit]);

  useEffect(() => {
    fetchQuestionBank();
  }, [fetchQuestionBank]);

  const handleFilterChange = (newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  const handleResetFilters = () => {
    setFilters({
      category: '',
      topic: '',
      difficulty: '',
      question_type: '',
      search: '',
    });
    setPagination((prev) => ({ ...prev, page: 1 }));
  };

  const handlePageChange = (newPage) => {
    setPagination((prev) => ({ ...prev, page: newPage }));
  };

  // ── Open Create Modals ────────────────────────────────────────────────────────
  const handleOpenAddMCQ = () => {
    setSelectedQuestion(null);
    setShowMCQModal(true);
  };

  const handleOpenAddCoding = () => {
    setSelectedQuestion(null);
    setShowCodingModal(true);
  };

  const handleOpenEdit = (q) => {
    setSelectedQuestion(q);
    if (q.question_type?.toLowerCase() === 'coding') {
      setShowCodingModal(true);
    } else {
      setShowMCQModal(true);
    }
  };

  // ── Save Question Handler ─────────────────────────────────────────────────────
  const handleSaveQuestion = async (questionData) => {
    if (selectedQuestion?.id) {
      const updated = await updateQuestion(selectedQuestion.id, questionData);
      showToast('Question updated successfully!');
      setQuestions((prev) => prev.map((q) => (q.id === selectedQuestion.id ? { ...q, ...questionData, ...updated } : q)));
    } else {
      const created = await createQuestion(questionData);
      showToast('New question created successfully!');
      setQuestions((prev) => [created, ...prev]);
    }
    fetchQuestionBank();
  };

  // ── Delete Question Handler ───────────────────────────────────────────────────
  const handleDeleteConfirm = async () => {
    if (!deletingQuestion) return;
    try {
      setDeleting(true);
      await deleteQuestion(deletingQuestion.id);
      showToast('Question deleted successfully.', 'danger');
      setQuestions((prev) => prev.filter((q) => q.id !== deletingQuestion.id));
      setDeletingQuestion(null);
    } catch (err) {
      showToast(err?.response?.data?.detail || 'Failed to delete question.', 'danger');
    } finally {
      setDeleting(false);
    }
  };

  // ── Bulk Import Handler ───────────────────────────────────────────────────────
  const handleBulkImport = async (formData, previewRows) => {
    try {
      await importQuestions(formData);
      showToast(`Successfully imported ${previewRows.length} questions!`);
      fetchQuestionBank();
    } catch (err) {
      showToast(err?.response?.data?.detail || 'Bulk import failed.', 'danger');
    }
  };

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Toast Notification Banner */}
      {toast && (
        <div
          className={`alert alert-${toast.type} alert-dismissible fade show position-fixed top-0 end-0 m-3 shadow-lg rounded-3`}
          style={{ zIndex: 1080, minWidth: '300px' }}
        >
          <div className="d-flex align-items-center gap-2">
            <i className={`bi ${toast.type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'}`}></i>
            <span>{toast.message}</span>
          </div>
          <button type="button" className="btn-close" onClick={() => setToast(null)}></button>
        </div>
      )}

      {/* Header Bar */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-2">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-warning text-dark text-uppercase tracking-wider">Examiner Hub</span>
            <span className="badge bg-light text-secondary border">{questions.length} Items</span>
          </div>
          <h1 className="h3 mb-0 fw-bold">Question Bank Management</h1>
          <p className="text-muted mb-0 small">Create, organize, filter, and import Aptitude, Reasoning, Technical, and Coding questions</p>
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="row g-4">
        {/* Left Sidebar Filter */}
        <div className="col-12 col-lg-3">
          <CategoryFilterSidebar
            filters={filters}
            onFilterChange={handleFilterChange}
            onResetFilters={handleResetFilters}
          />
        </div>

        {/* Right Main Table / Cards Content */}
        <div className="col-12 col-lg-9">
          <QuestionBankList
            questions={questions}
            loading={loading}
            error={error}
            filters={filters}
            pagination={pagination}
            onFilterChange={handleFilterChange}
            onPageChange={handlePageChange}
            onOpenAddMCQ={handleOpenAddMCQ}
            onOpenAddCoding={handleOpenAddCoding}
            onOpenImport={() => setShowImportModal(true)}
            onEditQuestion={handleOpenEdit}
            onDeleteQuestion={(q) => setDeletingQuestion(q)}
          />
        </div>
      </div>

      {/* MCQ Question Form Modal */}
      <MCQQuestionForm
        show={showMCQModal}
        onClose={() => setShowMCQModal(false)}
        onSave={handleSaveQuestion}
        initialData={selectedQuestion}
      />

      {/* Coding Question Form Modal */}
      <CodingQuestionForm
        show={showCodingModal}
        onClose={() => setShowCodingModal(false)}
        onSave={handleSaveQuestion}
        initialData={selectedQuestion}
      />

      {/* Bulk Import Modal */}
      <BulkImportModal
        show={showImportModal}
        onClose={() => setShowImportModal(false)}
        onImport={handleBulkImport}
      />

      {/* Delete Confirmation Modal */}
      {deletingQuestion && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 rounded-4 shadow">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold text-danger">Delete Question?</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setDeletingQuestion(null)}
                  disabled={deleting}
                ></button>
              </div>
              <div className="modal-body">
                <p>Are you sure you want to delete question <strong>#{deletingQuestion.id}</strong>?</p>
                <div className="bg-light p-3 rounded-3 border small text-dark mb-2 font-monospace">
                  "{deletingQuestion.question_text || deletingQuestion.text}"
                </div>
                <p className="text-muted small mb-0">This action cannot be undone.</p>
              </div>
              <div className="modal-footer border-top-0 pt-0">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  onClick={() => setDeletingQuestion(null)}
                  disabled={deleting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={handleDeleteConfirm}
                  disabled={deleting}
                >
                  {deleting ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Deleting...</>
                  ) : (
                    'Delete Question'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuestionBankPage;
