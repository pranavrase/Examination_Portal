import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStudent } from '../../context/StudentContext';

const MyExamsPage = () => {
  const navigate = useNavigate();
  const { exams, loadingExams, examsError, fetchExams } = useStudent();
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'available' | 'upcoming' | 'completed' | 'expired'
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    fetchExams();
  }, [fetchExams]);

  // Status badge helper
  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'active':
      case 'available':
        return <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25"><i className="bi bi-play-circle me-1"></i> Available Now</span>;
      case 'upcoming':
        return <span className="badge bg-info bg-opacity-10 text-info border border-info border-opacity-25"><i className="bi bi-clock me-1"></i> Upcoming</span>;
      case 'in_progress':
        return <span className="badge bg-warning bg-opacity-10 text-warning text-dark border border-warning border-opacity-25"><i className="bi bi-hourglass-split me-1"></i> In Progress</span>;
      case 'completed':
        return <span className="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-25"><i className="bi bi-check-circle me-1"></i> Completed</span>;
      case 'expired':
      case 'closed':
        return <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25"><i className="bi bi-x-circle me-1"></i> Expired</span>;
      default:
        return <span className="badge bg-light text-dark border">{status || 'Assigned'}</span>;
    }
  };

  const getSubjectBadge = (cat) => {
    const norm = (cat || 'General').toLowerCase();
    if (norm.includes('aptitude')) return <span className="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25">Aptitude</span>;
    if (norm.includes('reasoning')) return <span className="badge bg-info bg-opacity-10 text-info border border-info border-opacity-25">Reasoning</span>;
    if (norm.includes('technical')) return <span className="badge bg-warning bg-opacity-10 text-dark border border-warning border-opacity-25">Technical</span>;
    if (norm.includes('coding')) return <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25">Coding</span>;
    return <span className="badge bg-light text-dark border">{cat || 'Mixed'}</span>;
  };

  const filteredExams = exams.filter((exam) => {
    const matchesSearch =
      exam.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      exam.subject?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      exam.category?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCat =
      categoryFilter === 'all' ||
      exam.subject?.toLowerCase().includes(categoryFilter) ||
      exam.category?.toLowerCase().includes(categoryFilter) ||
      exam.type?.toLowerCase().includes(categoryFilter);

    const st = exam.status?.toLowerCase() || 'upcoming';
    let matchesTab = true;
    if (activeTab === 'available') matchesTab = st === 'active' || st === 'available';
    else if (activeTab === 'upcoming') matchesTab = st === 'upcoming' || st === 'assigned';
    else if (activeTab === 'completed') matchesTab = st === 'completed';
    else if (activeTab === 'expired') matchesTab = st === 'expired' || st === 'closed';

    return matchesSearch && matchesCat && matchesTab;
  });

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 text-uppercase tracking-wider">Candidate Portal</span>
            <span className="badge bg-light text-secondary border">{exams.length} Total Exams</span>
          </div>
          <h1 className="h4 mb-0 fw-bold">My Examinations</h1>
          <p className="text-muted mb-0 small">Browse, review instructions, and launch all assigned and scheduled assessments.</p>
        </div>
        <button className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1.5 rounded-3" onClick={fetchExams}>
          <i className="bi bi-arrow-clockwise"></i> Refresh
        </button>
      </header>

      {/* Filter Tabs & Search Controls */}
      <div className="card shadow-sm border-0 rounded-4 mb-4">
        <div className="card-header bg-white border-bottom p-3">
          <div className="row g-3 align-items-center">
            {/* Status Tabs */}
            <div className="col-12 col-lg-7">
              <div className="nav nav-pills gap-1">
                {[
                  { id: 'all', label: 'All Exams' },
                  { id: 'available', label: 'Available Now' },
                  { id: 'upcoming', label: 'Upcoming' },
                  { id: 'completed', label: 'Completed' },
                  { id: 'expired', label: 'Expired' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    className={`btn btn-sm rounded-3 px-3 ${activeTab === tab.id ? 'btn-primary shadow-sm' : 'btn-light text-secondary'}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Search & Category Filter */}
            <div className="col-12 col-lg-5 d-flex gap-2">
              <select
                className="form-select form-select-sm bg-light"
                style={{ maxWidth: '140px' }}
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="all">All Topics</option>
                <option value="aptitude">Aptitude</option>
                <option value="reasoning">Reasoning</option>
                <option value="technical">Technical</option>
                <option value="coding">Coding</option>
              </select>

              <div className="input-group input-group-sm flex-grow-1">
                <span className="input-group-text bg-light border-end-0"><i className="bi bi-search text-muted"></i></span>
                <input
                  type="text"
                  className="form-control border-start-0 bg-light"
                  placeholder="Search exam title..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Exams Table / Cards */}
        <div className="card-body p-0">
          {loadingExams ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status"></div>
              <p className="text-muted mt-2 small">Loading your assigned examinations...</p>
            </div>
          ) : examsError ? (
            <div className="p-4">
              <div className="alert alert-danger rounded-3 mb-0"><i className="bi bi-exclamation-triangle-fill me-2"></i>{examsError}</div>
            </div>
          ) : filteredExams.length === 0 ? (
            <div className="text-center py-5 text-muted p-4">
              <div className="display-4 text-muted mb-2"><i className="bi bi-journal-x"></i></div>
              <h6 className="fw-bold">No Examinations Found</h6>
              <p className="small mb-0">No assigned exams match your selected tab or filter criteria.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="px-4 py-3 border-0">Examination</th>
                    <th className="py-3 border-0">Subject & Category</th>
                    <th className="py-3 border-0">Schedule / Duration</th>
                    <th className="py-3 border-0">Marks & Rules</th>
                    <th className="py-3 border-0">Status</th>
                    <th className="px-4 py-3 border-0 text-end">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredExams.map((exam) => {
                    const isAvailable = exam.status === 'active' || exam.status === 'available';
                    const isCompleted = exam.status === 'completed';

                    return (
                      <tr key={exam.id}>
                        <td className="px-4 py-3">
                          <div className="fw-bold text-dark">{exam.title}</div>
                          <small className="text-muted">ID: #{exam.id}</small>
                        </td>
                        <td className="py-3">
                          {getSubjectBadge(exam.subject || exam.category || exam.type)}
                          <div className="small text-muted mt-1">{exam.topic || 'Core Evaluation'}</div>
                        </td>
                        <td className="py-3">
                          <div className="small text-dark fw-semibold">
                            <i className="bi bi-stopwatch text-primary me-1"></i>
                            {exam.duration_minutes || exam.duration || 60} mins
                          </div>
                          <div className="small text-muted">
                            <i className="bi bi-calendar3 me-1"></i>
                            {exam.scheduled_start ? new Date(exam.scheduled_start).toLocaleDateString() : 'Self-Paced'}
                          </div>
                        </td>
                        <td className="py-3">
                          <div className="small text-dark">
                            <strong>{exam.total_marks || 100}</strong> Total Marks ({exam.passing_percentage || 40}% Pass)
                          </div>
                          <div className="small text-muted">
                            {exam.negative_marking ? (
                              <span className="text-warning"><i className="bi bi-dash-circle me-1"></i>-{exam.negative_marking} Penalty</span>
                            ) : (
                              <span className="text-success"><i className="bi bi-check-circle me-1"></i>No Negative Marks</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3">{getStatusBadge(exam.status)}</td>
                        <td className="px-4 py-3 text-end">
                          {isCompleted ? (
                            <button
                              className="btn btn-sm btn-outline-success rounded-3 d-inline-flex align-items-center gap-1"
                              onClick={() => navigate(`/results/${exam.attempt_id || exam.id}`)}
                            >
                              <i className="bi bi-file-earmark-bar-graph"></i> Scorecard
                            </button>
                          ) : isAvailable ? (
                            <button
                              className="btn btn-sm btn-primary rounded-3 px-3 fw-semibold d-inline-flex align-items-center gap-1 shadow-sm"
                              onClick={() => navigate(`/student/exam/${exam.id}`)}
                            >
                              <i className="bi bi-play-circle-fill"></i> Start Exam
                            </button>
                          ) : (
                            <button
                              className="btn btn-sm btn-outline-primary rounded-3 d-inline-flex align-items-center gap-1"
                              onClick={() => navigate(`/student/exam/${exam.id}`)}
                            >
                              <i className="bi bi-info-circle"></i> Instructions
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyExamsPage;
