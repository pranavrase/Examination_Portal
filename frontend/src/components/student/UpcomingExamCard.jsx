import React from 'react';
import { useNavigate } from 'react-router-dom';

const UpcomingExamCard = ({ exam }) => {
  const navigate = useNavigate();
  
  if (!exam) return null;

  // Format date and time safely
  const formattedDate = exam.scheduled_start 
    ? new Date(exam.scheduled_start).toLocaleDateString(undefined, { 
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' 
      })
    : 'Date TBD';
    
  const formattedTime = exam.scheduled_start
    ? new Date(exam.scheduled_start).toLocaleTimeString(undefined, { 
        hour: '2-digit', minute: '2-digit' 
      })
    : 'Time TBD';

  const handleViewExam = () => {
    // We navigate to a placeholder exam details/lobby page for now
    navigate(`/student/exam/${exam.id}`);
  };

  return (
    <div className="card shadow-sm border-0 rounded-4 mb-3" style={{ background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.05) 0%, rgba(14, 165, 233, 0.05) 100%)', border: '1px solid rgba(79, 70, 229, 0.1)' }}>
      <div className="card-body p-4">
        <div className="d-flex justify-content-between align-items-start mb-3">
          <div>
            <span className="badge bg-primary bg-opacity-10 text-primary mb-2">Upcoming Exam</span>
            <h5 className="fw-bold mb-1">{exam.title}</h5>
            {exam.subject && <p className="text-muted mb-0 small">{exam.subject}</p>}
          </div>
          <div className="bg-white p-2 rounded-3 shadow-sm text-center" style={{ minWidth: '70px' }}>
            <div className="text-primary fw-bold fs-4 mb-0" style={{ lineHeight: '1' }}>
              {exam.scheduled_start ? new Date(exam.scheduled_start).getDate() : '--'}
            </div>
            <div className="small text-muted text-uppercase" style={{ fontSize: '0.7rem' }}>
              {exam.scheduled_start ? new Date(exam.scheduled_start).toLocaleDateString(undefined, { month: 'short' }) : 'TBD'}
            </div>
          </div>
        </div>
        
        <div className="row g-3 mb-4">
          <div className="col-6">
            <div className="d-flex align-items-center text-muted small">
              <i className="bi bi-calendar3 me-2 text-primary"></i>
              {formattedDate}
            </div>
          </div>
          <div className="col-6">
            <div className="d-flex align-items-center text-muted small">
              <i className="bi bi-clock me-2 text-primary"></i>
              {formattedTime}
            </div>
          </div>
          <div className="col-6">
            <div className="d-flex align-items-center text-muted small">
              <i className="bi bi-hourglass-split me-2 text-primary"></i>
              {exam.duration_minutes || exam.duration || '--'} mins
            </div>
          </div>
          <div className="col-6">
            <div className="d-flex align-items-center text-muted small">
              <i className="bi bi-award me-2 text-primary"></i>
              {exam.total_marks || '--'} Marks
            </div>
          </div>
        </div>

        <button 
          className="btn btn-primary w-100 rounded-3 py-2 fw-semibold d-flex align-items-center justify-content-center gap-2"
          onClick={handleViewExam}
        >
          View Exam Details <i className="bi bi-arrow-right"></i>
        </button>
      </div>
    </div>
  );
};

export default UpcomingExamCard;
