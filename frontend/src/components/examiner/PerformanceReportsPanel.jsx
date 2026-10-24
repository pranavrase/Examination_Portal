import React, { useEffect, useState, useCallback } from 'react';
import { getPerformanceAnalysis, getMyExams } from '../../api/examinerApi';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const TOPIC_COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ec4899',
  '#3b82f6', '#8b5cf6', '#14b8a6', '#f97316',
  '#06b6d4', '#84cc16', '#a855f7', '#e11d48',
  '#0ea5e9', '#d946ef', '#f43f5e', '#64748b'
];

const CustomPieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const item = payload[0]?.payload;
  return (
    <div className="bg-dark text-white rounded-3 px-3 py-2 shadow-lg" style={{ fontSize: '0.82rem', zIndex: 1000 }}>
      <div className="fw-bold mb-1">{item.topic}</div>
      <div className="text-light small">
        Accuracy: <strong className="text-info">{item.accuracy_percentage}%</strong>
      </div>
      <div className="text-light small opacity-75">
        Answers Evaluated: {item.total_answers}
      </div>
      <div className="text-light small opacity-75">
        Avg Score: {item.average_score}
      </div>
      <div className="text-light small opacity-75">
        Benchmark: <span className="text-success fw-semibold">{item.benchmark}</span>
      </div>
    </div>
  );
};

