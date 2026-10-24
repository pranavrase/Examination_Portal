import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getResult } from '../../api/resultApi';
import ResultBreakdownChart from '../../components/results/ResultBreakdownChart';

// ── Helpers ──────────────────────────────────────────────────────────────────
const formatDate = (dateStr) => {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return isNaN(d.getTime())
    ? dateStr
    : d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const pct = (obtained, total) => {
  if (!total || total === 0) return null;
  return ((obtained / total) * 100).toFixed(1);
};

// ── Skeleton Loader ───────────────────────────────────────────────────────────
const SkeletonBlock = ({ height = '1rem', width = '100%', className = '' }) => (
  <div
    className={`rounded placeholder-glow ${className}`}
    style={{ height, width }}
  >
    <span className="placeholder w-100 h-100 rounded" />
  </div>
);

const ResultSkeleton = () => (
  <div className="container py-5" style={{ maxWidth: 820 }}>
    <SkeletonBlock height="2rem" width="60%" className="mb-4" />
    <div className="row g-3 mb-4">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="col-6 col-md-3">
          <SkeletonBlock height="90px" />
        </div>
      ))}
    </div>
    <SkeletonBlock height="240px" />
  </div>
);

// ── Status Badge ─────────────────────────────────────────────────────────────
const StatusBadge = ({ status }) => {
  const norm = (status || '').toLowerCase();
  const map = {
    passed: { cls: 'bg-success', icon: 'bi-trophy-fill', label: 'PASSED' },
    pass: { cls: 'bg-success', icon: 'bi-trophy-fill', label: 'PASSED' },
    failed: { cls: 'bg-danger', icon: 'bi-x-circle-fill', label: 'FAILED' },
    fail: { cls: 'bg-danger', icon: 'bi-x-circle-fill', label: 'FAILED' },
    pending: { cls: 'bg-warning text-dark', icon: 'bi-hourglass-split', label: 'PENDING' },
  };
  const cfg = map[norm] || { cls: 'bg-secondary', icon: 'bi-question-circle', label: status || 'UNKNOWN' };

  return (
    <span className={`badge ${cfg.cls} d-inline-flex align-items-center gap-2 px-3 py-2 rounded-3`} style={{ fontSize: '1rem' }}>
      <i className={`bi ${cfg.icon}`} />
      {cfg.label}
    </span>
  );
};

// ── Stat Card ─────────────────────────────────────────────────────────────────
const StatCard = ({ label, value, icon, accent = 'primary', sub = null }) => (
  <div className={`card border-0 shadow-sm rounded-4 h-100 border-start border-${accent} border-4`}>
    <div className="card-body py-3">
      <div className="d-flex align-items-start justify-content-between">
        <div>
          <p className="text-muted small fw-semibold mb-1 text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.06em' }}>
            {label}
          </p>
          <h4 className="fw-bold mb-0" style={{ lineHeight: 1 }}>{value ?? '—'}</h4>
          {sub && <p className="text-muted mb-0 mt-1" style={{ fontSize: '0.8rem' }}>{sub}</p>}
        </div>
        <div className={`text-${accent} opacity-50`} style={{ fontSize: '1.6rem' }}>
          <i className={`bi ${icon}`} />
        </div>
      </div>
    </div>
  </div>
);

// ── Detail Row ────────────────────────────────────────────────────────────────
const DetailRow = ({ label, value }) => {
  if (value === undefined || value === null || value === '') return null;
  return (
    <tr>
      <td className="text-muted small pe-4 py-2" style={{ whiteSpace: 'nowrap', width: '40%' }}>{label}</td>
      <td className="fw-semibold small py-2">{String(value)}</td>
    </tr>
  );
};

