import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const AssignedExamsList = ({ exams, loading, error }) => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  if (loading) {
    return (
      <div className="text-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Loading exams...</span>
        </div>
        <p className="text-muted mt-2">Loading assigned exams...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-danger rounded-3" role="alert">
        <i className="bi bi-exclamation-triangle-fill me-2"></i> {error}
      </div>
    );
  }

  // Filter out completed ones, keep assigned/upcoming/active
  const activeExams = exams.filter(exam => 
    (exam.status !== 'completed' && exam.status !== 'closed' && exam.status !== 'expired' && !exam.attempt_id) &&
    (exam.title?.toLowerCase().includes(searchTerm.toLowerCase()) || 
     exam.subject?.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  if (exams.length === 0) {
    return (
      <div className="card shadow-sm border-0 rounded-4">
        <div className="card-body p-5 text-center">
          <div className="display-4 text-muted mb-3">
            <i className="bi bi-calendar2-x"></i>
          </div>
          <h5 className="text-muted">No Assigned Exams</h5>
          <p className="text-secondary mb-0">You don't have any exams assigned to you at the moment.</p>
        </div>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'active':
        return <span className="badge bg-success bg-opacity-10 text-success">Active Now</span>;
      case 'upcoming':
        return <span className="badge bg-info bg-opacity-10 text-info">Upcoming</span>;
      case 'assigned':
      default:
        return <span className="badge bg-secondary bg-opacity-10 text-secondary">Assigned</span>;
    }
  };

  const getActionBtn = (exam) => {
    const isReady = exam.status?.toLowerCase() === 'active';
    
    return (
      <button 
        className={`btn btn-sm ${isReady ? 'btn-primary' : 'btn-outline-primary'}`}
        onClick={() => navigate(`/student/exam/${exam.id}`)}
      >
        {isReady ? (
          <><i className="bi bi-play-circle me-1"></i> Start Exam</>
        ) : (
          <><i className="bi bi-info-circle me-1"></i> Details</>
        )}
      </button>
    );
  };

  return (
    <div className="card shadow-sm border-0 rounded-4">
      <div className="card-header bg-white border-bottom p-4 d-flex justify-content-between align-items-center">
        <h5 className="mb-0 fw-bold">All Assigned Exams</h5>
        <div className="input-group" style={{ maxWidth: '250px' }}>
          <span className="input-group-text bg-light border-end-0">
            <i className="bi bi-search text-muted"></i>
          </span>
          <input 
            type="text" 
            className="form-control border-start-0 bg-light" 
            placeholder="Search exams..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>
      <div className="card-body p-0">
        {activeExams.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <p className="mb-0">No assigned exams match your search.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover mb-0 align-middle">
              <thead className="table-light">
                <tr>
                  <th className="px-4 py-3 border-0">Exam Title</th>
                  <th className="py-3 border-0">Date & Time</th>
                  <th className="py-3 border-0">Duration</th>
                  <th className="py-3 border-0">Status</th>
                  <th className="px-4 py-3 border-0 text-end">Action</th>
                </tr>
              </thead>
              <tbody>
                {activeExams.map((exam) => (
                  <tr key={exam.id}>
                    <td className="px-4 py-3">
                      <div className="fw-semibold text-dark">{exam.title}</div>
                      <div className="text-muted small">{exam.subject || exam.type || 'General'}</div>
                    </td>
                    <td className="py-3">
                      {exam.scheduled_start ? (
                        <>
                          <div><i className="bi bi-calendar3 me-1 text-muted"></i> {new Date(exam.scheduled_start).toLocaleDateString()}</div>
                          <div className="small text-muted"><i className="bi bi-clock me-1"></i> {new Date(exam.scheduled_start).toLocaleTimeString(undefined, {hour: '2-digit', minute:'2-digit'})}</div>
                        </>
                      ) : (
                        <span className="text-muted">Not scheduled</span>
                      )}
                    </td>
                    <td className="py-3">
                      {exam.duration_minutes || exam.duration ? `${exam.duration_minutes || exam.duration} mins` : '--'}
                    </td>
                    <td className="py-3">
                      {getStatusBadge(exam.status)}
                    </td>
                    <td className="px-4 py-3 text-end">
                      {getActionBtn(exam)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AssignedExamsList;
