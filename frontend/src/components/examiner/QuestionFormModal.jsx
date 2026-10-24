import React, { useEffect, useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { useExaminer } from '../../context/ExaminerContext';

const QUESTION_TYPES = ['mcq', 'true_false', 'short_answer', 'coding'];
const DIFFICULTY_LEVELS = ['easy', 'medium', 'hard'];

const QuestionFormModal = ({ exam, question, onClose }) => {
  const { addQuestion, editQuestion, actionLoading, actionError } = useExaminer();
  const isEdit = Boolean(question);

  const defaultOptions = question?.options?.length
    ? question.options.map((o) => ({ text: o.text || o, is_correct: o.is_correct || false }))
    : [
        { text: '', is_correct: true },
        { text: '', is_correct: false },
        { text: '', is_correct: false },
        { text: '', is_correct: false },
      ];

  const {
    register,
    handleSubmit,
    watch,
    control,
    reset,
    formState: { errors },
  } = useForm({
    defaultValues: {
      question_text: question?.question_text || question?.text || '',
      question_type: question?.question_type || question?.type || 'mcq',
      difficulty: question?.difficulty || 'medium',
      marks: question?.marks || 1,
      negative_marks: question?.negative_marks || 0,
      explanation: question?.explanation || '',
      options: defaultOptions,
      correct_answer: question?.correct_answer || '',
      code_template: question?.code_template || '',
      expected_output: question?.expected_output || '',
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: 'options' });
  const questionType = watch('question_type');

  const onSubmit = async (data) => {
    try {
      // Clean options for non-MCQ types
      const payload = { ...data };
      if (data.question_type !== 'mcq' && data.question_type !== 'true_false') {
        delete payload.options;
      }
      if (isEdit) {
        await editQuestion(exam.id, question.id, payload);
      } else {
        await addQuestion(exam.id, payload);
      }
      onClose();
    } catch (_) {}
  };

  const isMcqType = questionType === 'mcq' || questionType === 'true_false';

  return (
    <div
      className="modal d-block"
      tabIndex="-1"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
      id="question-form-modal"
    >
      <div className="modal-dialog modal-lg modal-dialog-scrollable modal-dialog-centered">
        <div className="modal-content border-0 shadow rounded-4">
          <div className="modal-header border-0 pb-0 px-4 pt-4">
            <div>
              <span className="badge bg-primary text-white mb-2">
                {isEdit ? 'EDIT QUESTION' : 'ADD QUESTION'}
              </span>
              <h5 className="modal-title fw-bold mb-0">
                {isEdit ? 'Edit Question' : `Add Question to: ${exam?.title}`}
              </h5>
            </div>
            <button type="button" className="btn-close ms-auto" onClick={onClose} />
          </div>

          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="modal-body px-4 pt-3">
              {actionError && (
                <div className="alert alert-danger border-0 rounded-3 py-2 small mb-3">
                  <i className="bi bi-exclamation-triangle-fill me-2" />
                  {actionError}
                </div>
              )}

              <div className="row g-3">
                {/* Question Text */}
                <div className="col-12">
                  <label className="form-label fw-semibold small">
                    Question Text <span className="text-danger">*</span>
                  </label>
                  <textarea
                    id="question-text-input"
                    className={`form-control rounded-3 ${errors.question_text ? 'is-invalid' : ''}`}
                    rows={3}
                    placeholder="Enter the question..."
                    {...register('question_text', {
                      required: 'Question text is required',
                      minLength: { value: 5, message: 'Minimum 5 characters' },
                    })}
                  />
                  {errors.question_text && (
                    <div className="invalid-feedback">{errors.question_text.message}</div>
                  )}
                </div>

                {/* Type, Difficulty, Marks */}
                <div className="col-md-4">
                  <label className="form-label fw-semibold small">Question Type</label>
                  <select
                    id="question-type-select"
                    className="form-select rounded-3"
                    {...register('question_type')}
                  >
                    {QUESTION_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t === 'mcq' ? 'MCQ' : t === 'true_false' ? 'True / False' : t.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="form-label fw-semibold small">Difficulty</label>
                  <select
                    id="question-difficulty-select"
                    className="form-select rounded-3"
                    {...register('difficulty')}
                  >
                    {DIFFICULTY_LEVELS.map((d) => (
                      <option key={d} value={d}>
                        {d.charAt(0).toUpperCase() + d.slice(1)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-md-2">
                  <label className="form-label fw-semibold small">Marks</label>
                  <input
                    id="question-marks-input"
                    type="number"
                    className="form-control rounded-3"
                    min={0}
                    step={0.5}
                    {...register('marks', { min: 0 })}
                  />
                </div>
                <div className="col-md-2">
                  <label className="form-label fw-semibold small">Neg. Marks</label>
                  <input
                    id="question-negative-marks-input"
                    type="number"
                    className="form-control rounded-3"
                    min={0}
                    step={0.25}
                    {...register('negative_marks', { min: 0 })}
                  />
                </div>

                {/* MCQ / True-False Options */}
                {isMcqType && (
                  <div className="col-12">
                    <label className="form-label fw-semibold small">
                      Answer Options <span className="text-danger">*</span>
                    </label>
                    <div className="d-flex flex-column gap-2">
                      {fields.map((field, index) => (
                        <div key={field.id} className="d-flex align-items-center gap-2">
                          <div className="form-check mb-0">
                            <input
                              className="form-check-input"
                              type={questionType === 'mcq' ? 'radio' : 'checkbox'}
                              id={`option-correct-${index}`}
                              value={index}
                              {...register(`options.${index}.is_correct`)}
                            />
                          </div>
                          <input
                            id={`option-text-${index}`}
                            type="text"
                            className="form-control form-control-sm rounded-3"
                            placeholder={`Option ${String.fromCharCode(65 + index)}`}
                            {...register(`options.${index}.text`, { required: true })}
                          />
                          {questionType === 'mcq' && fields.length > 2 && (
                            <button
                              type="button"
                              className="btn btn-sm btn-outline-danger rounded-3"
                              onClick={() => remove(index)}
                            >
                              <i className="bi bi-x" />
                            </button>
                          )}
                        </div>
                      ))}
                      {questionType === 'mcq' && fields.length < 6 && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-secondary rounded-3 align-self-start"
                          onClick={() => append({ text: '', is_correct: false })}
                        >
                          <i className="bi bi-plus me-1" />
                          Add Option
                        </button>
                      )}
                    </div>
                    <div className="form-text">
                      <i className="bi bi-info-circle me-1" />
                      Select the radio button next to the correct answer.
                    </div>
                  </div>
                )}

                {/* Short Answer */}
                {questionType === 'short_answer' && (
                  <div className="col-12">
                    <label className="form-label fw-semibold small">Correct Answer</label>
                    <input
                      id="question-correct-answer-input"
                      type="text"
                      className="form-control rounded-3"
                      placeholder="Expected correct answer..."
                      {...register('correct_answer')}
                    />
                  </div>
                )}

                {/* Coding */}
                {questionType === 'coding' && (
                  <>
                    <div className="col-12">
                      <label className="form-label fw-semibold small">Code Template (starter code)</label>
                      <textarea
                        id="question-code-template"
                        className="form-control rounded-3 font-monospace"
                        rows={4}
                        placeholder="def solution(n):\n    # Write your code here\n    pass"
                        {...register('code_template')}
                      />
                    </div>
                    <div className="col-12">
                      <label className="form-label fw-semibold small">Expected Output</label>
                      <textarea
                        id="question-expected-output"
                        className="form-control rounded-3 font-monospace"
                        rows={3}
                        placeholder="Expected output for test cases..."
                        {...register('expected_output')}
                      />
                    </div>
                  </>
                )}

                {/* Explanation */}
                <div className="col-12">
                  <label className="form-label fw-semibold small">
                    Explanation <span className="text-muted small fw-normal">(shown after submission)</span>
                  </label>
                  <textarea
                    id="question-explanation-input"
                    className="form-control rounded-3"
                    rows={2}
                    placeholder="Explanation for the correct answer..."
                    {...register('explanation')}
                  />
                </div>
              </div>
            </div>

            <div className="modal-footer border-0 px-4 pb-4">
              <button
                type="button"
                className="btn btn-light rounded-3 px-4"
                onClick={onClose}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                id="btn-save-question"
                type="submit"
                className="btn btn-primary rounded-3 px-4 d-flex align-items-center gap-2"
                disabled={actionLoading}
              >
                {actionLoading ? (
                  <>
                    <span className="spinner-border spinner-border-sm" />
                    Saving...
                  </>
                ) : (
                  <>
                    <i className="bi bi-check-lg" />
                    {isEdit ? 'Save Changes' : 'Add Question'}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default QuestionFormModal;
