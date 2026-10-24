import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { getCandidateWiseReport } from '../../api/reportApi';
import ReportExportButton from '../../components/reports/ReportExportButton';

// ─── Colour helpers ──────────────────────────────────────────────────────────
const BAR_COLORS = ['#6366f1','#22c55e','#f59e0b','#ef4444','#06b6d4','#8b5cf6'];

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

const TableSkeleton = () => (
  <div className="p-4">
    {Array.from({ length: 6 }).map((_, i) => (
      <Skeleton key={i} h="2.2rem" cls="mb-2" />
    ))}
  </div>
);

// ─── Status badge ────────────────────────────────────────────────────────────
const PassFailBadge = ({ status }) => {
  const s = (status || '').toLowerCase();
  if (['passed', 'pass'].includes(s))
    return <span className="badge bg-success bg-opacity-15 text-success fw-semibold" style={{ fontSize: '0.7rem' }}>PASSED</span>;
  if (['failed', 'fail'].includes(s))
    return <span className="badge bg-danger bg-opacity-15 text-danger fw-semibold" style={{ fontSize: '0.7rem' }}>FAILED</span>;
  if (s)
    return <span className="badge bg-secondary bg-opacity-15 text-secondary fw-semibold" style={{ fontSize: '0.7rem' }}>{status.toUpperCase()}</span>;
  return <span className="text-muted">—</span>;
};

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

