import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axiosInstance from '../../api/axiosInstance';
import { useAuth } from '../../context/AuthContext';

const StudentExamLobbyPage = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [exam, setExam] = useState(null);
  const [attemptInfo, setAttemptInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [acknowledged, setAcknowledged] = useState(false);

  useEffect(() => {
    const fetchExamDetails = async () => {
      setLoading(true);
      setError(null);
      try {
        let examData;
        try {
          const res = await axiosInstance.get(`/exams/${examId}`);
          examData = res.data;
        } catch (initialErr) {
          // Fallback to student-specific exam detail endpoint
          const res = await axiosInstance.get(`/students/exams/${examId}`);
          examData = res.data;
        }
        setExam(examData);

        // Fetch authoritative attempt status directly from backend
        try {
          const attRes = await axiosInstance.get(`/exams/${examId}/my-attempt`);
          if (attRes?.data) {
            setAttemptInfo(attRes.data);
          }
        } catch (attErr) {
          console.warn('Could not fetch student attempt status:', attErr);
        }
      } catch (err) {
        console.warn('Failed to fetch exam lobby info:', err);
        setError(err?.response?.data?.detail || 'Exam details unavailable or unauthorized.');
        setExam(null);
      } finally {
        setLoading(false);
      }
    };

    if (examId) {
      fetchExamDetails();
    }
  }, [examId]);

  const handleStartExam = async () => {
    if (isCompleted || !acknowledged) return;

    // Trigger full-screen mode immediately on user click
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen().catch(() => { });
      } else if (elem.webkitRequestFullscreen) {
        await elem.webkitRequestFullscreen().catch(() => { });
      } else if (elem.mozRequestFullScreen) {
        await elem.mozRequestFullScreen().catch(() => { });
      } else if (elem.msRequestFullscreen) {
        await elem.msRequestFullscreen().catch(() => { });
      }
    } catch (_) { }

    // Route to coding / interactive examination room
    navigate(`/student/exam/${examId}/coding`);
  };

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading exam...</span>
        </div>
        <p className="text-muted mt-3 small">Loading assessment instructions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container py-5">
        <div className="alert alert-danger rounded-4 p-4 text-center">
          <i className="bi bi-exclamation-triangle-fill fs-2 d-block mb-2"></i>
          <h5>Unable to Access Examination</h5>
          <p className="small mb-3">{error}</p>
          <Link to="/student" className="btn btn-outline-secondary btn-sm">
            <i className="bi bi-arrow-left me-1"></i> Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const duration = exam?.duration_minutes || exam?.settings?.duration_minutes || exam?.duration || 60;
  const marks = exam?.total_marks || exam?.settings?.total_marks || 100;
  const passPct = exam?.passing_percentage || exam?.settings?.passing_percentage || 40;
  const candidateInstructions = exam?.instructions || (exam?.description?.includes('[INSTRUCTIONS]') ? exam.description.split('[INSTRUCTIONS]')[1]?.trim() : null);

  const isCompleted = Boolean(
    attemptInfo?.is_completed ||
    attemptInfo?.status === 'submitted' ||
    attemptInfo?.status === 'auto_submitted' ||
    exam?.is_completed ||
    exam?.attempt_status === 'submitted' ||
    exam?.attempt_status === 'auto_submitted'
  );
  const effectiveAttemptId = attemptInfo?.attempt_id || exam?.attempt_id || examId;
  const effectiveAttemptStatus = attemptInfo?.status || exam?.attempt_status || 'submitted';
  const submittedAt = attemptInfo?.submitted_at || null;

  return (
    <div className="container py-4">
      {/* Back link */}
      <div className="mb-3">
        <Link to="/student" className="text-decoration-none text-muted small d-inline-flex align-items-center gap-1 hover-primary">
          <i className="bi bi-arrow-left"></i> Back to Student Dashboard
        </Link>
      </div>

      <div className="card shadow-sm border-0 rounded-4 overflow-hidden mb-4">
        {/* Header banner */}
        <div className="card-header bg-dark text-white p-4 p-md-5 border-bottom border-secondary border-opacity-25" style={{ background: 'linear-gradient(135deg, #0b0f19 0%, #1e1b4b 50%, #172554 100%)' }}>
          <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span className="badge bg-primary bg-opacity-25 text-primary-emphasis border border-primary border-opacity-50 text-uppercase tracking-wider">
              Assessment Lobby
            </span>
            {isCompleted ? (
              <span className="badge bg-warning bg-opacity-25 text-warning border border-warning border-opacity-50">
                <i className="bi bi-lock-fill me-1"></i> Exam Completed / Locked
              </span>
            ) : (
              <>
                <span className="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50">
                  <i className="bi bi-shield-lock-fill me-1"></i> Secure Environment
                </span>
                <span className="badge bg-info bg-opacity-25 text-info border border-info border-opacity-50">
                  <i className="bi bi-arrows-fullscreen me-1"></i> Fullscreen Enforced
                </span>
              </>
            )}
          </div>
          <h2 className="fw-bold mb-2 text-white">{exam?.title || 'Examination'}</h2>
          <p className="text-white-50 mb-0" style={{ maxWidth: '700px' }}>
            {exam?.description?.replace(/\[INSTRUCTIONS\].*$/s, '').trim() || 'Please review the official instructions, rules, and hardware guidelines before launching your test session.'}
          </p>
        </div>

        {/* Quick parameters grid */}
        <div className="card-body p-4 p-md-5">
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <div className="p-3 bg-light rounded-3 border text-center h-100">
                <div className="text-muted small mb-1">Time Limit</div>
                <div className="fw-bold fs-5 text-dark"><i className="bi bi-stopwatch text-primary me-1"></i>{duration} Mins</div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="p-3 bg-light rounded-3 border text-center h-100">
                <div className="text-muted small mb-1">Total Marks</div>
                <div className="fw-bold fs-5 text-dark"><i className="bi bi-award text-success me-1"></i>{marks} Marks</div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="p-3 bg-light rounded-3 border text-center h-100">
                <div className="text-muted small mb-1">Pass Criteria</div>
                <div className="fw-bold fs-5 text-dark"><i className="bi bi-graph-up text-info me-1"></i>{passPct}% Min</div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="p-3 bg-light rounded-3 border text-center h-100">
                <div className="text-muted small mb-1">Negative Marking</div>
                <div className="fw-bold fs-5 text-dark">
                  <i className="bi bi-info-circle text-warning me-1"></i>
                  {exam?.negative_marking ? `${exam.negative_marking} Penalty` : 'None'}
                </div>
              </div>
            </div>
          </div>

          {/* Examiner Candidate Instructions (if present) */}
          {candidateInstructions && (
            <div className="card border-primary border-opacity-25 bg-primary bg-opacity-10 p-4 rounded-4 mb-4">
              <h5 className="fw-bold text-primary mb-2 d-flex align-items-center gap-2">
                <i className="bi bi-megaphone-fill"></i> Instructions from Examiner
              </h5>
              <div className="small text-dark" style={{ whiteSpace: 'pre-line', lineHeight: '1.6' }}>
                {candidateInstructions}
              </div>
            </div>
          )}

          {/* Guidelines Section */}
          <div className="mb-4">
            <h5 className="fw-bold text-dark mb-3"><i className="bi bi-card-checklist text-primary me-2"></i>Examination Rules & Anti-Cheating Guidelines</h5>
            <ul className="list-group list-group-flush border rounded-3 small">
              <li className="list-group-item d-flex align-items-start gap-2 py-2.5">
                <i className="bi bi-arrows-fullscreen text-primary mt-0.5"></i>
                <div><strong>Fullscreen Mode Required:</strong> The examination will launch in full-screen mode. Leaving or minimizing full-screen will be recorded as a proctoring infraction.</div>
              </li>
              <li className="list-group-item d-flex align-items-start gap-2 py-2.5">
                <i className="bi bi-check2-circle text-primary mt-0.5"></i>
                <div><strong>Continuous Timer:</strong> Once started, the countdown timer runs continuously and will automatically submit when time expires.</div>
              </li>
              <li className="list-group-item d-flex align-items-start gap-2 py-2.5">
                <i className="bi bi-check2-circle text-primary mt-0.5"></i>
                <div><strong>Auto-Saving:</strong> Your chosen options and coding solutions are automatically saved and synced to the cloud.</div>
              </li>
              <li className="list-group-item d-flex align-items-start gap-2 py-2.5">
                <i className="bi bi-shield-exclamation text-warning mt-0.5"></i>
                <div><strong>Strict Proctoring Policy:</strong> Tab switches, window blurring, and external application focus will trigger immediate warnings and lead to auto-termination.</div>
              </li>
            </ul>
          </div>

          {/* Completed / Submitted Lock Card or Launch Form */}
          {isCompleted ? (
            <div className="card border-success border-opacity-50 bg-success bg-opacity-10 p-4 rounded-4 mb-4 text-center shadow-sm">
              <div
                className="d-inline-flex align-items-center justify-content-center bg-success text-white rounded-circle mb-3 mx-auto shadow-sm"
                style={{ width: '56px', height: '56px' }}
              >
                <i className="bi bi-shield-check fs-2"></i>
              </div>
              <h4 className="fw-bold text-success mb-2">Exam Already Submitted</h4>
              <p className="text-secondary small mb-3 mx-auto" style={{ maxWidth: '540px' }}>
                You have already completed and finalized this examination. Re-entry, retaking, or restarting is permanently locked. You can view your performance, evaluated answers, and detailed scorecard below.
              </p>
              <div className="d-flex flex-wrap justify-content-center gap-2 mb-4">
                <span className="badge bg-success bg-opacity-25 text-success border border-success border-opacity-50 px-3 py-2 rounded-pill small">
                  Status: {effectiveAttemptStatus === 'auto_submitted' ? 'Auto-Submitted (Timer / Security)' : 'Submitted & Finalized'}
                </span>
                {effectiveAttemptId && (
                  <span className="badge bg-dark bg-opacity-50 text-white border border-secondary border-opacity-25 px-3 py-2 rounded-pill small">
                    Attempt #{effectiveAttemptId}
                  </span>
                )}
                {submittedAt && (
                  <span className="badge bg-dark bg-opacity-50 text-white border border-secondary border-opacity-25 px-3 py-2 rounded-pill small">
                    Submitted: {new Date(submittedAt).toLocaleString()}
                  </span>
                )}
              </div>
              <div className="d-flex flex-column flex-sm-row align-items-center justify-content-center gap-3">
                <Link
                  id="btn-view-result-lobby"
                  to={`/results/${effectiveAttemptId}`}
                  className="btn btn-success px-4 py-2 rounded-3 fw-semibold d-inline-flex align-items-center gap-2 shadow-sm"
                >
                  <i className="bi bi-file-earmark-bar-graph-fill"></i>
                  <span>View Result / Scorecard</span>
                </Link>
                <Link to="/student" className="btn btn-outline-secondary px-3 py-2 rounded-3">
                  <i className="bi bi-arrow-left me-1"></i> Return to Dashboard
                </Link>
              </div>
            </div>
          ) : (
            <>
              {/* Acknowledgement Checkbox */}
              <div className="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 mb-4">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    id="ackCheck"
                    checked={acknowledged}
                    onChange={(e) => setAcknowledged(e.target.checked)}
                  />
                  <label className="form-check-label small fw-semibold text-dark user-select-none" htmlFor="ackCheck">
                    I understand that this assessment runs in strict full-screen mode. I agree to abide by all anti-cheat rules and launch my test session.
                  </label>
                </div>
              </div>

              {/* Action Row */}
              <div className="d-flex flex-column flex-sm-row align-items-center justify-content-between gap-3">
                <Link to="/student" className="btn btn-outline-secondary btn-sm px-3 rounded-3 order-2 order-sm-1">
                  Cancel & Return
                </Link>
                <button
                  id="btn-start-exam-lobby"
                  className="btn btn-primary rounded-3 px-4 py-2 fw-semibold d-flex align-items-center gap-2 order-1 order-sm-2"
                  disabled={!acknowledged}
                  onClick={handleStartExam}
                >
                  <i className="bi bi-arrows-fullscreen fs-6"></i>
                  <span>Launch Fullscreen Assessment</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentExamLobbyPage;
