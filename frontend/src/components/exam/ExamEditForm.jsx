import React, { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useExam } from '../../context/ExamContext';

const ExamEditForm = () => {
  const { currentExam, updateExam, actionLoading, actionError, successMsg, clearMessages } = useExam();
  
  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm({
    defaultValues: {
      title: '',
      description: ''
    }
  });

  useEffect(() => {
    if (currentExam) {
      reset({
        title: currentExam.title || '',
        description: currentExam.description || ''
      });
    }
  }, [currentExam, reset]);

  // Clear messages on unmount
  useEffect(() => {
    return () => clearMessages();
  }, [clearMessages]);

  const onSubmit = async (data) => {
    if (!currentExam) return;
    try {
      await updateExam(currentExam.id, data);
      reset(data); // reset form to new clean state
    } catch (err) {
      // Error handled by context
    }
  };

  const isPublished = currentExam?.status === 'published';

  return (
    <div className="card shadow-sm border-0 rounded-4 h-100">
      <div className="card-header bg-white border-bottom p-4">
        <h5 className="mb-0 fw-bold">Basic Information</h5>
      </div>
      <div className="card-body p-4">
        {actionError && (
          <div className="alert alert-danger rounded-3 py-2 px-3 small">
            {actionError}
          </div>
        )}
        {successMsg && !isDirty && (
          <div className="alert alert-success rounded-3 py-2 px-3 small">
            {successMsg}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="mb-3">
            <label className="form-label fw-semibold">Exam Title <span className="text-danger">*</span></label>
            <input
              type="text"
              className={`form-control ${errors.title ? 'is-invalid' : ''}`}
              disabled={isPublished || actionLoading}
              {...register('title', { 
                required: 'Exam title is required',
                maxLength: { value: 100, message: 'Title must not exceed 100 characters' }
              })}
            />
            {errors.title && <div className="invalid-feedback">{errors.title.message}</div>}
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold">Description</label>
            <textarea
              className={`form-control ${errors.description ? 'is-invalid' : ''}`}
              rows="4"
              disabled={isPublished || actionLoading}
              {...register('description', {
                maxLength: { value: 500, message: 'Description must not exceed 500 characters' }
              })}
            ></textarea>
            {errors.description && <div className="invalid-feedback">{errors.description.message}</div>}
          </div>

          <div className="d-flex justify-content-end">
            <button 
              type="submit" 
              className="btn btn-primary"
              disabled={!isDirty || isPublished || actionLoading}
            >
              {actionLoading ? (
                <><span className="spinner-border spinner-border-sm me-2"></span>Saving...</>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ExamEditForm;