// ─── Error / empty ───────────────────────────────────────────────────────────
const ErrorBanner = ({ code, message, onRetry }) => {
  const msgs = {
    401: 'Authentication required. Please log in.',
    403: 'You are not authorized to view candidate reports.',
    404: 'No report data found.',
    422: 'Invalid filter values. Please check your input.',
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

const EmptyState = ({ message }) => (
  <div className="text-center py-5 text-muted">
    <i className="bi bi-people fs-1 d-block mb-3 opacity-30" />
    <h6 className="fw-semibold mb-1">No Candidates Found</h6>
    <p className="small mb-0">{message || 'Try adjusting the filters or selecting a different exam.'}</p>
  </div>
);

// ─── Filter bar ──────────────────────────────────────────────────────────────
const EMPTY_FILTERS = { exam_id: '', topic: '', candidate: '', from_date: '', to_date: '' };

const FilterBar = ({ filters, onChange, onApply, onReset, loading }) => (
  <div className="card border-0 shadow-sm rounded-4 mb-4">
    <div className="card-body p-4">
      <div className="row g-3 align-items-end">
        <div className="col-12 col-md-3">
          <label className="form-label small fw-semibold text-muted mb-1">Exam ID / Name</label>
          <input
            id="cand-filter-exam"
            type="text"
            className="form-control form-control-sm rounded-3"
            placeholder="e.g. 101"
            value={filters.exam_id}
            onChange={e => onChange('exam_id', e.target.value)}
          />
        </div>
        <div className="col-12 col-md-2">
          <label className="form-label small fw-semibold text-muted mb-1">Topic</label>
          <input
            id="cand-filter-topic"
            type="text"
            className="form-control form-control-sm rounded-3"
            placeholder="Topic"
            value={filters.topic}
            onChange={e => onChange('topic', e.target.value)}
          />
        </div>
        <div className="col-12 col-md-3">
          <label className="form-label small fw-semibold text-muted mb-1">Candidate Name / ID</label>
          <input
            id="cand-filter-candidate"
            type="text"
            className="form-control form-control-sm rounded-3"
            placeholder="Search candidate…"
            value={filters.candidate}
            onChange={e => onChange('candidate', e.target.value)}
          />
        </div>
        <div className="col-6 col-md-2">
          <label className="form-label small fw-semibold text-muted mb-1">From</label>
          <input
            id="cand-filter-from"
            type="date"
            className="form-control form-control-sm rounded-3"
            value={filters.from_date}
            onChange={e => onChange('from_date', e.target.value)}
          />
        </div>
        <div className="col-6 col-md-1">
          <label className="form-label small fw-semibold text-muted mb-1">To</label>
          <input
            id="cand-filter-to"
            type="date"
            className="form-control form-control-sm rounded-3"
            value={filters.to_date}
            onChange={e => onChange('to_date', e.target.value)}
          />
        </div>
        <div className="col-12 col-md-1 d-flex gap-2 justify-content-md-end">
          <button
            id="cand-filter-apply"
            className="btn btn-primary btn-sm rounded-3 flex-grow-1 flex-md-grow-0"
            onClick={onApply}
            disabled={loading}
          >
            {loading
              ? <span className="spinner-border spinner-border-sm" />
              : <><i className="bi bi-funnel-fill me-1" />Apply</>}
          </button>
          <button
            id="cand-filter-reset"
            className="btn btn-outline-secondary btn-sm rounded-3"
            onClick={onReset}
            disabled={loading}
            title="Reset"
          >
            <i className="bi bi-x-lg" />
          </button>
        </div>
      </div>
    </div>
  </div>
);

// ── Sort icon helper ─────────────────────────────────────────────────────────
const SortIcon = ({ col, sortCol, sortDir }) => {
  if (col !== sortCol) return <i className="bi bi-chevron-expand text-muted opacity-40 ms-1" style={{ fontSize: '0.7rem' }} />;
  return sortDir === 'asc'
    ? <i className="bi bi-chevron-up ms-1 text-primary" style={{ fontSize: '0.7rem' }} />
    : <i className="bi bi-chevron-down ms-1 text-primary" style={{ fontSize: '0.7rem' }} />;
};

// ════════════════════════════════════════════════════════════════════════════
// Main Page
// ════════════════════════════════════════════════════════════════════════════
const PAGE_SIZE = 15;

const CandidateWiseReportPage = () => {
  const [data, setData]         = useState([]);
  const [loading, setLoading]   = useState(false);
  const [errorCode, setErrCode] = useState(null);
  const [errorMsg, setErrMsg]   = useState('');
  const [filters, setFilters]   = useState(EMPTY_FILTERS);
  const [applied, setApplied]   = useState(EMPTY_FILTERS);

  // Client-side search (in addition to server filter)
  const [search, setSearch]     = useState('');
  // Sort
  const [sortCol, setSortCol]   = useState('rank');
  const [sortDir, setSortDir]   = useState('asc');
  // Pagination (client-side on fetched page)
  const [page, setPage]         = useState(1);

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const fetchReport = useCallback(async (params) => {
    setLoading(true);
    setErrCode(null);
    setErrMsg('');
    setPage(1);
    try {
      const clean = Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== '')
      );
      const res = await getCandidateWiseReport(clean);
      const list = Array.isArray(res)
        ? res
        : res?.candidates || res?.data || res?.results || [];
      setData(list);
    } catch (err) {
      setErrCode(err?.response?.status || null);
      setErrMsg(err?.response?.data?.detail || err.message || 'Failed to load report.');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchReport(EMPTY_FILTERS); }, [fetchReport]);

  const handleApply = () => { setApplied(filters); fetchReport(filters); };
  const handleReset = () => {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    setSearch('');
    fetchReport(EMPTY_FILTERS);
  };

  // ── Sort ───────────────────────────────────────────────────────────────────
  const handleSort = (col) => {
    if (col === sortCol) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortCol(col); setSortDir('asc'); }
    setPage(1);
  };

  // ── Derived / filtered / sorted data ──────────────────────────────────────
  const processed = useMemo(() => {
    let rows = [...data];

    // client-side search
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(r =>
        (r.candidate_name || r.student_name || r.name || '').toLowerCase().includes(q) ||
        String(r.candidate_id || r.student_id || '').toLowerCase().includes(q)
      );
    }

    // sort
    rows.sort((a, b) => {
      let va = a[sortCol] ?? a[sortCol === 'rank' ? 'rank' : sortCol] ?? 0;
      let vb = b[sortCol] ?? b[sortCol === 'rank' ? 'rank' : sortCol] ?? 0;
      if (typeof va === 'string') va = va.toLowerCase();
      if (typeof vb === 'string') vb = vb.toLowerCase();
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return rows;
  }, [data, search, sortCol, sortDir]);

  const totalPages = Math.max(1, Math.ceil(processed.length / PAGE_SIZE));
  const pageData   = processed.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // ── Summary numbers ────────────────────────────────────────────────────────
  const totalCandidates = data.length;
  const passCount  = data.filter(r => ['passed', 'pass'].includes((r.status || r.pass_fail_status || '').toLowerCase())).length;
  const passRate   = totalCandidates ? `${((passCount / totalCandidates) * 100).toFixed(1)}%` : null;
  const avgScore   = totalCandidates
    ? (data.reduce((s, r) => s + (r.score ?? r.marks_obtained ?? 0), 0) / totalCandidates).toFixed(1)
    : null;
  const avgPct     = totalCandidates
    ? (data.reduce((s, r) => s + (r.percentage ?? 0), 0) / totalCandidates).toFixed(1)
    : null;

  // ── Chart: top 10 by score ─────────────────────────────────────────────────
  const chartData = [...data]
    .sort((a, b) => (b.score ?? b.marks_obtained ?? 0) - (a.score ?? a.marks_obtained ?? 0))
    .slice(0, 10)
    .map(r => ({
      name: (r.candidate_name || r.student_name || r.name || `#${r.rank}`).split(' ')[0],
      score: r.score ?? r.marks_obtained ?? 0,
    }));

  // ── Sortable column defs ───────────────────────────────────────────────────
  const COLS = [
    { key: 'rank',             label: 'Rank',       sortable: true },
    { key: 'candidate_name',   label: 'Candidate',  sortable: true },
    { key: 'exam_name',        label: 'Exam',       sortable: false },
    { key: 'score',            label: 'Score',      sortable: true },
    { key: 'percentage',       label: '%',          sortable: true },
    { key: 'status',           label: 'Status',     sortable: true },
    { key: 'attempt_date',     label: 'Date',       sortable: true },
  ];

  // Only show columns that have at least one non-null value
  const activeCols = COLS.filter(c =>
    c.key === 'rank' || c.key === 'candidate_name' ||
    data.some(r => r[c.key] != null || r[c.key.replace('candidate_name', 'student_name')] != null)
  );

  const cellVal = (row, col) => {
    if (col.key === 'candidate_name') return row.candidate_name || row.student_name || row.name || '—';
    if (col.key === 'score') return row.score ?? row.marks_obtained ?? '—';
    if (col.key === 'percentage') {
      const p = row.percentage;
      return typeof p === 'number' ? `${p.toFixed(1)}%` : '—';
    }
    if (col.key === 'status') return <PassFailBadge status={row.status || row.pass_fail_status} />;
    if (col.key === 'attempt_date') {
      const d = row.attempt_date || row.exam_date || row.created_at;
      if (!d) return '—';
      return new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    }
    return row[col.key] ?? '—';
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
                <li className="breadcrumb-item active">Candidate Report</li>
              </ol>
            </nav>
            <h2 className="fw-bold mb-0">Candidate-Wise Performance Report</h2>
            <p className="text-muted small mb-0">Searchable, sortable breakdown of each candidate's exam performance</p>
          </div>
          <ReportExportButton filters={applied} disabled={loading || data.length === 0} />
        </div>

        {/* ── Filters ─────────────────────────────────────────────────────── */}
        <FilterBar
          filters={filters}
          onChange={(k, v) => setFilters(p => ({ ...p, [k]: v }))}
          onApply={handleApply}
          onReset={handleReset}
          loading={loading}
        />

        {/* ── Error ───────────────────────────────────────────────────────── */}
        {errorCode && (
          <ErrorBanner code={errorCode} message={errorMsg} onRetry={() => fetchReport(applied)} />
        )}

        {/* ── Summary cards ────────────────────────────────────────────────── */}
        {!loading && data.length > 0 && (
          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <SummaryCard label="Candidates" value={totalCandidates} icon="bi-people-fill" accent="primary" />
            </div>
            {passRate && (
              <div className="col-6 col-md-3">
                <SummaryCard label="Pass Rate" value={passRate} icon="bi-trophy-fill" accent="success" />
              </div>
            )}
            {avgScore && (
              <div className="col-6 col-md-3">
                <SummaryCard label="Avg Score" value={avgScore} icon="bi-graph-up-arrow" accent="info" />
              </div>
            )}
            {avgPct && (
              <div className="col-6 col-md-3">
                <SummaryCard label="Avg %" value={`${avgPct}%`} icon="bi-percent" accent="warning" />
              </div>
            )}
          </div>
        )}

        {/* ── Chart: Top 10 candidates ─────────────────────────────────────── */}
        {!loading && chartData.length > 0 && (
          <div className="card border-0 shadow-sm rounded-4 mb-4">
            <div className="card-body p-4">
              <h6 className="fw-bold text-secondary text-uppercase small mb-3" style={{ letterSpacing: '0.07em' }}>
                <i className="bi bi-bar-chart-fill me-1 text-primary" />
                Top 10 Candidates by Score
              </h6>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} margin={{ top: 4, right: 10, left: -14, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="score" name="Score" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── Table ───────────────────────────────────────────────────────── */}
        <div className="card border-0 shadow-sm rounded-4">
          {/* Table header: search + count */}
          <div className="card-header bg-white border-0 px-4 pt-4 pb-3 d-flex flex-wrap align-items-center gap-2 justify-content-between">
            <h6 className="fw-bold mb-0">
              <i className="bi bi-table me-2 text-primary" />
              Candidate Table
              {!loading && (
                <span className="badge bg-secondary bg-opacity-10 text-secondary ms-2" style={{ fontSize: '0.7rem' }}>
                  {processed.length} results
                </span>
              )}
            </h6>
            <div className="input-group input-group-sm" style={{ maxWidth: 240 }}>
              <span className="input-group-text bg-white border-end-0">
                <i className="bi bi-search text-muted" />
              </span>
              <input
                id="cand-table-search"
                type="text"
                className="form-control border-start-0"
                placeholder="Search by name or ID…"
                value={search}
                onChange={e => { setSearch(e.target.value); setPage(1); }}
              />
            </div>
          </div>

          <div className="card-body p-0">
            {loading ? (
              <TableSkeleton />
            ) : data.length === 0 && !errorCode ? (
              <EmptyState message="No candidate data found. Try adjusting the filters." />
            ) : processed.length === 0 ? (
              <EmptyState message={`No candidates match "${search}".`} />
            ) : (
              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      {activeCols.map(c => (
                        <th
                          key={c.key}
                          className={`py-3 text-uppercase text-muted fw-semibold ${c.sortable ? 'cursor-pointer user-select-none' : ''}`}
                          style={{ fontSize: '0.68rem', letterSpacing: '0.06em', whiteSpace: 'nowrap', cursor: c.sortable ? 'pointer' : 'default' }}
                          onClick={() => c.sortable && handleSort(c.key)}
                        >
                          {c.label}
                          {c.sortable && <SortIcon col={c.key} sortCol={sortCol} sortDir={sortDir} />}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {pageData.map((row, idx) => (
                      <tr key={row.candidate_id || row.student_id || idx}>
                        {activeCols.map(c => (
                          <td key={c.key} className="py-2 small">
                            {c.key === 'rank' ? (
                              <span className="fw-bold text-muted">{row.rank ?? idx + 1 + (page - 1) * PAGE_SIZE}</span>
                            ) : c.key === 'candidate_name' ? (
                              <div className="d-flex align-items-center gap-2">
                                <div
                                  className="rounded-circle bg-primary bg-opacity-10 text-primary d-flex align-items-center justify-content-center fw-bold flex-shrink-0"
                                  style={{ width: 32, height: 32, fontSize: '0.8rem' }}
                                >
                                  {(row.candidate_name || row.student_name || row.name || '?').charAt(0).toUpperCase()}
                                </div>
                                <div>
                                  <div className="fw-semibold">{row.candidate_name || row.student_name || row.name || '—'}</div>
                                  {(row.candidate_id || row.student_id) && (
                                    <div className="text-muted" style={{ fontSize: '0.72rem' }}>
                                      #{row.candidate_id || row.student_id}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : (
                              cellVal(row, c)
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {!loading && totalPages > 1 && (
              <div className="d-flex justify-content-center align-items-center gap-2 p-4 border-top">
                <button
                  className="btn btn-sm btn-outline-secondary rounded-3"
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  <i className="bi bi-chevron-left" /> Prev
                </button>
                <span className="text-muted small">Page {page} of {totalPages}</span>
                <button
                  className="btn btn-sm btn-outline-secondary rounded-3"
                  disabled={page === totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next <i className="bi bi-chevron-right" />
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default CandidateWiseReportPage;
