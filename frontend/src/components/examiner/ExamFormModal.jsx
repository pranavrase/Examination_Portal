import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useExaminer } from '../../context/ExaminerContext';
import { generateExamPaper } from '../../api/examinerApi';

const CATEGORIES = [
  { id: 'aptitude', label: 'Aptitude' },
  { id: 'reasoning', label: 'Logical Reasoning' },
  { id: 'technical', label: 'Technical Core' },
  { id: 'coding', label: 'Programming / Coding' },
  { id: 'mixed', label: 'Mixed Evaluation' },
];

const INSTRUCTION_PRESETS = [
  {
    label: 'Standard Assessment',
    icon: 'bi-card-checklist',
    text: `1. Ensure a stable internet connection and quiet environment before starting.\n2. Do not switch tabs, refresh, or minimize the browser window during the examination.\n3. Keep track of the countdown timer at the top of your screen.\n4. You can flag questions for review and return to them before final submission.\n5. Click "Submit Exam" once you have answered all questions or your time expires.`,
  },
  {
    label: 'Coding & Anti-Cheat',
    icon: 'bi-shield-check',
    text: `1. Fullscreen proctoring mode is strictly enforced. Leaving full-screen or switching applications triggers security violations.\n2. Only the integrated code editor and specified standard libraries are permitted.\n3. Ensure your code passes all custom and hidden test cases before advancing.\n4. Any form of plagiarism or external assistance will lead to automatic disqualification.`,
  },
  {
    label: 'Negative Marking Alert',
    icon: 'bi-exclamation-octagon',
    text: `1. This examination implements negative marking for incorrect answers.\n2. Carefully read each question before answering. Unattempted questions carry zero penalty.\n3. Make sure to confirm each selection before proceeding to subsequent sections.`,
  },
];

