import React, { useEffect, useState } from 'react';
import { getCandidates, assignCandidatesToExam, unassignCandidateFromExam, getMyExams } from '../../api/examinerApi';

const CandidateManagementPanel = () => {
  const [candidates, setCandidates] = useState([]);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [targetExamId, setTargetExamId] = useState('');
  const [assignLoading, setAssignLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [candData, examData] = await Promise.all([
        getCandidates(),
        getMyExams(),
      ]);
      console.log('Candidates API response:', candData);
      console.log('Candidates array length:', Array.isArray(candData) ? candData.length : 'Not an array');
      setCandidates(Array.isArray(candData) ? candData : []);
      setExams(Array.isArray(examData) ? examData : examData?.items || []);
    } catch (err) {
      console.error('Failed to load candidate directory:', err);
      console.error('Error response:', err.response?.data);
      setCandidates([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredCandidates = candidates.filter((c) => {
    const term = search.toLowerCase();
    const matchesSearch = c.full_name?.toLowerCase().includes(term) || c.email?.toLowerCase().includes(term) || c.roll_number?.toLowerCase().includes(term);
    const matchesStatus = statusFilter ? c.status?.toLowerCase() === statusFilter.toLowerCase() : true;
    return matchesSearch && matchesStatus;
  });

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedStudentIds(filteredCandidates.map((c) => c.id));
    } else {
      setSelectedStudentIds([]);
    }
  };

  const handleToggleStudent = (id) => {
    setSelectedStudentIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleAssignBatch = async () => {
    if (!targetExamId || selectedStudentIds.length === 0) return;
    try {
      setAssignLoading(true);
      await assignCandidatesToExam(targetExamId, {
        student_ids: selectedStudentIds,
      });
      setMessage({ type: 'success', text: `Assigned ${selectedStudentIds.length} candidate(s) successfully!` });
      setShowAssignModal(false);
      setSelectedStudentIds([]);
      fetchData();
    } catch (err) {
      setMessage({ type: 'danger', text: err?.response?.data?.detail || 'Assignment failed' });
    } finally {
      setAssignLoading(false);
    }
  };

  const handleUnassign = async (examId, studentId) => {
    try {
      await unassignCandidateFromExam(examId, studentId);
      setMessage({ type: 'info', text: 'Candidate unassigned successfully.' });
      fetchData();
    } catch (err) {
      alert('Failed to unassign candidate');
    }
  };

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'in progress':
        return <span className="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-3">In Progress</span>;
      case 'completed':
      case 'submitted':
        return <span className="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-3">Completed</span>;
      case 'auto submitted':
        return <span className="badge bg-info-subtle text-info border border-info-subtle rounded-pill px-3">Auto Submitted</span>;
      case 'disqualified':
        return <span className="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-3">Disqualified</span>;
      default:
        return <span className="badge bg-secondary-subtle text-secondary border border-secondary-subtle rounded-pill px-3">Not Started</span>;
    }
  };

  return (
    <div className="card border-0 shadow-sm rounded-4 mb-4" id="candidate-management">
      {/* Header */}
      <div className="card-header bg-white border-0 rounded-top-4 p-4 pb-0">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
          <div>
            <span className="badge bg-success text-white mb-1 text-uppercase fw-semibold">
              Candidate Directory & Assignments
            </span>
            <h5 className="fw-bold mb-1 d-flex align-items-center gap-2">
              <i className="bi bi-people-fill text-success" />
              <span>Registered Candidates</span>
            </h5>
            <p className="text-muted small mb-0">
              Manage candidate exam enrollments, batch assignments, and lifecycle status
            </p>
          </div>
          <button
            className="btn btn-success d-flex align-items-center gap-2 rounded-3 px-4 shadow-sm"
            onClick={() => setShowAssignModal(true)}
            disabled={selectedStudentIds.length === 0}
          >
            <i className="bi bi-person-plus-fill" />
            Assign Selected ({selectedStudentIds.length})
          </button>
        </div>

        {/* Global Alert Notification */}
        {message && (
          <div className={`alert alert-${message.type} alert-dismissible fade show rounded-3 py-2 small mb-3`} role="alert">
            <i className={`bi ${message.type === 'success' ? 'bi-check-circle-fill' : 'bi-info-circle-fill'} me-2`} />
            <span>{message.text}</span>
            <button type="button" className="btn-close py-2" onClick={() => setMessage(null)} />
          </div>
        )}

        {/* Search & Status Filters */}
        <div className="row g-2 mb-3">
          <div className="col-12 col-md-6">
            <div className="input-group">
              <span className="input-group-text bg-light border-end-0">
                <i className="bi bi-search text-muted" />
              </span>
              <input
                type="text"
                className="form-control border-start-0 bg-light"
                placeholder="Search candidates by name, email or roll number..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="col-6 col-md-3">
            <select
              className="form-select bg-light"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="not started">Not Started</option>
              <option value="in progress">In Progress</option>
              <option value="completed">Completed / Submitted</option>
              <option value="auto submitted">Auto Submitted</option>
              <option value="disqualified">Disqualified</option>
            </select>
          </div>
          <div className="col-6 col-md-3 d-flex align-items-center">
            <span className="text-muted small">
              Showing <strong>{filteredCandidates.length}</strong> candidates
            </span>
          </div>
        </div>
      </div>

      {/* Table Body */}
      <div className="card-body p-0">
        {loading ? (
          <div className="p-5 text-center">
            <div className="spinner-border text-success" role="status" />
            <p className="text-muted small mt-2">Loading candidate directory...</p>
          </div>
        ) : candidates.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-people display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">No candidates registered</h6>
            <p className="small mb-0">Candidates will appear here once they register for exams.</p>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <i className="bi bi-search display-4 d-block mb-3 opacity-30" />
            <h6 className="fw-semibold">No candidates found</h6>
            <p className="small mb-0">Try changing your search keyword or filters.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light">
                <tr>
                  <th className="ps-4 py-3" style={{ width: 40 }}>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={selectedStudentIds.length === filteredCandidates.length && filteredCandidates.length > 0}
                      onChange={handleSelectAll}
                    />
                  </th>
                  <th className="py-3 fw-semibold text-muted small">CANDIDATE</th>
                  <th className="py-3 fw-semibold text-muted small">ROLL NO</th>
                  <th className="py-3 fw-semibold text-muted small">DEPARTMENT</th>
                  <th className="py-3 fw-semibold text-muted small">STATUS</th>
                  <th className="pe-4 py-3 fw-semibold text-muted small text-end">ENROLLED EXAMS</th>
                </tr>
              </thead>
              <tbody>
                {filteredCandidates.map((c) => (
                  <tr key={c.id} className="border-top">
                    <td className="ps-4 py-3">
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={selectedStudentIds.includes(c.id)}
                        onChange={() => handleToggleStudent(c.id)}
                      />
                    </td>
                    <td className="py-3">
                      <div className="d-flex align-items-center gap-2">
                        <div
                          className="rounded-circle bg-success bg-opacity-10 text-success fw-bold d-flex align-items-center justify-content-center"
                          style={{ width: 34, height: 34, fontSize: '0.85rem' }}
                        >
                          {c.full_name?.charAt(0) || 'S'}
                        </div>
                        <div>
                          <div className="fw-semibold text-dark">{c.full_name}</div>
                          <div className="text-muted small">{c.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="text-muted small font-monospace">{c.roll_number}</td>
                    <td className="text-muted small">{c.department}</td>
                    <td>{getStatusBadge(c.status)}</td>
                    <td className="pe-4 text-end">
                      {c.assigned_exams && c.assigned_exams.length > 0 ? (
                        <div className="d-flex justify-content-end gap-1 flex-wrap">
                          {c.assigned_exams.map((ae) => (
                            <span key={ae.exam_id} className="badge bg-light text-dark border d-flex align-items-center gap-1.5 px-2 py-1">
                              <span>{ae.title}</span>
                              <button
                                type="button"
                                className="btn-close"
                                style={{ fontSize: '0.5rem' }}
                                onClick={() => handleUnassign(ae.exam_id, c.id)}
                                title="Remove assignment"
                              />
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="badge bg-light text-muted border">None Assigned</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Batch Assignment Modal */}
      {showAssignModal && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1055 }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 rounded-4 shadow">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold">Assign Examination</h5>
                <button type="button" className="btn-close" onClick={() => setShowAssignModal(false)} />
              </div>
              <div className="modal-body">
                <p className="text-muted small">
                  Assign <strong>{selectedStudentIds.length}</strong> selected candidate(s) to an active examination:
                </p>
                <div className="mb-3">
                  <label className="form-label small fw-semibold text-muted text-uppercase">Select Examination</label>
                  <select
                    className="form-select rounded-3"
                    value={targetExamId}
                    onChange={(e) => setTargetExamId(e.target.value)}
                  >
                    <option value="">-- Choose Examination --</option>
                    {exams.map((ex) => (
                      <option key={ex.id} value={ex.id}>
                        {ex.title} ({ex.status})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="modal-footer border-top-0 pt-0">
                <button type="button" className="btn btn-outline-secondary rounded-3" onClick={() => setShowAssignModal(false)}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-success rounded-3 px-4"
                  onClick={handleAssignBatch}
                  disabled={!targetExamId || assignLoading}
                >
                  {assignLoading ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CandidateManagementPanel;
