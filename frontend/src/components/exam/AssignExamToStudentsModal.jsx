import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useExam } from '../../context/ExamContext';

const AssignExamToStudentsModal = ({ show, onClose }) => {
  const { currentExam, assignExam, actionLoading, actionError } = useExam();
  const [localError, setLocalError] = useState(null);
  const [mode, setMode] = useState('list'); // 'list' (email list) or 'batch'

  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    defaultValues: {
      student_emails: '',
      scheduled_start: '',
      scheduled_end: ''
    }
  });

  if (!show || !currentExam) return null;

  const onSubmit = async (data) => {
    setLocalError(null);
    try {
      // The backend expects an array of strings (emails or IDs) or a specific DTO
      // We'll parse the comma separated emails.
      const emails = data.student_emails
        .split(',')
        .map(e => e.trim())
        .filter(e => e);

      if (emails.length === 0) {
        setLocalError('Please provide at least one student email.');
        return;
      }

      const payload = {
        student_emails: emails,
        scheduled_start: data.scheduled_start || null,
        scheduled_end: data.scheduled_end || null
      };

      await assignExam(currentExam.id, payload);
      reset();
      onClose();
    } catch (err) {
      setLocalError(err.message || 'Failed to assign exam');
    }
  };

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content border-0 rounded-4 shadow">
          <div className="modal-header border-bottom-0 pb-0">
            <h5 className="modal-title fw-bold">Assign "{currentExam.title}"</h5>
            <button type="button" className="btn-close" onClick={onClose} disabled={actionLoading}></button>
          </div>
          
          <div className="modal-body">
            {(actionError || localError) && (
              <div className="alert alert-danger py-2 px-3 small rounded-3">
                <i className="bi bi-exclamation-triangle-fill me-2"></i>
                {localError || actionError}
              </div>
            )}

            <form id="assignForm" onSubmit={handleSubmit(onSubmit)}>
              <div className="mb-4">
                <label className="form-label fw-semibold">Student Emails <span className="text-danger">*</span></label>
                <textarea
                  className={`form-control ${errors.student_emails ? 'is-invalid' : ''}`}
                  rows="3"
                  placeholder="student1@example.com, student2@example.com"
                  disabled={actionLoading}
                  {...register('student_emails', { 
                    required: 'Please provide at least one email' 
                  })}
                ></textarea>
                <div className="form-text">Enter comma-separated email addresses of the students.</div>
                {errors.student_emails && <div className="invalid-feedback">{errors.student_emails.message}</div>}
              </div>

              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label fw-semibold">Scheduled Start (Optional)</label>
                  <input
                    type="datetime-local"
                    className="form-control"
                    disabled={actionLoading}
                    {...register('scheduled_start')}
                  />
                </div>
                <div className="col-md-6">
                  <label className="form-label fw-semibold">Scheduled End (Optional)</label>
                  <input
                    type="datetime-local"
                    className="form-control"
                    disabled={actionLoading}
                    {...register('scheduled_end')}
                  />
                </div>
              </div>
            </form>
          </div>
          
          <div className="modal-footer border-top-0 pt-0">
            <button 
              type="button" 
              className="btn btn-outline-secondary" 
              onClick={onClose}
              disabled={actionLoading}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              form="assignForm"
              className="btn btn-primary"
              disabled={actionLoading}
            >
              {actionLoading ? (
                <><span className="spinner-border spinner-border-sm me-2"></span>Assigning...</>
              ) : (
                'Assign Students'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssignExamToStudentsModal;