const PerformanceReportsPanel = () => {
  const [data, setData] = useState(null);
  const [exams, setExams] = useState([]);
  const [selectedExamId, setSelectedExamId] = useState('');
  const [loading, setLoading] = useState(true);

  // Load available examinations for filter
  useEffect(() => {
    const loadExams = async () => {
      try {
        const res = await getMyExams();
        setExams(Array.isArray(res) ? res : res?.items || []);
      } catch (err) {
        console.error('Failed to load exams list:', err);
        setExams([]);
      }
    };
    loadExams();
  }, []);

  // Fetch performance report based on selected exam
  const fetchPerf = useCallback(async (examId) => {
    try {
      setLoading(true);
      const params = {};
      if (examId) {
        params.exam_id = examId;
      }
      const res = await getPerformanceAnalysis(params);
      setData(res);
    } catch (err) {
      console.error('Failed to load performance report:', err);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPerf(selectedExamId);
  }, [selectedExamId, fetchPerf]);

  const handlePrint = () => {
    window.print();
  };

  const overall = data?.overall_stats || {};
  const avgScore = overall.average_score ?? 0;
  const highestScore = overall.highest_score ?? overall.max_score ?? 0;
  const lowestScore = overall.lowest_score ?? overall.min_score ?? overall.minimum_score ?? 0;
  const passPercentage = overall.pass_percentage ?? 0;
  const failPercentage = overall.fail_percentage ?? 0;
  const totalEvaluated = overall.total_evaluated ?? 0;

  const topics = data?.topic_performance || [];
  const questions = data?.question_wise_insights || [];
  const strengths = data?.candidate_strengths || [];
  const weaknesses = data?.weak_topics || [];

  return (
    <div className="d-flex flex-column gap-4" id="performance-reports-panel">
      {/* Top Header Card */}
      <div className="card border-0 shadow-sm rounded-4 p-4">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
          <div>
            <span className="badge bg-primary mb-1 text-uppercase fw-semibold">
              Deep Analytics & Performance Insights
            </span>
            <h4 className="fw-bold mb-1 text-dark">Candidate Performance & Topic Analysis</h4>
            <p className="text-muted small mb-0">
              Cohort-wide accuracy, topic strengths, difficult question identification, and pass metrics
            </p>
          </div>

          <div className="d-flex flex-wrap align-items-center gap-2">
            {/* Examination Filter */}
            <div className="d-flex align-items-center gap-2 bg-light border rounded-3 px-3 py-1.5">
              <i className="bi bi-funnel text-muted small" />
              <label htmlFor="exam-filter-select" className="small fw-semibold text-muted mb-0 text-nowrap">
                Exam:
              </label>
              <select
                id="exam-filter-select"
                className="form-select form-select-sm border-0 bg-transparent fw-medium py-1"
                style={{ minWidth: 200, cursor: 'pointer' }}
                value={selectedExamId}
                onChange={(e) => setSelectedExamId(e.target.value)}
              >
                <option value="">All Examinations ({exams.length})</option>
                {exams.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.title} {ex.status ? `(${ex.status})` : ''}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              className="btn btn-outline-primary d-flex align-items-center gap-2 rounded-3 px-4 shadow-sm"
              onClick={handlePrint}
            >
              <i className="bi bi-printer-fill" />
              Print / Export PDF
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
          <div className="spinner-border text-primary" role="status" />
          <p className="text-muted small mt-2">Computing comprehensive analytics & performance metrics...</p>
        </div>
      ) : (
        <>
          {/* Cohort KPIs - 5 Balanced Responsive Cards */}
          <div className="row g-3 row-cols-2 row-cols-sm-3 row-cols-xl-5" id="cohort-kpis">
            {/* Average Score */}
            <div className="col">
              <div className="card border border-primary border-opacity-20 shadow-sm rounded-4 p-3 text-center h-100 bg-white">
                <div className="text-muted small fw-medium mb-1 d-flex align-items-center justify-content-center gap-1">
                  <i className="bi bi-bar-chart-fill text-primary" />
                  <span>Average Score</span>
                </div>
                <div className="fs-3 fw-bold text-primary">{avgScore}%</div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>{totalEvaluated} evaluated</div>
              </div>
            </div>

            {/* Highest Score */}
            <div className="col">
              <div className="card border border-success border-opacity-20 shadow-sm rounded-4 p-3 text-center h-100 bg-white">
                <div className="text-muted small fw-medium mb-1 d-flex align-items-center justify-content-center gap-1">
                  <i className="bi bi-trophy-fill text-success" />
                  <span>Highest Score</span>
                </div>
                <div className="fs-3 fw-bold text-success">{highestScore}%</div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>Top candidate</div>
              </div>
            </div>

            {/* Lowest Score */}
            <div className="col">
              <div className="card border border-danger border-opacity-25 shadow-sm rounded-4 p-3 text-center h-100 bg-white">
                <div className="text-muted small fw-medium mb-1 d-flex align-items-center justify-content-center gap-1">
                  <i className="bi bi-graph-down-arrow text-danger" />
                  <span>Lowest Score</span>
                </div>
                <div className="fs-3 fw-bold text-danger" id="kpi-lowest-score">{lowestScore}%</div>
                <div className="text-muted" style={{ fontSize: '0.75rem' }}>Base benchmark</div>
              </div>
            </div>

            {/* Pass Percentage */}
            <div className="col">
              <div className="card border border-success border-opacity-20 shadow-sm rounded-4 p-3 text-center h-100 bg-success bg-opacity-10">
                <div className="text-muted small fw-medium mb-1 d-flex align-items-center justify-content-center gap-1">
                  <i className="bi bi-check-circle-fill text-success" />
                  <span>Pass Percentage</span>
                </div>
                <div className="fs-3 fw-bold text-success">{passPercentage}%</div>
                <div className="text-success small fw-semibold" style={{ fontSize: '0.75rem' }}>Qualified candidates</div>
              </div>
            </div>

            {/* Fail Percentage */}
            <div className="col">
              <div className="card border border-danger border-opacity-20 shadow-sm rounded-4 p-3 text-center h-100 bg-danger bg-opacity-10">
                <div className="text-muted small fw-medium mb-1 d-flex align-items-center justify-content-center gap-1">
                  <i className="bi bi-x-circle-fill text-danger" />
                  <span>Fail Percentage</span>
                </div>
                <div className="fs-3 fw-bold text-danger">{failPercentage}%</div>
                <div className="text-danger small fw-semibold" style={{ fontSize: '0.75rem' }}>Require improvement</div>
              </div>
            </div>
          </div>

          {/* Topic-Wise Accuracy & Performance - PIE CHART & LIST */}
          <div className="card border-0 shadow-sm rounded-4 p-4">
            <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-3">
              <h5 className="fw-bold mb-0 d-flex align-items-center gap-2">
                <i className="bi bi-pie-chart-fill text-primary" />
                <span>Topic-Wise Accuracy & Performance</span>
              </h5>
              {topics.length > 0 && (
                <span className="badge bg-light text-dark border rounded-pill px-3 py-1.5 fw-semibold mt-2 mt-md-0">
                  {topics.length} Topics Analyzed
                </span>
              )}
            </div>

            {topics.length > 0 ? (
              <div className="row g-4 align-items-center">
                {/* Recharts Pie Chart */}
                <div className="col-lg-5 col-xl-5">
                  <div className="p-3 bg-light rounded-4 text-center border">
                    <h6 className="fw-bold text-dark mb-1 small text-uppercase">Accuracy Distribution by Topic</h6>
                    <p className="text-muted small mb-2" style={{ fontSize: '0.75rem' }}>Hover over segments to inspect details</p>
                    <div style={{ width: '100%', height: 300 }}>
                      <ResponsiveContainer>
                        <PieChart>
                          <Pie
                            data={topics}
                            dataKey="accuracy_percentage"
                            nameKey="topic"
                            cx="50%"
                            cy="50%"
                            innerRadius={55}
                            outerRadius={95}
                            paddingAngle={3}
                          >
                            {topics.map((entry, index) => (
                              <Cell
                                key={`cell-${index}`}
                                fill={TOPIC_COLORS[index % TOPIC_COLORS.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip content={<CustomPieTooltip />} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Topic Breakdown Cards */}
                <div className="col-lg-7 col-xl-7">
                  <div
                    className="d-flex flex-column gap-3 pe-1"
                    style={{ maxHeight: 360, overflowY: 'auto' }}
                  >
                    {topics.map((t, idx) => (
                      <div key={t.topic} className="p-3 border rounded-3 bg-light">
                        <div className="d-flex justify-content-between align-items-center mb-1">
                          <div className="d-flex align-items-center gap-2">
                            <span
                              className="d-inline-block rounded-circle"
                              style={{
                                width: 10,
                                height: 10,
                                backgroundColor: TOPIC_COLORS[idx % TOPIC_COLORS.length],
                              }}
                            />
                            <span className="fw-bold text-dark">{t.topic}</span>
                          </div>
                          <span
                            className={`badge ${
                              t.accuracy_percentage >= 75
                                ? 'bg-success-subtle text-success'
                                : t.accuracy_percentage >= 50
                                ? 'bg-primary-subtle text-primary'
                                : 'bg-warning-subtle text-warning'
                            } rounded-pill px-2.5 py-1 fw-bold`}
                          >
                            {t.accuracy_percentage}% Accuracy
                          </span>
                        </div>
                        <div className="progress my-2" style={{ height: 8 }}>
                          <div
                            className={`progress-bar ${
                              t.accuracy_percentage >= 75
                                ? 'bg-success'
                                : t.accuracy_percentage >= 50
                                ? 'bg-primary'
                                : 'bg-warning'
                            }`}
                            role="progressbar"
                            style={{ width: `${Math.max(t.accuracy_percentage, 2)}%` }}
                          />
                        </div>
                        <div className="d-flex justify-content-between text-muted small mt-1.5" style={{ fontSize: '0.78rem' }}>
                          <span>Avg Marks: <strong>{t.average_score}</strong></span>
                          <span>Evaluated: <strong>{t.total_answers}</strong> answers</span>
                          <span>Difficulty: <strong>{t.difficulty}</strong></span>
                          <span className="text-success fw-semibold">{t.benchmark}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-5 text-muted">
                <i className="bi bi-pie-chart display-5 d-block mb-2 opacity-30" />
                <h6 className="fw-semibold">No topic performance data available</h6>
                <p className="small mb-0">Topic analysis will appear after students complete exams.</p>
              </div>
            )}
          </div>

          {/* Question-Wise Analysis & Difficult Questions */}
          <div className="row g-4">
            <div className="col-lg-8">
              <div className="card border-0 shadow-sm rounded-4 p-4 h-100">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h5 className="fw-bold mb-0 d-flex align-items-center gap-2">
                    <i className="bi bi-patch-question-fill text-warning" />
                    <span>Question-Wise Difficulty & Error Rates</span>
                  </h5>
                  {questions.length > 0 && (
                    <span className="badge bg-secondary-subtle text-secondary rounded-pill px-2.5 py-1 small">
                      {questions.length} Questions
                    </span>
                  )}
                </div>

                <div className="table-responsive" style={{ maxHeight: 420, overflowY: 'auto' }}>
                  <table className="table table-hover align-middle mb-0">
                    <thead className="table-light sticky-top">
                      <tr>
                        <th className="py-2.5 small fw-semibold text-muted">Q ID</th>
                        <th className="py-2.5 small fw-semibold text-muted">PROBLEM / QUESTION</th>
                        <th className="py-2.5 small fw-semibold text-muted">ACCURACY</th>
                        <th className="py-2.5 small fw-semibold text-muted">ERROR RATE</th>
                        <th className="py-2.5 small fw-semibold text-muted">AVG TIME</th>
                        <th className="py-2.5 small fw-semibold text-muted text-end">DIAGNOSIS</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questions.length > 0 ? (
                        questions.map((q) => (
                          <tr key={q.question_id}>
                            <td className="font-monospace fw-bold text-muted small">#{q.question_id}</td>
                            <td className="small text-dark fw-medium" style={{ maxWidth: 240 }} title={q.text}>
                              {q.text}
                            </td>
                            <td>
                              <span
                                className={`badge ${
                                  q.accuracy >= 65
                                    ? 'bg-success-subtle text-success'
                                    : q.accuracy >= 40
                                    ? 'bg-warning-subtle text-warning'
                                    : 'bg-danger-subtle text-danger'
                                } rounded-pill px-2.5 py-1`}
                              >
                                {q.accuracy}%
                              </span>
                            </td>
                            <td>
                              <span
                                className={`badge ${
                                  q.error_rate > 50
                                    ? 'bg-danger-subtle text-danger'
                                    : q.error_rate > 25
                                    ? 'bg-warning-subtle text-warning'
                                    : 'bg-secondary-subtle text-secondary'
                                } rounded-pill px-2.5 py-1`}
                              >
                                {q.error_rate}%
                              </span>
                            </td>
                            <td className="small text-muted">{q.avg_time_sec}s</td>
                            <td className="text-end">
                              <span
                                className={`badge ${
                                  q.status === 'High Accuracy' || q.status === 'Good Performance'
                                    ? 'bg-success text-white'
                                    : q.status === 'Moderate Performance'
                                    ? 'bg-primary text-white'
                                    : 'bg-danger text-white'
                                } rounded-pill px-2.5 py-1 small`}
                              >
                                {q.status}
                              </span>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="6" className="text-center text-muted small py-4">
                            No question data available yet
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Strengths & Weaknesses */}
            <div className="col-lg-4">
              <div className="card border-0 shadow-sm rounded-4 p-4 h-100 d-flex flex-column gap-3">
                <h5 className="fw-bold mb-1 d-flex align-items-center gap-2">
                  <i className="bi bi-lightbulb-fill text-info" />
                  <span>Cohort Insights</span>
                </h5>

                <div className="p-3 bg-success bg-opacity-10 border border-success border-opacity-15 rounded-3">
                  <div className="fw-bold text-success small text-uppercase mb-2 d-flex align-items-center gap-1.5">
                    <i className="bi bi-check-circle-fill" /> Candidate Strengths
                  </div>
                  {strengths.length > 0 ? (
                    <ul className="mb-0 ps-3 small text-dark d-flex flex-column gap-1">
                      {strengths.map((strength, index) => (
                        <li key={index} className="fw-medium">{strength}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mb-0 small text-muted">No strength data available yet.</p>
                  )}
                </div>

                <div className="p-3 bg-danger bg-opacity-10 border border-danger border-opacity-15 rounded-3">
                  <div className="fw-bold text-danger small text-uppercase mb-2 d-flex align-items-center gap-1.5">
                    <i className="bi bi-exclamation-triangle-fill" /> Focus Areas / Weak Topics
                  </div>
                  {weaknesses.length > 0 ? (
                    <ul className="mb-0 ps-3 small text-dark d-flex flex-column gap-1">
                      {weaknesses.map((weakness, index) => (
                        <li key={index} className="fw-medium">{weakness}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mb-0 small text-muted">No weakness data available yet.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default PerformanceReportsPanel;
