import React, { useMemo } from 'react';
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';

// ── Colour Palette ──────────────────────────────────────────────────────────
const COLORS = {
  correct: '#22c55e',    // green-500
  incorrect: '#ef4444',  // red-500
  unanswered: '#94a3b8', // slate-400
  obtained: '#6366f1',   // indigo-500
  total: '#e2e8f0',      // slate-200
  coding: '#f59e0b',     // amber-500
};

// ── Custom Tooltip ──────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-dark text-white rounded-3 px-3 py-2 shadow-lg" style={{ fontSize: '0.8rem' }}>
      {label && <p className="mb-1 fw-semibold text-secondary">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} className="mb-0" style={{ color: p.color || '#fff' }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
};

/**
 * ResultBreakdownChart
 *
 * Adaptively renders the most meaningful chart(s) for the available result data.
 *
 * Props:
 *  result {Object} – raw result object returned from GET /results/{attempt_id}
 */
const ResultBreakdownChart = ({ result }) => {
  if (!result) return null;

  // ── Derive available fields ────────────────────────────────────────────────
  const {
    marks_obtained,
    total_marks,
    correct_answers,
    incorrect_answers,
    unanswered_questions,
    coding_score,
    section_scores,
  } = result;

  const hasMarkData =
    typeof marks_obtained === 'number' && typeof total_marks === 'number';
  const hasAnswerBreakdown =
    typeof correct_answers === 'number' ||
    typeof incorrect_answers === 'number' ||
    typeof unanswered_questions === 'number';
  const hasSectionData =
    Array.isArray(section_scores) && section_scores.length > 0;

  // ── Nothing to chart ───────────────────────────────────────────────────────
  if (!hasMarkData && !hasAnswerBreakdown && !hasSectionData) {
    return (
      <div className="text-center py-5 text-secondary">
        <i className="bi bi-bar-chart-line fs-2 d-block mb-2 opacity-50" />
        <p className="mb-0 small">No breakdown data available for this result.</p>
      </div>
    );
  }

  // ── Score Donut data ───────────────────────────────────────────────────────
  const scoreDonutData = hasMarkData
    ? [
        { name: 'Obtained', value: marks_obtained, fill: COLORS.obtained },
        {
          name: 'Remaining',
          value: Math.max(0, total_marks - marks_obtained),
          fill: COLORS.total,
        },
      ]
    : null;

  // ── Answer breakdown Pie data ──────────────────────────────────────────────
  const answerPieData = useMemo(() => {
    const data = [];
    if (typeof correct_answers === 'number')
      data.push({ name: 'Correct', value: correct_answers, color: COLORS.correct });
    if (typeof incorrect_answers === 'number')
      data.push({ name: 'Incorrect', value: incorrect_answers, color: COLORS.incorrect });
    if (typeof unanswered_questions === 'number')
      data.push({ name: 'Unanswered', value: unanswered_questions, color: COLORS.unanswered });
    return data.filter((d) => d.value > 0);
  }, [correct_answers, incorrect_answers, unanswered_questions]);

  // ── Section Bar data ──────────────────────────────────────────────────────
  const sectionBarData = hasSectionData
    ? section_scores.map((s) => ({
        name: s.section || s.topic || s.name || 'Section',
        Obtained: s.obtained ?? s.marks_obtained ?? 0,
        Total: s.total ?? s.max_marks ?? 0,
      }))
    : null;

  // ── Coding score supplement ────────────────────────────────────────────────
  const codingBarData =
    typeof coding_score === 'number' && hasMarkData
      ? [
          { name: 'MCQ', value: Math.max(0, marks_obtained - coding_score) },
          { name: 'Coding', value: coding_score },
        ]
      : null;

  return (
    <div className="row g-4">
      {/* ── Score Donut ─────────────────────────────────────────────────── */}
      {scoreDonutData && (
        <div className={`col-12 ${hasAnswerBreakdown ? 'col-md-6' : ''}`}>
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <h6 className="fw-bold text-secondary text-uppercase small tracking-wider mb-3">
                <i className="bi bi-circle-half me-1" />
                Score Overview
              </h6>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={scoreDonutData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                    startAngle={90}
                    endAngle={-270}
                  >
                    {scoreDonutData.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="d-flex justify-content-center gap-4 mt-1">
                <span className="d-flex align-items-center gap-1 small">
                  <span
                    className="rounded-circle d-inline-block"
                    style={{ width: 10, height: 10, background: COLORS.obtained }}
                  />
                  Obtained
                </span>
                <span className="d-flex align-items-center gap-1 small text-secondary">
                  <span
                    className="rounded-circle d-inline-block"
                    style={{ width: 10, height: 10, background: COLORS.total }}
                  />
                  Remaining
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Answer Breakdown Pie ────────────────────────────────────────── */}
      {hasAnswerBreakdown && answerPieData.length > 0 && (
        <div className={`col-12 ${scoreDonutData ? 'col-md-6' : ''}`}>
          <div className="card border-0 shadow-sm rounded-4 h-100">
            <div className="card-body">
              <h6 className="fw-bold text-secondary text-uppercase small tracking-wider mb-3">
                <i className="bi bi-pie-chart-fill me-1" />
                Answer Breakdown
              </h6>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={answerPieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {answerPieData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="d-flex justify-content-center gap-3 mt-1 flex-wrap">
                {answerPieData.map((d, i) => (
                  <span key={i} className="d-flex align-items-center gap-1 small">
                    <span
                      className="rounded-circle d-inline-block"
                      style={{ width: 10, height: 10, background: d.color }}
                    />
                    {d.name} ({d.value})
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Section Performance Bar ─────────────────────────────────────── */}
      {sectionBarData && (
        <div className="col-12">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body">
              <h6 className="fw-bold text-secondary text-uppercase small tracking-wider mb-3">
                <i className="bi bi-bar-chart-steps me-1" />
                Section / Topic Performance
              </h6>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={sectionBarData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend />
                  <Bar dataKey="Total" fill={COLORS.total} radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Obtained" fill={COLORS.obtained} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Coding vs MCQ split ─────────────────────────────────────────── */}
      {codingBarData && (
        <div className="col-12 col-md-6">
          <div className="card border-0 shadow-sm rounded-4">
            <div className="card-body">
              <h6 className="fw-bold text-secondary text-uppercase small tracking-wider mb-3">
                <i className="bi bi-code-slash me-1" />
                MCQ vs Coding Score
              </h6>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart
                  data={codingBarData}
                  layout="vertical"
                  margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={50} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {codingBarData.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={index === 0 ? COLORS.obtained : COLORS.coding}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ResultBreakdownChart;
