import React, { useState, useCallback, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis, Cell,
} from 'recharts';
import { getTopicWiseReport } from '../../api/reportApi';
import ReportExportButton from '../../components/reports/ReportExportButton';

// ─── Colour palette ─────────────────────────────────────────────────────────
const BAR_COLORS = [
  '#6366f1','#22c55e','#f59e0b','#ef4444',
  '#06b6d4','#8b5cf6','#ec4899','#10b981',
];

// ─── Shared helpers ──────────────────────────────────────────────────────────
const fmt = (v, decimals = 1) =>
  typeof v === 'number' ? v.toFixed(decimals) : '—';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-dark text-white rounded-3 px-3 py-2 shadow" style={{ fontSize: '0.78rem' }}>
      {label && <p className="fw-semibold mb-1 text-secondary">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="mb-0" style={{ color: p.color || '#fff' }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

// ─── Skeleton ────────────────────────────────────────────────────────────────
const Skeleton = ({ h = '1rem', w = '100%', cls = '' }) => (
  <div className={`placeholder-glow ${cls}`} style={{ height: h, width: w }}>
    <span className="placeholder rounded w-100 h-100 d-block" />
  </div>
);

const SummarySkeleton = () => (
  <div className="row g-3 mb-4">
    {[1, 2, 3, 4].map(i => (
      <div key={i} className="col-6 col-md-3"><Skeleton h="80px" /></div>
    ))}
  </div>
);

// ─── Summary card ────────────────────────────────────────────────────────────
const SummaryCard = ({ label, value, icon, accent = 'primary' }) => (
  <div className={`card border-0 shadow-sm rounded-4 border-start border-${accent} border-4`}>
    <div className="card-body py-3">
      <p className="text-muted small fw-semibold mb-1 text-uppercase" style={{ fontSize: '0.68rem', letterSpacing: '0.07em' }}>
        {label}
      </p>
      <div className="d-flex align-items-center justify-content-between">
        <h4 className="fw-bold mb-0">{value ?? '—'}</h4>
        <i className={`bi ${icon} text-${accent} fs-4 opacity-40`} />
      </div>
    </div>
  </div>
);

// ─── Filter bar ──────────────────────────────────────────────────────────────
const FilterBar = ({ filters, onChange, onApply, onReset, loading }) => (
  <div className="card border-0 shadow-sm rounded-4 mb-4">
    <div className="card-body p-4">
      <div className="row g-3 align-items-end">
        <div className="col-12 col-md-4">
          <label className="form-label small fw-semibold text-muted mb-1">Exam ID / Name</label>
          <input
            id="topic-filter-exam"
            type="text"
            className="form-control form-control-sm rounded-3"
            placeholder="e.g. 101 or Aptitude Test"
            value={filters.exam_id}
            onChange={e => onChange('exam_id', e.target.value)}
          />
        </div>
        <div className="col-12 col-md-3">
          <label className="form-label small fw-semibold text-muted mb-1">Topic</label>
          <input
            id="topic-filter-topic"
            type="text"
            className="form-control form-control-sm rounded-3"
            placeholder="Filter by topic"
            value={filters.topic}
            onChange={e => onChange('topic', e.target.value)}
          />
        </div>
        <div className="col-6 col-md-2">
          <label className="form-label small fw-semibold text-muted mb-1">From Date</label>
          <input
            id="topic-filter-from"
            type="date"
            className="form-control form-control-sm rounded-3"
            value={filters.from_date}
            onChange={e => onChange('from_date', e.target.value)}
          />
        </div>
        <div className="col-6 col-md-2">
          <label className="form-label small fw-semibold text-muted mb-1">To Date</label>
          <input
            id="topic-filter-to"
            type="date"
            className="form-control form-control-sm rounded-3"
            value={filters.to_date}
            onChange={e => onChange('to_date', e.target.value)}
          />
        </div>
        <div className="col-12 col-md-1 d-flex gap-2 justify-content-md-end">
          <button
            id="topic-filter-apply"
            className="btn btn-primary btn-sm rounded-3 flex-grow-1 flex-md-grow-0"
            onClick={onApply}
            disabled={loading}
          >
            {loading
              ? <span className="spinner-border spinner-border-sm" />
              : <><i className="bi bi-funnel-fill me-1" />Apply</>
            }
          </button>
          <button
            id="topic-filter-reset"
            className="btn btn-outline-secondary btn-sm rounded-3"
            onClick={onReset}
            disabled={loading}
            title="Reset filters"
          >
            <i className="bi bi-x-lg" />
          </button>
        </div>
      </div>
    </div>
  </div>
);

// ─── Empty / Error states ────────────────────────────────────────────────────
const EmptyState = ({ message }) => (
  <div className="text-center py-5 text-muted">
    <i className="bi bi-bar-chart-line fs-1 d-block mb-3 opacity-30" />
    <h6 className="fw-semibold mb-1">No Data Found</h6>
    <p className="small mb-0">{message || 'Try changing the selected exam or date range.'}</p>
  </div>
);

const ErrorBanner = ({ code, message, onRetry }) => {
  const msgs = {
    401: 'Authentication required. Please log in.',
    403: 'You are not authorized to view performance reports.',
    404: 'Report data not found.',
    422: 'Invalid filter parameters. Please check the values.',
    500: 'Server error. Please try again later.',
  };
  return (
    <div className="alert alert-danger d-flex align-items-center gap-3 rounded-4 border-0 shadow-sm">
      <i className="bi bi-exclamation-triangle-fill fs-4 flex-shrink-0" />
      <div className="flex-grow-1">
        <strong>{code ? `Error ${code}` : 'Request Failed'}</strong>
        <p className="mb-0 small">{msgs[code] || message || 'An unexpected error occurred.'}</p>
      </div>
      {onRetry && (
        <button className="btn btn-sm btn-outline-danger rounded-3" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════════════════
// Main Page
// ════════════════════════════════════════════════════════════════════════════
const EMPTY_FILTERS = { exam_id: '', topic: '', from_date: '', to_date: '' };

const TopicWiseReportPage = () => {
  const [data, setData]         = useState([]);
  const [loading, setLoading]   = useState(false);
  const [errorCode, setErrCode] = useState(null);
  const [errorMsg, setErrMsg]   = useState('');
  const [filters, setFilters]   = useState(EMPTY_FILTERS);
  const [applied, setApplied]   = useState(EMPTY_FILTERS); // last committed filters

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchReport = useCallback(async (params) => {
    setLoading(true);
    setErrCode(null);
    setErrMsg('');
    try {
      const clean = Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== '')
      );
      const res = await getTopicWiseReport(clean);
      // Accept array or wrapped { topics: [], data: [] }
      const list = Array.isArray(res)
        ? res
        : res?.topics || res?.data || res?.results || [];
      setData(list);
    } catch (err) {
      setErrCode(err?.response?.status || null);
      setErrMsg(err?.response?.data?.detail || err.message || 'Failed to load report.');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // initial load (no filters)
  useEffect(() => { fetchReport(EMPTY_FILTERS); }, [fetchReport]);

  const handleApply = () => {
    setApplied(filters);
    fetchReport(filters);
  };

  const handleReset = () => {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    fetchReport(EMPTY_FILTERS);
  };

  const handleFilterChange = (key, val) =>
    setFilters(prev => ({ ...prev, [key]: val }));

  // ── Derived summaries ──────────────────────────────────────────────────────
  const totalTopics   = data.length;
  const avgAccuracy   = data.length
    ? (data.reduce((s, r) => s + (r.accuracy ?? 0), 0) / data.length).toFixed(1)
    : null;
  const totalCandidates = data.reduce((s, r) => s + (r.candidates_attempted ?? 0), 0) || null;
  const totalQuestions  = data.reduce((s, r) => s + (r.questions_count ?? r.num_questions ?? 0), 0) || null;

  // ── Chart data ─────────────────────────────────────────────────────────────
  const hasAvgScore  = data.some(r => typeof r.avg_score === 'number' || typeof r.average_score === 'number');
  const hasAccuracy  = data.some(r => typeof r.accuracy === 'number');
  const hasBreakdown = data.some(r => typeof r.correct_answers === 'number');

  const chartBase = data.map(r => ({
    topic:    r.topic || r.topic_name || r.name || 'Unknown',
    avg:      r.avg_score ?? r.average_score ?? 0,
    max:      r.max_score ?? r.maximum_score ?? 0,
    min:      r.min_score ?? r.minimum_score ?? 0,
    accuracy: r.accuracy ?? 0,
    correct:  r.correct_answers ?? 0,
    incorrect:r.incorrect_answers ?? 0,
    unanswered: r.unanswered_questions ?? 0,
  }));

  // ── Table columns (dynamic) ────────────────────────────────────────────────
  const COL_MAP = [
    { key: 'topic',               label: 'Topic',             always: true },
    { key: 'questions_count',     label: 'Questions',         alt: 'num_questions' },
    { key: 'candidates_attempted',label: 'Candidates' },
    { key: 'avg_score',           label: 'Avg Score',         alt: 'average_score', fmt: true },
    { key: 'max_score',           label: 'Max Score',         alt: 'maximum_score' },
    { key: 'min_score',           label: 'Min Score',         alt: 'minimum_score' },
    { key: 'accuracy',            label: 'Accuracy',          fmt: true, suffix: '%' },
    { key: 'correct_answers',     label: 'Correct' },
    { key: 'incorrect_answers',   label: 'Incorrect' },
    { key: 'unanswered_questions',label: 'Unanswered' },
  ];

  const activeCols = COL_MAP.filter(c => {
    if (c.always) return true;
    return data.some(r => r[c.key] != null || (c.alt && r[c.alt] != null));
  });

  const cellVal = (row, col) => {
    let v = row[col.key];
    if (v == null && col.alt) v = row[col.alt];
    if (v == null) return '—';
    const num = typeof v === 'number' ? (col.fmt ? v.toFixed(1) : v) : v;
    return col.suffix ? `${num}${col.suffix}` : num;
  };

  return (
    <div className="bg-light min-vh-100">
      <div className="container-fluid py-4 px-lg-5">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-start gap-3 mb-4">
          <div>
            <nav aria-label="breadcrumb" className="mb-1">
              <ol className="breadcrumb small mb-0">
                <li className="breadcrumb-item"><Link to="/examiner" className="text-decoration-none">Dashboard</Link></li>
                <li className="breadcrumb-item active">Topic-Wise Report</li>
              </ol>
            </nav>
            <h2 className="fw-bold mb-0">Topic-Wise Performance Report</h2>
            <p className="text-muted small mb-0">Analyze performance grouped by exam topic</p>
          </div>
          <ReportExportButton filters={applied} disabled={loading || data.length === 0} />
        </div>

        {/* ── Filters ─────────────────────────────────────────────────────── */}
        <FilterBar
          filters={filters}
          onChange={handleFilterChange}
          onApply={handleApply}
          onReset={handleReset}
          loading={loading}
        />

        {/* ── Error banner ─────────────────────────────────────────────────── */}
        {errorCode && (
          <ErrorBanner code={errorCode} message={errorMsg} onRetry={() => fetchReport(applied)} />
        )}

        {/* ── Summary cards ────────────────────────────────────────────────── */}
        {loading ? (
          <SummarySkeleton />
        ) : data.length > 0 && (
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <SummaryCard label="Total Topics"      value={totalTopics}      icon="bi-collection"        accent="primary" />
            </div>
            {totalCandidates !== null && (
              <div className="col-6 col-md-3">
                <SummaryCard label="Candidates"      value={totalCandidates}  icon="bi-people-fill"       accent="info" />
              </div>
            )}
            {avgAccuracy !== null && (
              <div className="col-6 col-md-3">
                <SummaryCard label="Avg Accuracy"    value={`${avgAccuracy}%`} icon="bi-bullseye"         accent="success" />
              </div>
            )}
            {totalQuestions !== null && (
              <div className="col-6 col-md-3">
                <SummaryCard label="Total Questions" value={totalQuestions}    icon="bi-question-circle"  accent="warning" />
              </div>
            )}
          </div>
        )}

        {/* ── Charts ───────────────────────────────────────────────────────── */}
        {!loading && data.length > 0 && (
          <div className="row g-4 mb-4">

            {/* Average Score by Topic */}
            {hasAvgScore && (
              <div className="col-12 col-xl-6">
                <div className="card border-0 shadow-sm rounded-4">
                  <div className="card-body p-4">
                    <h6 className="fw-bold text-secondary text-uppercase small mb-3" style={{ letterSpacing: '0.07em' }}>
                      <i className="bi bi-bar-chart-fill me-1 text-primary" /> Average Score by Topic
                    </h6>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={chartBase} margin={{ top: 4, right: 10, left: -14, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="topic" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="avg" name="Avg Score" radius={[4, 4, 0, 0]}>
                          {chartBase.map((_, i) => (
                            <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}

            {/* Accuracy by Topic */}
            {hasAccuracy && (
              <div className="col-12 col-xl-6">
                <div className="card border-0 shadow-sm rounded-4">
                  <div className="card-body p-4">
                    <h6 className="fw-bold text-secondary text-uppercase small mb-3" style={{ letterSpacing: '0.07em' }}>
                      <i className="bi bi-bullseye me-1 text-success" /> Accuracy by Topic
                    </h6>
                    <ResponsiveContainer width="100%" height={220}>
                      <RadarChart data={chartBase}>
                        <PolarGrid stroke="#e2e8f0" />
                        <PolarAngleAxis dataKey="topic" tick={{ fontSize: 11 }} />
                        <PolarRadiusAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
                        <Radar name="Accuracy %" dataKey="accuracy" stroke="#22c55e" fill="#22c55e" fillOpacity={0.3} />
                        <Tooltip content={<CustomTooltip />} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}

            {/* Correct / Incorrect / Unanswered grouped bar */}
            {hasBreakdown && (
              <div className="col-12">
                <div className="card border-0 shadow-sm rounded-4">
                  <div className="card-body p-4">
                    <h6 className="fw-bold text-secondary text-uppercase small mb-3" style={{ letterSpacing: '0.07em' }}>
                      <i className="bi bi-pie-chart-fill me-1 text-warning" /> Answer Breakdown by Topic
                    </h6>
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={chartBase} margin={{ top: 4, right: 10, left: -14, bottom: 40 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis dataKey="topic" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
                        <Bar dataKey="correct"   name="Correct"    fill="#22c55e" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="incorrect" name="Incorrect"  fill="#ef4444" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="unanswered" name="Unanswered" fill="#94a3b8" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Detailed table ───────────────────────────────────────────────── */}
        <div className="card border-0 shadow-sm rounded-4">
          <div className="card-header bg-white border-0 px-4 pt-4 pb-0">
            <h6 className="fw-bold mb-0">
              <i className="bi bi-table me-2 text-primary" />Detailed Topic Table
            </h6>
          </div>
          <div className="card-body p-0">
            {loading ? (
              <div className="p-4">
                {[1, 2, 3, 4, 5].map(i => (
                  <Skeleton key={i} h="2.2rem" cls="mb-2" />
                ))}
              </div>
            ) : data.length === 0 && !errorCode ? (
              <EmptyState message="No topic data found. Try adjusting the exam or date filters." />
            ) : data.length > 0 ? (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      {activeCols.map(c => (
                        <th key={c.key} className="py-3 text-uppercase text-muted fw-semibold"
                          style={{ fontSize: '0.68rem', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
                          {c.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.map((row, idx) => (
                      <tr key={idx}>
                        {activeCols.map(c => (
                          <td key={c.key} className="py-2 small">
                            {c.key === 'topic'
                              ? <span className="fw-semibold">{row.topic || row.topic_name || row.name || '—'}</span>
                              : c.key === 'accuracy'
                              ? (
                                <div className="d-flex align-items-center gap-2">
                                  <div className="progress flex-grow-1" style={{ height: 5, maxWidth: 60 }}>
                                    <div
                                      className="progress-bar bg-success"
                                      style={{ width: `${Math.min(100, row.accuracy ?? 0)}%` }}
                                    />
                                  </div>
                                  <span>{cellVal(row, c)}</span>
                                </div>
                              )
                              : cellVal(row, c)
                            }
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </div>
        </div>

      </div>
    </div>
  );
};

export default TopicWiseReportPage;
