import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useExam } from '../../context/ExamContext';

const ExamSettingsPanel = () => {
  const { currentExam, updateExam, actionLoading } = useExam();
  
  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm({
    defaultValues: {
      duration: 60,
      total_marks: 100,
      passing_percentage: 40,
      negative_marking: 0,
      randomize_questions: false,
      randomize_options: false
    }
  });

  useEffect(() => {
    if (currentExam) {
      reset({
        duration: currentExam.duration || currentExam.duration_minutes || 60,
        total_marks: currentExam.total_marks || 100,
        passing_percentage: currentExam.passing_percentage || 40,
        negative_marking: currentExam.negative_marking || 0,
        randomize_questions: !!currentExam.randomize_questions,
        randomize_options: !!currentExam.randomize_options
      });
    }
  }, [currentExam, reset]);

  const onSubmit = async (data) => {
    if (!currentExam) return;
    try {
      // Parse numeric fields
      const formattedData = {
        ...data,
        duration: parseInt(data.duration, 10),
        total_marks: parseFloat(data.total_marks),
        passing_percentage: parseFloat(data.passing_percentage),
        negative_marking: parseFloat(data.negative_marking)
      };
      await updateExam(currentExam.id, formattedData);
      reset(formattedData);
    } catch (err) {
      // Error is displayed globally or handled by context
    }
  };

  const isPublished = currentExam?.status === 'published';

  return (
    <div className="card shadow-sm border-0 rounded-4 h-100">
      <div className="card-header bg-white border-bottom p-4">
        <h5 className="mb-0 fw-bold">Exam Settings</h5>
      </div>
      <div className="card-body p-4">
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="row g-3 mb-4">
            <div className="col-md-6">
              <label className="form-label fw-semibold text-muted small text-uppercase">Duration (minutes)</label>
              <input
                type="number"
                className={`form-control ${errors.duration ? 'is-invalid' : ''}`}
                disabled={isPublished || actionLoading}
                {...register('duration', { 
                  required: 'Required',
                  min: { value: 1, message: 'Must be > 0' }
                })}
              />
              {errors.duration && <div className="invalid-feedback">{errors.duration.message}</div>}
            </div>
            
            <div className="col-md-6">
              <label className="form-label fw-semibold text-muted small text-uppercase">Total Marks</label>
              <input
                type="number"
                step="0.5"
                className={`form-control ${errors.total_marks ? 'is-invalid' : ''}`}
                disabled={isPublished || actionLoading}
                {...register('total_marks', { 
                  required: 'Required',
                  min: { value: 1, message: 'Must be > 0' }
                })}
              />
              {errors.total_marks && <div className="invalid-feedback">{errors.total_marks.message}</div>}
            </div>

            <div className="col-md-6">
              <label className="form-label fw-semibold text-muted small text-uppercase">Passing Percentage (%)</label>
              <div className="input-group">
                <input
                  type="number"
                  step="0.1"
                  className={`form-control ${errors.passing_percentage ? 'is-invalid' : ''}`}
                  disabled={isPublished || actionLoading}
                  {...register('passing_percentage', { 
                    required: 'Required',
                    min: { value: 0, message: '0-100' },
                    max: { value: 100, message: '0-100' }
                  })}
                />
                <span className="input-group-text">%</span>
                {errors.passing_percentage && <div className="invalid-feedback">{errors.passing_percentage.message}</div>}
              </div>
            </div>

            <div className="col-md-6">
              <label className="form-label fw-semibold text-muted small text-uppercase">Negative Marking Ratio</label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g., 0.25"
                className={`form-control ${errors.negative_marking ? 'is-invalid' : ''}`}
                disabled={isPublished || actionLoading}
                {...register('negative_marking', { 
                  min: { value: 0, message: 'Cannot be negative' },
                  max: { value: 1, message: 'Usually between 0 and 1' }
                })}
              />
              {errors.negative_marking && <div className="invalid-feedback">{errors.negative_marking.message}</div>}
            </div>
          </div>

          <div className="mb-4">
            <h6 className="fw-semibold mb-3">Randomization</h6>
            <div className="form-check form-switch mb-2">
              <input 
                className="form-check-input" 
                type="checkbox" 
                id="randomizeQuestions"
                disabled={isPublished || actionLoading}
                {...register('randomize_questions')}
              />
              <label className="form-check-label" htmlFor="randomizeQuestions">
                Randomize Questions (Order)
              </label>
            </div>
            <div className="form-check form-switch">
              <input 
                className="form-check-input" 
                type="checkbox" 
                id="randomizeOptions"
                disabled={isPublished || actionLoading}
                {...register('randomize_options')}
              />
              <label className="form-check-label" htmlFor="randomizeOptions">
                Randomize Options (MCQs)
              </label>
            </div>
          </div>

          <div className="d-flex justify-content-end">
            <button 
              type="submit" 
              className="btn btn-outline-primary"
              disabled={!isDirty || isPublished || actionLoading}
            >
              {actionLoading ? 'Saving...' : 'Update Settings'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ExamSettingsPanel;
