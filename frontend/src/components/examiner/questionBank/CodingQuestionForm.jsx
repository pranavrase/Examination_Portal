import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import TestCaseEditor from './TestCaseEditor';

const LANGUAGES = [
  { id: 'python', name: 'Python 3' },
  { id: 'cpp', name: 'C++ 17' },
  { id: 'java', name: 'Java 11' },
  { id: 'javascript', name: 'Node.js (JS)' },
  { id: 'c', name: 'C' },
];

const CodingQuestionForm = ({ show, onClose, onSave, initialData = null }) => {
  const [serverError, setServerError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [testCases, setTestCases] = useState([]);
  const [selectedLangs, setSelectedLangs] = useState(['python', 'cpp', 'java', 'javascript']);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({
    defaultValues: {
      category: 'Coding',
      topic: '',
      difficulty: 'Medium',
      question_type: 'coding',
      question_text: '',
      constraints: '',
      marks: 10,
      time_limit: 2,
      memory_limit: 256,
    },
  });

  useEffect(() => {
    if (initialData) {
      const topicName = (typeof initialData.category === 'object' && initialData.category !== null ? initialData.category.topic : null)
        || initialData.topic
        || '';
      const diffVal = (typeof initialData.category === 'object' && initialData.category !== null ? initialData.category.difficulty : null)
        || initialData.difficulty
        || 'Medium';
      const capitalizedDiff = diffVal ? diffVal.charAt(0).toUpperCase() + diffVal.slice(1).toLowerCase() : 'Medium';

      reset({
        category: 'Coding',
        topic: topicName,
        difficulty: ['Easy', 'Medium', 'Hard'].includes(capitalizedDiff) ? capitalizedDiff : 'Medium',
        question_type: 'coding',
        question_text: initialData.question_text || initialData.text || initialData.coding_details?.problem_statement || '',
        constraints: initialData.coding_details?.constraints || initialData.constraints || '',
        marks: initialData.marks || 10,
        time_limit: initialData.coding_details?.time_limit_ms ? (initialData.coding_details.time_limit_ms / 1000) : (initialData.time_limit || 2),
        memory_limit: initialData.coding_details?.memory_limit_kb ? Math.round(initialData.coding_details.memory_limit_kb / 1024) : (initialData.memory_limit || 256),
      });
      setTestCases(initialData.coding_details?.test_cases || initialData.test_cases || []);
      setSelectedLangs(initialData.coding_details?.allowed_languages || initialData.allowed_languages || ['python', 'cpp', 'java', 'javascript']);
    } else {
      reset({
        category: 'Coding',
        topic: '',
        difficulty: 'Medium',
        question_type: 'coding',
        question_text: '',
        constraints: '',
        marks: 10,
        time_limit: 2,
        memory_limit: 256,
      });
      setTestCases([]);
      setSelectedLangs(['python', 'cpp', 'java', 'javascript']);
    }
    setServerError(null);
  }, [initialData, reset, show]);

  if (!show) return null;

  const handleLangToggle = (langId) => {
    if (selectedLangs.includes(langId)) {
      if (selectedLangs.length === 1) {
        alert('At least one programming language must be selected.');
        return;
      }
      setSelectedLangs(selectedLangs.filter((l) => l !== langId));
    } else {
      setSelectedLangs([...selectedLangs, langId]);
    }
  };

  const onSubmit = async (data) => {
    setServerError(null);

    if (testCases.length === 0) {
      setServerError('Please add at least one test case for this coding question.');
      return;
    }

    try {
      setSubmitting(true);
      await onSave({
        ...data,
        category_id: initialData?.category_id || (typeof initialData?.category === 'object' ? initialData.category?.id : undefined),
        marks: parseFloat(data.marks),
        problem_statement: data.question_text,
        time_limit_ms: Math.round(parseFloat(data.time_limit) * 1000),
        memory_limit_kb: parseInt(data.memory_limit, 10) * 1024,
        allowed_languages: selectedLangs,
        test_cases: testCases,
      });
      onClose();
    } catch (err) {
      setServerError(err.message || err?.response?.data?.detail || 'Failed to save coding question.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
      <div className="modal-dialog modal-dialog-centered modal-xl">
        <div className="modal-content border-0 rounded-4 shadow">
          <div className="modal-header border-bottom-0 pb-0">
            <h5 className="modal-title fw-bold">
              <i className="bi bi-code-square me-2 text-danger"></i>
              {initialData ? 'Edit Coding Question' : 'Add Coding Question'}
            </h5>
            <button type="button" className="btn-close" onClick={onClose} disabled={submitting}></button>
          </div>

          <div className="modal-body p-4" style={{ maxHeight: '80vh', overflowY: 'auto' }}>
            {serverError && (
              <div className="alert alert-danger py-2 px-3 small rounded-3 mb-3">
                <i className="bi bi-exclamation-triangle-fill me-2"></i>
                {serverError}
              </div>
            )}

            <form id="codingForm" onSubmit={handleSubmit(onSubmit)}>
              {/* Category, Topic, Difficulty, Marks */}
              <div className="row g-3 mb-3">
                <div className="col-md-3">
                  <label className="form-label small fw-bold">Category</label>
                  <input type="text" className="form-control form-control-sm bg-light" value="Coding" readOnly />
                </div>
                <div className="col-md-3">
                  <label className="form-label small fw-bold">Topic <span className="text-danger">*</span></label>
                  <input
                    type="text"
                    className={`form-control form-control-sm ${errors.topic ? 'is-invalid' : ''}`}
                    placeholder="e.g. Dynamic Programming, Strings"
                    {...register('topic', { required: 'Topic is required' })}
                  />
                </div>
                <div className="col-md-3">
                  <label className="form-label small fw-bold">Difficulty <span className="text-danger">*</span></label>
                  <select className="form-select form-select-sm" {...register('difficulty')}>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="Hard">Hard</option>
                  </select>
                </div>
                <div className="col-md-3">
                  <label className="form-label small fw-bold">Marks <span className="text-danger">*</span></label>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    className={`form-control form-control-sm ${errors.marks ? 'is-invalid' : ''}`}
                    {...register('marks', { required: true, min: 1 })}
                  />
                </div>
              </div>

              {/* Problem Statement */}
              <div className="mb-3">
                <label className="form-label small fw-bold">Problem Statement <span className="text-danger">*</span></label>
                <textarea
                  className={`form-control ${errors.question_text ? 'is-invalid' : ''}`}
                  rows="4"
                  placeholder="Describe the coding challenge statement, input format, and output format..."
                  {...register('question_text', { required: 'Problem statement is required' })}
                ></textarea>
                {errors.question_text && <div className="invalid-feedback">{errors.question_text.message}</div>}
              </div>

              {/* Constraints */}
              <div className="mb-4">
                <label className="form-label small fw-bold">Constraints</label>
                <textarea
                  className="form-control form-control-sm font-monospace"
                  rows="2"
                  placeholder="e.g. 1 <= N <= 10^5&#10;1 <= A[i] <= 10^9"
                  {...register('constraints')}
                ></textarea>
              </div>

              {/* Languages & Limits */}
              <div className="row g-3 mb-4">
                <div className="col-md-6">
                  <label className="form-label small fw-bold">Allowed Languages</label>
                  <div className="d-flex flex-wrap gap-2 pt-1">
                    {LANGUAGES.map((lang) => {
                      const isChecked = selectedLangs.includes(lang.id);
                      return (
                        <button
                          key={lang.id}
                          type="button"
                          className={`btn btn-sm ${
                            isChecked ? 'btn-outline-primary active fw-bold' : 'btn-light text-muted'
                          }`}
                          onClick={() => handleLangToggle(lang.id)}
                        >
                          <i className={`bi ${isChecked ? 'bi-check-square-fill me-1' : 'bi-square me-1'}`}></i>
                          {lang.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="col-md-3">
                  <label className="form-label small fw-bold">Time Limit (sec)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0.5"
                    max="10"
                    className="form-control form-control-sm"
                    {...register('time_limit', { required: true })}
                  />
                </div>

                <div className="col-md-3">
                  <label className="form-label small fw-bold">Memory Limit (MB)</label>
                  <input
                    type="number"
                    step="16"
                    min="64"
                    max="1024"
                    className="form-control form-control-sm"
                    {...register('memory_limit', { required: true })}
                  />
                </div>
              </div>

              {/* Test Cases Editor */}
              <TestCaseEditor testCases={testCases} onChange={setTestCases} />
            </form>
          </div>

          <div className="modal-footer border-top-0 pt-0">
            <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" form="codingForm" className="btn btn-primary" disabled={submitting}>
              {submitting ? (
                <><span className="spinner-border spinner-border-sm me-2"></span>Saving...</>
              ) : (
                'Save Coding Question'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodingQuestionForm;