// ── Error State ───────────────────────────────────────────────────────────────
const ErrorState = ({ code, message, onRetry }) => {
  const messages = {
    401: 'You must be logged in to view this result.',
    403: 'You are not authorized to view this result.',
    404: 'Result not found. It may not have been calculated yet.',
    500: 'A server error occurred. Please try again later.',
  };
  return (
    <div className="container d-flex flex-column align-items-center justify-content-center py-5" style={{ minHeight: '60vh' }}>
      <i className="bi bi-exclamation-triangle-fill text-warning fs-1 mb-3" />
      <h5 className="fw-bold mb-2">{code ? `Error ${code}` : 'Something went wrong'}</h5>
      <p className="text-muted text-center mb-4" style={{ maxWidth: 400 }}>
        {messages[code] || message || 'An unexpected error occurred.'}
      </p>
      <div className="d-flex gap-2">
        {onRetry && (
          <button className="btn btn-primary rounded-3" onClick={onRetry}>
            <i className="bi bi-arrow-clockwise me-2" />Retry
          </button>
        )}
        <Link to="/student" className="btn btn-outline-secondary rounded-3">
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
};

// ── Main Page ─────────────────────────────────────────────────────────────────
const ResultScorecardPage = () => {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const { user, role } = useAuth();

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorCode, setErrorCode] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [retryCount, setRetryCount] = useState(0);
  const MAX_RETRIES = 5;

  const fetchResult = useCallback(async (attempt = 0) => {
    if (!attemptId) return;
    if (attempt === 0) {
      setLoading(true);
      setErrorCode(null);
      setErrorMsg('');
    }

    let retrying = false;

    try {
      const data = await getResult(attemptId);

      // ── Normalize backend field names ──────────────────────────────────────
      // Backend returns: total_marks_obtained, total_marks_possible, pass_fail (bool)
      // ResultScorecardPage uses: marks_obtained, total_marks, status (string)
      const normalized = {
        ...data,
        // Marks
        marks_obtained:
          data.marks_obtained ??
          data.total_marks_obtained ??
          data.marks_obtained_mcq,
        total_marks:
          data.total_marks ??
          data.total_marks_possible ??
          data.total_possible,
        // Percentage
        percentage:
          data.percentage ??
          (data.total_marks_possible > 0
            ? ((data.total_marks_obtained / data.total_marks_possible) * 100).toFixed(2)
            : 0),
        // Status: normalize boolean pass_fail → string
        status:
          data.status ??
          (data.pass_fail === true
            ? 'passed'
            : data.pass_fail === false
            ? 'failed'
            : data.pass_fail_status),
      };
      setResult(normalized);
      setRetryCount(0);
    } catch (err) {
      const httpStatus = err?.response?.status;
      const detail = err?.response?.data?.detail || '';

      // Retry on 404/409 while result is still being computed server-side
      const shouldRetry =
        (httpStatus === 404 || httpStatus === 409) &&
        attempt < MAX_RETRIES;

      if (shouldRetry) {
        retrying = true;
        setRetryCount(attempt + 1);
        setTimeout(() => fetchResult(attempt + 1), 2000);
        return;
      }

      setErrorCode(httpStatus || null);
      setErrorMsg(detail || err.message || 'Failed to load result.');
    } finally {
      if (!retrying) {
        setLoading(false);
      }
    }
  }, [attemptId]);

  useEffect(() => {
    fetchResult(0);
  }, [fetchResult]);

  if (loading) {
    return (
      <div>
        <ResultSkeleton />
        {retryCount > 0 && (
          <div className="text-center pb-4" style={{ marginTop: '-2rem' }}>
            <div className="spinner-border spinner-border-sm text-primary me-2" role="status" aria-hidden="true" />
            <span className="text-muted small">
              Calculating your result… ({retryCount}/{MAX_RETRIES})
            </span>
          </div>
        )}
      </div>
    );
  }
  if (errorCode || (!result && !loading)) {
    return <ErrorState code={errorCode} message={errorMsg} onRetry={() => fetchResult(0)} />;
  }


  // ── Derived values ─────────────────────────────────────────────────────────
  const percentage = result.percentage != null
    ? parseFloat(result.percentage).toFixed(1)
    : pct(result.marks_obtained, result.total_marks);
  const status = result.status || result.result_status || result.pass_fail_status;
  const passedNorm = (status || '').toLowerCase();
  const isPassedOrFailed = ['passed', 'pass', 'failed', 'fail'].includes(passedNorm);

  const examId = result.exam_id || result.examId;


  return (
    <div className="bg-light min-vh-100">
      <div className="container py-5" style={{ maxWidth: 860 }}>

        {/* ── Breadcrumb ──────────────────────────────────────────────────── */}
        <nav aria-label="breadcrumb" className="mb-3">
          <ol className="breadcrumb small">
            <li className="breadcrumb-item">
              <Link to={`/${role || 'student'}`} className="text-decoration-none">Dashboard</Link>
            </li>
            {examId && (
              <li className="breadcrumb-item">
                <Link to={`/exams/${examId}/rankings`} className="text-decoration-none">Rankings</Link>
              </li>
            )}
            <li className="breadcrumb-item active" aria-current="page">Result #{attemptId}</li>
          </ol>
        </nav>

        {/* ── Header Card ─────────────────────────────────────────────────── */}
        <div className="card border-0 shadow rounded-4 mb-4 overflow-hidden">
          {/* Gradient accent strip */}
          <div style={{ height: 6, background: 'linear-gradient(90deg,#6366f1,#8b5cf6,#06b6d4)' }} />
          <div className="card-body p-4">
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-start gap-3">
              <div>
                <span className="badge bg-primary bg-opacity-10 text-primary fw-semibold mb-2" style={{ fontSize: '0.7rem', letterSpacing: '0.08em' }}>
                  EXAM RESULT
                </span>
                <h2 className="fw-bold mb-1" style={{ lineHeight: 1.2 }}>
                  {result.exam_name || result.exam_title || 'Examination'}
                </h2>
                {result.student_name && (
                  <p className="text-muted mb-0">
                    <i className="bi bi-person-fill me-1" />
                    {result.student_name}
                  </p>
                )}
              </div>

              <div className="text-md-end">
                {status && <StatusBadge status={status} />}
              </div>
            </div>

            {/* ── Big Score Display ──────────────────────────────────────── */}
            {(typeof result.marks_obtained === 'number' || typeof result.total_marks === 'number') && (
              <div className="mt-4 p-4 rounded-4 text-center"
                style={{ background: 'linear-gradient(135deg,#6366f110 0%,#8b5cf610 100%)', border: '1px solid #6366f125' }}>
                <p className="text-muted small mb-1 fw-semibold text-uppercase" style={{ letterSpacing: '0.1em' }}>Score</p>
                <h1 className="display-4 fw-bold mb-0" style={{ color: '#6366f1' }}>
                  {result.marks_obtained ?? '—'}
                  <span className="fs-3 text-muted fw-normal"> / {result.total_marks ?? '—'}</span>
                </h1>
                {percentage !== null && (
                  <p className="text-muted mb-0 mt-1 fs-5">{percentage}%</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Stat Cards Row ───────────────────────────────────────────────── */}
        <div className="row g-3 mb-4">
          {typeof result.marks_obtained === 'number' && (
            <div className="col-6 col-md-3">
              <StatCard label="Marks Obtained" value={result.marks_obtained} icon="bi-check2-all" accent="success" />
            </div>
          )}
          {typeof result.total_marks === 'number' && (
            <div className="col-6 col-md-3">
              <StatCard label="Total Marks" value={result.total_marks} icon="bi-clipboard2-check" accent="primary" />
            </div>
          )}
          {percentage !== null && (
            <div className="col-6 col-md-3">
              <StatCard label="Percentage" value={`${percentage}%`} icon="bi-percent" accent="info" />
            </div>
          )}
          {typeof result.correct_answers === 'number' && (
            <div className="col-6 col-md-3">
              <StatCard label="Correct Answers" value={result.correct_answers} icon="bi-patch-check-fill" accent="success" />
            </div>
          )}
          {typeof result.incorrect_answers === 'number' && (
            <div className="col-6 col-md-3">
              <StatCard label="Incorrect" value={result.incorrect_answers} icon="bi-x-circle-fill" accent="danger" />
            </div>
          )}
          {typeof result.unanswered_questions === 'number' && (
            <div className="col-6 col-md-3">
              <StatCard label="Unanswered" value={result.unanswered_questions} icon="bi-dash-circle-fill" accent="warning" />
            </div>
          )}
          {typeof result.coding_score === 'number' && (
            <div className="col-6 col-md-3">
              <StatCard label="Coding Score" value={result.coding_score} icon="bi-code-slash" accent="warning" />
            </div>
          )}
          {typeof result.negative_marks === 'number' && result.negative_marks !== 0 && (
            <div className="col-6 col-md-3">
              <StatCard label="Negative Marks" value={`−${Math.abs(result.negative_marks)}`} icon="bi-dash-square-fill" accent="danger" />
            </div>
          )}
        </div>

        {/* ── Breakdown Charts ─────────────────────────────────────────────── */}
        <div className="mb-4">
          <h5 className="fw-bold mb-3">
            <i className="bi bi-bar-chart-line-fill me-2 text-primary" />
            Performance Breakdown
          </h5>
          <ResultBreakdownChart result={result} />
        </div>

        {/* ── Details Table ────────────────────────────────────────────────── */}
        <div className="card border-0 shadow-sm rounded-4 mb-4">
          <div className="card-body p-4">
            <h6 className="fw-bold mb-3 text-secondary text-uppercase" style={{ fontSize: '0.75rem', letterSpacing: '0.08em' }}>
              <i className="bi bi-info-circle me-2" />Result Details
            </h6>
            <div className="table-responsive">
              <table className="table table-sm table-borderless mb-0">
                <tbody>
                  <DetailRow label="Attempt ID" value={result.attempt_id || result.id || attemptId} />
                  <DetailRow label="Student Name" value={result.student_name} />
                  <DetailRow label="Exam Name" value={result.exam_name || result.exam_title} />
                  <DetailRow label="Exam Date" value={formatDate(result.exam_date || result.started_at)} />
                  <DetailRow label="Submission Time" value={formatDate(result.submitted_at || result.submission_time)} />
                  <DetailRow label="Result Calculated At" value={formatDate(result.calculated_at || result.result_date)} />
                  <DetailRow label="Submission Status" value={result.submission_status || result.attempt_status} />
                  {isPassedOrFailed && (
                    <DetailRow
                      label="Final Status"
                      value={<StatusBadge status={status} />}
                    />
                  )}
                  <DetailRow label="Pass Marks" value={result.pass_marks} />
                  <DetailRow label="Rank" value={result.rank} />
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── Action Buttons ──────────────────────────────────────────────── */}
        <div className="d-flex flex-wrap gap-2 justify-content-center">
          <button className="btn btn-outline-secondary rounded-3" onClick={() => navigate(-1)}>
            <i className="bi bi-arrow-left me-2" />Go Back
          </button>
          <Link to={`/${role || 'student'}`} className="btn btn-primary rounded-3">
            <i className="bi bi-house me-2" />Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ResultScorecardPage;