const ExamFormModal = ({ exam, onClose }) => {
  const { addExam, editExam, actionLoading, actionError } = useExaminer();
  const isEdit = Boolean(exam);
  const [activeTab, setActiveTab] = useState('config'); // 'config' | 'instructions' | 'paper_distribution'
  const [autoGenSuccess, setAutoGenSuccess] = useState(null);
  const [autoGenLoading, setAutoGenLoading] = useState(false);

  // Distribution states
  const [distAptitude, setDistAptitude] = useState(10);
  const [distReasoning, setDistReasoning] = useState(10);
  const [distTechnical, setDistTechnical] = useState(10);
  const [distCoding, setDistCoding] = useState(2);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm({
    defaultValues: {
      title: exam?.title || '',
      description: exam?.description || '',
      category: exam?.category || 'mixed',
      status: exam?.status || 'published',
      assign_all_students: true,
      duration_minutes: exam?.duration_minutes || exam?.settings?.duration_minutes || 60,
      total_marks: exam?.total_marks || exam?.settings?.total_marks || 100,
      passing_percentage: exam?.passing_percentage || exam?.settings?.passing_percentage || 40,
      negative_marking_ratio: exam?.negative_marking_ratio || exam?.settings?.negative_marking_ratio || 0.25,
      max_attempts: exam?.max_attempts || 1,
      randomize_questions: exam?.randomize_questions ?? exam?.settings?.randomize_questions ?? true,
      randomize_options: exam?.randomize_options ?? exam?.settings?.randomize_options ?? true,
      show_result_immediately: exam?.show_result_immediately ?? true,
      scheduled_start: exam?.scheduled_start || '',
      scheduled_end: exam?.scheduled_end || '',
      instructions: exam?.instructions || INSTRUCTION_PRESETS[0].text,
    },
  });

  const watchedInstructions = watch('instructions');

  useEffect(() => {
    if (exam) {
      reset({
        title: exam.title || '',
        description: exam.description || '',
        category: exam.category || 'mixed',
        status: exam.status || 'published',
        assign_all_students: true,
        duration_minutes: exam.duration_minutes || exam.settings?.duration_minutes || 60,
        total_marks: exam.total_marks || exam.settings?.total_marks || 100,
        passing_percentage: exam.passing_percentage || exam.settings?.passing_percentage || 40,
        negative_marking_ratio: exam.negative_marking_ratio || exam.settings?.negative_marking_ratio || 0.25,
        max_attempts: exam.max_attempts || 1,
        randomize_questions: exam.randomize_questions ?? exam.settings?.randomize_questions ?? true,
        randomize_options: exam.randomize_options ?? exam.settings?.randomize_options ?? true,
        show_result_immediately: exam.show_result_immediately ?? true,
        scheduled_start: exam.scheduled_start || '',
        scheduled_end: exam.scheduled_end || '',
        instructions: exam.instructions || INSTRUCTION_PRESETS[0].text,
      });
    }
  }, [exam, reset]);

  const onSubmit = async (data) => {
    try {
      const payload = {
        title: data.title,
        description: data.description,
        instructions: data.instructions,
        status: data.status || 'published',
        assign_all_students: Boolean(data.assign_all_students),
        settings: {
          duration_minutes: Number(data.duration_minutes),
          total_marks: Number(data.total_marks),
          passing_percentage: Number(data.passing_percentage),
          negative_marking_ratio: Number(data.negative_marking_ratio),
          randomize_questions: Boolean(data.randomize_questions),
          randomize_options: Boolean(data.randomize_options),
        },
      };

      let savedExam;
      if (isEdit) {
        savedExam = await editExam(exam.id, payload);
      } else {
        savedExam = await addExam(payload);
      }

      // If user configured automated paper distribution and exam has an ID
      if (savedExam?.id && (distAptitude > 0 || distReasoning > 0 || distTechnical > 0 || distCoding > 0)) {
        try {
          await generateExamPaper(savedExam.id, {
            aptitude_count: distAptitude,
            reasoning_count: distReasoning,
            technical_count: distTechnical,
            coding_count: distCoding,
          });
        } catch (_) { }
      }

      onClose();
    } catch (_) { }
  };

  const handleTriggerPaperAssembly = async () => {
    if (!exam?.id) return;
    try {
      setAutoGenLoading(true);
      setAutoGenSuccess(null);
      const res = await generateExamPaper(exam.id, {
        aptitude_count: distAptitude,
        reasoning_count: distReasoning,
        technical_count: distTechnical,
        coding_count: distCoding,
      });
      setAutoGenSuccess(res?.message || 'Exam paper successfully assembled!');
    } catch (err) {
      alert('Failed to assemble paper: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setAutoGenLoading(false);
    }
  };

  const totalQuestionsSum = Number(distAptitude) + Number(distReasoning) + Number(distTechnical) + Number(distCoding);

  return (
    <div
      className="modal d-block"
      tabIndex="-1"
      style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}
      id="exam-form-modal"
    >
      <div className="modal-dialog modal-lg modal-dialog-scrollable modal-dialog-centered">
        <div className="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
          {/* Header */}
          <div className="modal-header bg-dark text-white border-0 p-4">
            <div>
              <span className="badge bg-warning text-dark mb-1 text-uppercase fw-semibold">
                {isEdit ? 'Configure Examination' : 'New Examination Wizard'}
              </span>
              <h5 className="modal-title fw-bold mb-0 text-white">
                {isEdit ? `Edit: ${exam.title}` : 'Create New Examination'}
              </h5>
            </div>
            <button
              type="button"
              className="btn-close btn-close-white ms-auto"
              aria-label="Close"
              onClick={onClose}
            />
          </div>

          {/* Navigation Tabs */}
          <div className="bg-light px-4 pt-3 border-bottom d-flex gap-2 flex-wrap">
            <button
              type="button"
              className={`btn btn-sm pb-2 fw-semibold rounded-0 border-bottom border-3 transition-all ${activeTab === 'config' ? 'border-primary text-primary' : 'border-transparent text-muted'
                }`}
              onClick={() => setActiveTab('config')}
            >
              <i className="bi bi-sliders me-1.5" /> 1. Examination Setup
            </button>
            <button
              type="button"
              className={`btn btn-sm pb-2 fw-semibold rounded-0 border-bottom border-3 transition-all ${activeTab === 'instructions' ? 'border-primary text-primary' : 'border-transparent text-muted'
                }`}
              onClick={() => setActiveTab('instructions')}
            >
              <i className="bi bi-card-checklist me-1.5" /> 2. Candidate Instructions
            </button>
            <button
              type="button"
              className={`btn btn-sm pb-2 fw-semibold rounded-0 border-bottom border-3 transition-all ${activeTab === 'paper_distribution' ? 'border-primary text-primary' : 'border-transparent text-muted'
                }`}
              onClick={() => setActiveTab('paper_distribution')}
            >
              <i className="bi bi-grid-3x3-gap-fill me-1.5" /> 3. Question Distribution
            </button>
          </div>

          {/* Body */}
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="modal-body p-4" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
              {actionError && (
                <div className="alert alert-danger border-0 rounded-3 mb-4">
                  <i className="bi bi-exclamation-triangle-fill me-2" />
                  {actionError}
                </div>
              )}

              {autoGenSuccess && (
                <div className="alert alert-success border-0 rounded-3 mb-4">
                  <i className="bi bi-check-circle-fill me-2" />
                  {autoGenSuccess}
                </div>
              )}

              {/* ── TAB 1: Core Configuration ────────────────────────────── */}
              {activeTab === 'config' && (
                <div className="d-flex flex-column gap-3">
                  {/* Examination Name */}
                  <div>
                    <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                      Examination Name <span className="text-danger">*</span>
                    </label>
                    <input
                      type="text"
                      className={`form-control rounded-3 ${errors.title ? 'is-invalid' : ''}`}
                      placeholder="e.g. Aptitude & Technical Algorithms Assessment"
                      {...register('title', { required: 'Examination title is required' })}
                    />
                    {errors.title && (
                      <div className="invalid-feedback">{errors.title.message}</div>
                    )}
                  </div>

                  {/* Category & Duration */}
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Category
                      </label>
                      <select className="form-select rounded-3" {...register('category')}>
                        {CATEGORIES.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Duration (Minutes) <span className="text-danger">*</span>
                      </label>
                      <div className="input-group">
                        <input
                          type="number"
                          className="form-control rounded-start-3"
                          min="5"
                          max="360"
                          {...register('duration_minutes', { required: true, min: 5 })}
                        />
                        <span className="input-group-text bg-light rounded-end-3">mins</span>
                      </div>
                    </div>
                  </div>

                  {/* Total Marks & Passing Marks / Percentage */}
                  <div className="row g-3">
                    <div className="col-md-4">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Total Marks
                      </label>
                      <input
                        type="number"
                        className="form-control rounded-3"
                        min="1"
                        {...register('total_marks', { required: true, min: 1 })}
                      />
                    </div>
                    <div className="col-md-4">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Passing %
                      </label>
                      <div className="input-group">
                        <input
                          type="number"
                          className="form-control rounded-start-3"
                          min="0"
                          max="100"
                          {...register('passing_percentage', { required: true })}
                        />
                        <span className="input-group-text bg-light rounded-end-3">%</span>
                      </div>
                    </div>
                    <div className="col-md-4">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Negative Marking Ratio
                      </label>
                      <select className="form-select rounded-3" {...register('negative_marking_ratio')}>
                        <option value="0.0">No Negative Marking (0.0)</option>
                        <option value="0.25">0.25 (25% penalty)</option>
                        <option value="0.33">0.33 (33% penalty)</option>
                        <option value="0.5">0.50 (50% penalty)</option>
                        <option value="1.0">1.00 (100% penalty)</option>
                      </select>
                    </div>
                  </div>

                  {/* Scheduling (Start & End Date/Time) */}
                  <div className="row g-3">
                    <div className="col-md-6">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Scheduled Start Date/Time
                      </label>
                      <input
                        type="datetime-local"
                        className="form-control rounded-3"
                        {...register('scheduled_start')}
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                        Scheduled End Date/Time
                      </label>
                      <input
                        type="datetime-local"
                        className="form-control rounded-3"
                        {...register('scheduled_end')}
                      />
                    </div>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                      Description / Overview
                    </label>
                    <textarea
                      rows={2}
                      className="form-control rounded-3"
                      placeholder="Brief summary of the test scope and topics covered..."
                      {...register('description')}
                    />
                  </div>

                  {/* Candidate Instructions Quick Banner */}
                  <div className="card border-info border-opacity-25 bg-info bg-opacity-10 p-3 rounded-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <h6 className="fw-bold text-info mb-0 d-flex align-items-center gap-1.5">
                        <i className="bi bi-card-checklist"></i> Candidate Instructions & Rules
                      </h6>
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-info rounded-pill py-0 px-2 fw-semibold"
                        onClick={() => setActiveTab('instructions')}
                      >
                        Open Instructions Editor <i className="bi bi-arrow-right ms-1"></i>
                      </button>
                    </div>
                    <p className="text-muted small mb-2">
                      Instructions will be prominently shown to candidates on their lobby page before they start the test.
                    </p>
                    <textarea
                      rows={2}
                      className="form-control rounded-3 bg-white"
                      placeholder="Enter guidelines or click 'Open Instructions Editor' for templates..."
                      {...register('instructions')}
                    />
                  </div>

                  {/* Publication & Candidate Access */}
                  <div className="card border-primary border-opacity-25 bg-primary bg-opacity-10 p-3 rounded-3">
                    <h6 className="fw-bold text-primary mb-2 d-flex align-items-center gap-1.5">
                      <i className="bi bi-broadcast"></i> Student Portal Visibility & Publishing
                    </h6>
                    <div className="row g-3">
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                          Publication Status
                        </label>
                        <select className="form-select rounded-3 bg-white" {...register('status')}>
                          <option value="published">Active & Published (Visible in Student "My Exams")</option>
                          <option value="draft">Draft (Hidden from Students)</option>
                        </select>
                      </div>
                      <div className="col-md-6 d-flex align-items-center">
                        <div className="form-check form-switch pt-md-3">
                          <input
                            className="form-check-input"
                            type="checkbox"
                            id="assign_all_students"
                            {...register('assign_all_students')}
                          />
                          <label className="form-check-label small fw-semibold" htmlFor="assign_all_students">
                            Assign to all registered students
                          </label>
                          <div className="text-muted" style={{ fontSize: '0.75rem' }}>
                            Ensures students can view and start this exam immediately
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Toggles */}
                  <div className="p-3 bg-light rounded-3 d-flex flex-column gap-2">
                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="randomize_questions"
                        {...register('randomize_questions')}
                      />
                      <label className="form-check-label small fw-semibold" htmlFor="randomize_questions">
                        Randomize question sequence for each candidate
                      </label>
                    </div>
                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="randomize_options"
                        {...register('randomize_options')}
                      />
                      <label className="form-check-label small fw-semibold" htmlFor="randomize_options">
                        Randomize MCQ answer options (A, B, C, D)
                      </label>
                    </div>
                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id="show_result_immediately"
                        {...register('show_result_immediately')}
                      />
                      <label className="form-check-label small fw-semibold" htmlFor="show_result_immediately">
                        Enable instant result scorecard visibility after submission
                      </label>
                    </div>
                  </div>
                </div>
              )}

              {/* ── TAB 2: Candidate Instructions Dedicated Editor ──────── */}
              {activeTab === 'instructions' && (
                <div className="d-flex flex-column gap-3">
                  <div className="card border-primary border-opacity-25 bg-primary bg-opacity-10 p-3 rounded-3">
                    <div className="d-flex justify-content-between align-items-center">
                      <h6 className="fw-bold text-primary mb-0 d-flex align-items-center gap-2">
                        <i className="bi bi-info-circle-fill fs-5"></i>
                        Candidate Lobby Instructions
                      </h6>
                      <span className="badge bg-primary rounded-pill">Visible to Student</span>
                    </div>
                    <p className="text-muted small mb-0 mt-1">
                      These instructions and rules are displayed in the candidate's exam lobby right before they enter the exam environment.
                    </p>
                  </div>

                  {/* Quick Preset Templates */}
                  <div>
                    <label className="form-label fw-semibold small text-muted text-uppercase mb-2">
                      Load Quick Presets / Templates:
                    </label>
                    <div className="d-flex flex-wrap gap-2">
                      {INSTRUCTION_PRESETS.map((preset, idx) => (
                        <button
                          key={idx}
                          type="button"
                          className="btn btn-sm btn-outline-secondary rounded-pill d-flex align-items-center gap-1.5"
                          onClick={() => setValue('instructions', preset.text, { shouldDirty: true })}
                        >
                          <i className={`bi ${preset.icon} text-primary`}></i>
                          {preset.label}
                        </button>
                      ))}
                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger rounded-pill d-flex align-items-center gap-1.5 ms-auto"
                        onClick={() => setValue('instructions', '', { shouldDirty: true })}
                      >
                        <i className="bi bi-trash3"></i> Clear
                      </button>
                    </div>
                  </div>

                  {/* Textarea */}
                  <div>
                    <label className="form-label fw-semibold small text-muted text-uppercase mb-1">
                      Instructions Text
                    </label>
                    <textarea
                      rows={6}
                      className="form-control rounded-3 font-monospace small"
                      placeholder="Type exam instructions, code of conduct, timing rules..."
                      {...register('instructions')}
                    />
                    <div className="form-text small text-muted">
                      Numbered lines or bullet points will be formatted as clear guidelines on the student exam lobby.
                    </div>
                  </div>

                  {/* Live Candidate Preview */}
                  <div className="card border rounded-3 p-3 bg-light">
                    <div className="d-flex align-items-center gap-2 mb-2 pb-2 border-bottom">
                      <i className="bi bi-eye-fill text-muted"></i>
                      <span className="fw-bold small text-uppercase text-muted">Live Candidate Lobby Preview</span>
                    </div>
                    <div className="p-3 bg-white rounded-2 border">
                      <h6 className="fw-bold text-dark mb-2 d-flex align-items-center gap-2">
                        <i className="bi bi-card-checklist text-primary"></i>
                        Instructions from Examiner
                      </h6>
                      {watchedInstructions ? (
                        <div className="small text-secondary" style={{ whiteSpace: 'pre-line', lineHeight: '1.6' }}>
                          {watchedInstructions}
                        </div>
                      ) : (
                        <span className="text-muted fst-italic small">No specific instructions entered.</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* ── TAB 3: Question Distribution & Paper Assembler ────── */}
              {activeTab === 'paper_distribution' && (
                <div className="d-flex flex-column gap-3">
                  <div className="alert alert-info border-0 rounded-3 mb-3 small d-flex align-items-center gap-2">
                    <i className="bi bi-info-circle-fill fs-5" />
                    <span>
                      Define the topic-wise question distribution. The system will automatically select matching questions from the Question Bank into this exam paper.
                    </span>
                  </div>

                  <div className="card border p-3 rounded-3 mb-2">
                    <h6 className="fw-bold mb-3 d-flex justify-content-between align-items-center">
                      <span>Topic Distribution</span>
                      <span className="badge bg-primary rounded-pill">{totalQuestionsSum} Total Questions</span>
                    </h6>

                    <div className="row g-3">
                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-muted">Aptitude Questions</label>
                        <div className="input-group">
                          <span className="input-group-text bg-light"><i className="bi bi-calculator text-primary" /></span>
                          <input
                            type="number"
                            min="0"
                            max="50"
                            className="form-control"
                            value={distAptitude}
                            onChange={(e) => setDistAptitude(Math.max(0, parseInt(e.target.value) || 0))}
                          />
                        </div>
                      </div>

                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-muted">Logical Reasoning</label>
                        <div className="input-group">
                          <span className="input-group-text bg-light"><i className="bi bi-puzzle text-info" /></span>
                          <input
                            type="number"
                            min="0"
                            max="50"
                            className="form-control"
                            value={distReasoning}
                            onChange={(e) => setDistReasoning(Math.max(0, parseInt(e.target.value) || 0))}
                          />
                        </div>
                      </div>

                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-muted">Technical CS Core</label>
                        <div className="input-group">
                          <span className="input-group-text bg-light"><i className="bi bi-cpu text-warning" /></span>
                          <input
                            type="number"
                            min="0"
                            max="50"
                            className="form-control"
                            value={distTechnical}
                            onChange={(e) => setDistTechnical(Math.max(0, parseInt(e.target.value) || 0))}
                          />
                        </div>
                      </div>

                      <div className="col-md-6">
                        <label className="form-label small fw-semibold text-muted">Programming / Coding</label>
                        <div className="input-group">
                          <span className="input-group-text bg-light"><i className="bi bi-code-slash text-success" /></span>
                          <input
                            type="number"
                            min="0"
                            max="10"
                            className="form-control"
                            value={distCoding}
                            onChange={(e) => setDistCoding(Math.max(0, parseInt(e.target.value) || 0))}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {isEdit && (
                    <div className="d-flex justify-content-end">
                      <button
                        type="button"
                        className="btn btn-outline-primary btn-sm rounded-3 d-flex align-items-center gap-2"
                        onClick={handleTriggerPaperAssembly}
                        disabled={autoGenLoading}
                      >
                        {autoGenLoading ? (
                          <span className="spinner-border spinner-border-sm" />
                        ) : (
                          <i className="bi bi-magic" />
                        )}
                        Auto-Assemble Exam Paper Now
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="modal-footer border-0 bg-light p-3 px-4">
              <button
                type="button"
                className="btn btn-outline-secondary rounded-3 px-4"
                onClick={onClose}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
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
                    {isEdit ? 'Update Examination' : 'Create Examination'}
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

export default ExamFormModal;
