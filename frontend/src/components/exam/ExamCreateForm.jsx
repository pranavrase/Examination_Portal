import React from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { useExam } from '../../context/ExamContext';

const INSTRUCTION_PRESETS = [
  {
    label: 'Standard Rules',
    icon: 'bi-card-checklist',
    text: `1. Ensure a stable internet connection before starting.\n2. Do not refresh or minimize the browser window during the test.\n3. Keep track of the remaining time displayed on the timer.\n4. Review all answers before submitting.`,
  },
  {
    label: 'Coding & Proctoring',
    icon: 'bi-shield-check',
    text: `1. Fullscreen mode is enforced. Tab switching will trigger security violations.\n2. Do not use external code editors or unauthorized assistance.\n3. Ensure your code passes all test cases before final submission.`,
  },
  {
    label: 'Negative Marking',
    icon: 'bi-exclamation-octagon',
    text: `1. Incorrect answers carry negative marking.\n2. Only answer questions you are confident about; unattempted questions have no penalty.\n3. Save and verify answers carefully.`,
  },
];

const ExamCreateForm = () => {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm({
    defaultValues: {
      title: '',
      description: '',
      instructions: INSTRUCTION_PRESETS[0].text,
      status: 'published',
      assign_all_students: true,
    },
  });

  const { createExam, actionLoading, actionError } = useExam();
  const navigate = useNavigate();
  const watchedInstructions = watch('instructions');

  const onSubmit = async (data) => {
    try {
      const payload = {
        title: data.title,
        description: data.description,
        instructions: data.instructions,
        status: data.status || 'published',
        assign_all_students: true,
      };
      const newExam = await createExam(payload);
      if (newExam && newExam.id) {
        navigate(`/exams/${newExam.id}/edit`);
      }
    } catch (err) {
      // Error is handled by context
    }
  };

  return (
    <div className="card shadow-sm border-0 rounded-4">
      <div className="card-header bg-white border-bottom p-4">
        <h5 className="mb-0 fw-bold">Create New Examination</h5>
      </div>
      <div className="card-body p-4">
        {actionError && (
          <div className="alert alert-danger rounded-3">
            <i className="bi bi-exclamation-triangle-fill me-2"></i>
            {actionError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="mb-3">
            <label className="form-label fw-semibold">
              Exam Title <span className="text-danger">*</span>
            </label>
            <input
              type="text"
              className={`form-control ${errors.title ? 'is-invalid' : ''}`}
              placeholder="e.g., Final Year Aptitude & Technical Assessment"
              {...register('title', {
                required: 'Exam title is required',
                maxLength: { value: 100, message: 'Title must not exceed 100 characters' },
              })}
            />
            {errors.title && <div className="invalid-feedback">{errors.title.message}</div>}
          </div>

          <div className="mb-3">
            <label className="form-label fw-semibold">Description</label>
            <textarea
              className={`form-control ${errors.description ? 'is-invalid' : ''}`}
              rows="3"
              placeholder="Provide general context or overview for the exam..."
              {...register('description', {
                maxLength: { value: 500, message: 'Description must not exceed 500 characters' },
              })}
            ></textarea>
            {errors.description && <div className="invalid-feedback">{errors.description.message}</div>}
          </div>

          {/* Candidate Instructions Section */}
          <div className="card border-info border-opacity-25 bg-info bg-opacity-10 p-3 rounded-3 mb-4">
            <div className="d-flex justify-content-between align-items-center mb-2">
              <label className="form-label fw-bold text-info mb-0 d-flex align-items-center gap-1.5">
                <i className="bi bi-card-checklist"></i> Candidate Instructions & Rules
              </label>
              <span className="badge bg-info text-dark rounded-pill">Shown in Student Lobby</span>
            </div>
            <p className="text-muted small mb-2">
              These guidelines are displayed to the candidate on the exam lobby screen before they start.
            </p>

            <div className="d-flex flex-wrap gap-2 mb-2">
              {INSTRUCTION_PRESETS.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="btn btn-xs btn-outline-secondary rounded-pill bg-white py-1 px-2.5 small"
                  onClick={() => setValue('instructions', preset.text)}
                >
                  <i className={`bi ${preset.icon} me-1 text-primary`}></i>
                  {preset.label}
                </button>
              ))}
            </div>

            <textarea
              className="form-control bg-white font-monospace small"
              rows="4"
              placeholder="Enter guidelines or select a preset template above..."
              {...register('instructions')}
            />

            {watchedInstructions && (
              <div className="mt-2 p-2 bg-white rounded border small text-secondary">
                <div className="fw-semibold text-muted text-uppercase" style={{ fontSize: '0.7rem' }}>
                  Live Preview:
                </div>
                <div style={{ whiteSpace: 'pre-line' }}>{watchedInstructions}</div>
              </div>
            )}
          </div>

          <div className="d-flex justify-content-end gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={() => navigate('/exams')}
              disabled={actionLoading}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary px-4" disabled={actionLoading}>
              {actionLoading ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2"></span>Creating...
                </>
              ) : (
                'Create Exam'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ExamCreateForm;
