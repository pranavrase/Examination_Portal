import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';

const MCQQuestionForm = ({ show, onClose, onSave, initialData = null }) => {
  const [serverError, setServerError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      category: 'Aptitude',
      topic: '',
      difficulty: 'Medium',
      question_type: 'mcq',
      question_text: '',
      marks: 1,
      options: [
        { text: '', is_correct: false },
        { text: '', is_correct: false },
        { text: '', is_correct: false },
        { text: '', is_correct: false },
      ],
      explanation: '',
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'options',
  });

  const watchedOptions = watch('options');

  useEffect(() => {
    if (initialData) {
      const rawOptions = initialData.mcq_options || initialData.options || [];
      const opts = rawOptions && rawOptions.length > 0
        ? rawOptions.map((o) => typeof o === 'string' ? { text: o, is_correct: false } : { text: o.option_text || o.text || '', is_correct: !!o.is_correct })
        : [
            { text: '', is_correct: false },
            { text: '', is_correct: false },
            { text: '', is_correct: false },
            { text: '', is_correct: false },
          ];

      const catName = typeof initialData.category === 'object' && initialData.category !== null
        ? (initialData.category.name || 'Aptitude')
        : (initialData.category || 'Aptitude');

      const topicName = (typeof initialData.category === 'object' && initialData.category !== null ? initialData.category.topic : null)
        || initialData.topic
        || '';

      const diffVal = (typeof initialData.category === 'object' && initialData.category !== null ? initialData.category.difficulty : null)
        || initialData.difficulty
        || 'Medium';

      const capitalizedCat = catName ? catName.charAt(0).toUpperCase() + catName.slice(1).toLowerCase() : 'Aptitude';
      const capitalizedDiff = diffVal ? diffVal.charAt(0).toUpperCase() + diffVal.slice(1).toLowerCase() : 'Medium';

      reset({
        category: ['Aptitude', 'Reasoning', 'Technical'].includes(capitalizedCat) ? capitalizedCat : 'Aptitude',
        topic: topicName,
        difficulty: ['Easy', 'Medium', 'Hard'].includes(capitalizedDiff) ? capitalizedDiff : 'Medium',
        question_type: 'mcq',
        question_text: initialData.question_text || initialData.text || '',
        marks: initialData.marks || 1,
        options: opts,
        explanation: initialData.explanation || '',
      });
    } else {
      reset({
        category: 'Aptitude',
        topic: '',
        difficulty: 'Medium',
        question_type: 'mcq',
        question_text: '',
        marks: 1,
        options: [
          { text: '', is_correct: false },
          { text: '', is_correct: false },
          { text: '', is_correct: false },
          { text: '', is_correct: false },
        ],
        explanation: '',
      });
    }
    setServerError(null);
  }, [initialData, reset, show]);

  if (!show) return null;

  const handleSelectCorrectRadio = (selectedIndex) => {
    watchedOptions.forEach((_, idx) => {
      setValue(`options.${idx}.is_correct`, idx === selectedIndex);
    });
  };

  const onSubmit = async (data) => {
    setServerError(null);

    // Validate at least one option is marked correct
    const hasCorrect = data.options.some((opt) => opt.is_correct);
    if (!hasCorrect) {
      setServerError('Please select at least one option as the correct answer.');
      return;
    }

    // Validate options are non-empty
    const emptyOption = data.options.some((opt) => !opt.text.trim());
    if (emptyOption) {
      setServerError('All options must have non-empty text.');
      return;
    }

    try {
      setSubmitting(true);
      await onSave({
        ...data,
        category_id: initialData?.category_id || (typeof initialData?.category === 'object' ? initialData.category?.id : undefined),
        marks: parseFloat(data.marks),
        options: data.options.map((opt) => ({
          option_text: opt.text,
          text: opt.text,
          is_correct: opt.is_correct,
        })),
      });
      onClose();
    } catch (err) {
      setServerError(err.message || err?.response?.data?.detail || 'Failed to save question.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content border-0 rounded-4 shadow">
          <div className="modal-header border-bottom-0 pb-0">
            <h5 className="modal-title fw-bold">
              <i className="bi bi-ui-radios me-2 text-primary"></i>
              {initialData ? 'Edit MCQ Question' : 'Add MCQ Question'}
            </h5>
            <button type="button" className="btn-close" onClick={onClose} disabled={submitting}></button>
          </div>

          <div className="modal-body p-4">
            {serverError && (
              <div className="alert alert-danger py-2 px-3 small rounded-3 mb-3">
                <i className="bi bi-exclamation-triangle-fill me-2"></i>
                {serverError}
              </div>
            )}

            <form id="mcqForm" onSubmit={handleSubmit(onSubmit)}>
              {/* Category, Topic, Difficulty, Marks */}
              <div className="row g-3 mb-3">
                <div className="col-md-3">
                  <label className="form-label small fw-bold">Category <span className="text-danger">*</span></label>
                  <select className="form-select form-select-sm" {...register('category', { required: true })}>
                    <option value="Aptitude">Aptitude</option>
                    <option value="Reasoning">Reasoning</option>
                    <option value="Technical">Technical</option>
                  </select>
                </div>
                <div className="col-md-3">
                  <label className="form-label small fw-bold">Topic <span className="text-danger">*</span></label>
                  <input
                    type="text"
                    className={`form-control form-control-sm ${errors.topic ? 'is-invalid' : ''}`}
                    placeholder="e.g. Profit & Loss"
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
                    step="0.5"
                    min="0.5"
                    className={`form-control form-control-sm ${errors.marks ? 'is-invalid' : ''}`}
                    {...register('marks', { required: true, min: 0.5 })}
                  />
                </div>
              </div>

              {/* Question Text */}
              <div className="mb-4">
                <label className="form-label small fw-bold">Question Statement <span className="text-danger">*</span></label>
                <textarea
                  className={`form-control ${errors.question_text ? 'is-invalid' : ''}`}
                  rows="3"
                  placeholder="Enter the complete question text..."
                  {...register('question_text', { required: 'Question text is required' })}
                ></textarea>
                {errors.question_text && <div className="invalid-feedback">{errors.question_text.message}</div>}
              </div>

              {/* Options */}
              <div className="mb-4">
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <label className="form-label small fw-bold mb-0">
                    Options & Correct Answer Selection <span className="text-danger">*</span>
                  </label>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary py-0"
                    onClick={() => append({ text: '', is_correct: false })}
                  >
                    <i className="bi bi-plus"></i> Add Option
                  </button>
                </div>

                <div className="d-flex flex-column gap-2">
                  {fields.map((field, index) => {
                    const isCorrect = watchedOptions?.[index]?.is_correct;
                    return (
                      <div key={field.id} className="input-group">
                        <div className="input-group-text bg-light">
                          <input
                            className="form-check-input mt-0"
                            type="radio"
                            name="correct_option_radio"
                            checked={!!isCorrect}
                            onChange={() => handleSelectCorrectRadio(index)}
                            title="Mark as correct answer"
                          />
                        </div>
                        <span className="input-group-text bg-white fw-bold text-muted small" style={{ minWidth: '40px' }}>
                          {String.fromCharCode(65 + index)}
                        </span>
                        <input
                          type="text"
                          className={`form-control ${isCorrect ? 'border-success bg-success bg-opacity-10 fw-semibold' : ''}`}
                          placeholder={`Option ${String.fromCharCode(65 + index)} text...`}
                          {...register(`options.${index}.text`, { required: true })}
                        />
                        {fields.length > 2 && (
                          <button
                            type="button"
                            className="btn btn-outline-danger"
                            onClick={() => remove(index)}
                            title="Remove option"
                          >
                            <i className="bi bi-trash"></i>
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="form-text small mt-1">
                  Select the radio button next to the option that represents the correct answer.
                </div>
              </div>

              {/* Explanation */}
              <div className="mb-3">
                <label className="form-label small fw-bold">Explanation / Solution (Optional)</label>
                <textarea
                  className="form-control form-control-sm"
                  rows="2"
                  placeholder="Explain why the answer is correct for candidates..."
                  {...register('explanation')}
                ></textarea>
              </div>
            </form>
          </div>

          <div className="modal-footer border-top-0 pt-0">
            <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" form="mcqForm" className="btn btn-primary" disabled={submitting}>
              {submitting ? (
                <><span className="spinner-border spinner-border-sm me-2"></span>Saving...</>
              ) : (
                'Save MCQ Question'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MCQQuestionForm;
