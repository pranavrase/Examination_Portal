import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useExam } from '../../context/ExamContext';
import { useAuth } from '../../context/AuthContext';

const ExamListPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { exams, fetchExams, deleteExam, loading, error, actionLoading } = useExam();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [examToDelete, setExamToDelete] = useState(null);

  useEffect(() => {
    fetchExams();
  }, [fetchExams]);

  const handleDeleteConfirm = async () => {
    if (!examToDelete) return;
    try {
      await deleteExam(examToDelete.id);
      setExamToDelete(null);
    } catch (err) {
      // Error handled by context
    }
  };

  const filteredExams = exams.filter((exam) => {
    const matchesSearch = exam.title?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter ? exam.status === statusFilter : true;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'published':
        return <span className="badge bg-success bg-opacity-10 text-success">Published</span>;
      case 'draft':
        return <span className="badge bg-secondary bg-opacity-10 text-secondary">Draft</span>;
      case 'closed':
        return <span className="badge bg-danger bg-opacity-10 text-danger">Closed</span>;
      default:
        return <span className="badge bg-primary bg-opacity-10 text-primary">{status}</span>;
    }
  };

  return (
    <div className="container py-4">
      <header className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
        <div>
          <h1 className="h3 mb-0 fw-bold">Exam Management</h1>
          <p className="text-muted mb-0">Create, configure, and manage examinations</p>
        </div>
        <button 
          className="btn btn-primary d-flex align-items-center gap-2"
          onClick={() => navigate('/exams/create')}
        >
          <i className="bi bi-plus-lg"></i> Create New Exam
        </button>
      </header>

      {error && (
        <div className="alert alert-danger rounded-3 mb-4">
          <i className="bi bi-exclamation-triangle-fill me-2"></i>
          {error}
        </div>
      )}

      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-header bg-white border-bottom p-4">
          <div className="row g-3">
            <div className="col-md-6">
              <div className="input-group">
                <span className="input-group-text bg-light border-end-0">
                  <i className="bi bi-search text-muted"></i>
                </span>
                <input 
                  type="text" 
                  className="form-control border-start-0 bg-light" 
                  placeholder="Search exams by title..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div className="col-md-4">
              <select 
                className="form-select bg-light"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="closed">Closed</option>
              </select>
            </div>
          </div>
        </div>

        <div className="card-body p-0">
          {loading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status"></div>
              <p className="text-muted mt-2">Loading exams...</p>
            </div>
          ) : filteredExams.length === 0 ? (
            <div className="text-center py-5 text-muted">
              <div className="display-4 mb-3"><i className="bi bi-folder-x"></i></div>
              <h5>No exams found</h5>
              <p className="mb-0">Try adjusting your search filters or create a new exam.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light">
                  <tr>
                    <th className="px-4 py-3 border-0">Title</th>
                    <th className="py-3 border-0">Status</th>
                    <th className="py-3 border-0">Duration</th>
                    <th className="py-3 border-0">Marks (Pass %)</th>
                    <th className="px-4 py-3 border-0 text-end">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredExams.map((exam) => (
                    <tr key={exam.id}>
                      <td className="px-4 py-3">
                        <div className="fw-semibold text-dark">{exam.title}</div>
                        <div className="text-muted small">
                          Created: {exam.created_at ? new Date(exam.created_at).toLocaleDateString() : '--'}
                        </div>
                      </td>
                      <td className="py-3">{getStatusBadge(exam.status)}</td>
                      <td className="py-3">
                        {exam.duration || exam.duration_minutes || '--'} mins
                      </td>
                      <td className="py-3">
                        {exam.total_marks || '--'} ({exam.passing_percentage || '--'}%)
                      </td>
                      <td className="px-4 py-3 text-end">
                        <button 
                          className="btn btn-sm btn-outline-primary me-2"
                          onClick={() => navigate(`/exams/${exam.id}/edit`)}
                          title="Configure Exam"
                        >
                          <i className="bi bi-gear"></i> Manage
                        </button>
                        <button 
                          className="btn btn-sm btn-outline-danger"
                          onClick={() => setExamToDelete(exam)}
                          disabled={actionLoading}
                          title="Delete Exam"
                        >
                          <i className="bi bi-trash"></i>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {examToDelete && (
        <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 rounded-4 shadow">
              <div className="modal-header border-bottom-0 pb-0">
                <h5 className="modal-title fw-bold text-danger">Delete Examination?</h5>
                <button type="button" className="btn-close" onClick={() => setExamToDelete(null)} disabled={actionLoading}></button>
              </div>
              <div className="modal-body">
                <p>Are you sure you want to delete:</p>
                <p className="fw-bold fs-5 text-dark mb-0">"{examToDelete.title}"?</p>
                <p className="text-muted mt-3 small">This action cannot be undone. All associated questions and data might be lost.</p>
              </div>
              <div className="modal-footer border-top-0 pt-0">
                <button type="button" className="btn btn-outline-secondary" onClick={() => setExamToDelete(null)} disabled={actionLoading}>
                  Cancel
                </button>
                <button type="button" className="btn btn-danger" onClick={handleDeleteConfirm} disabled={actionLoading}>
                  {actionLoading ? <span className="spinner-border spinner-border-sm"></span> : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExamListPage;
