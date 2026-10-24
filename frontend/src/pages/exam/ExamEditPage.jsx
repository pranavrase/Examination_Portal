import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useExam } from '../../context/ExamContext';
import ExamEditForm from '../../components/exam/ExamEditForm';
import ExamSettingsPanel from '../../components/exam/ExamSettingsPanel';
import ExamCreateForm from '../../components/exam/ExamCreateForm';
import ExamPublishModal from '../../components/exam/ExamPublishModal';
import AssignExamToStudentsModal from '../../components/exam/AssignExamToStudentsModal';

const ExamEditPage = ({ isCreate = false }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { currentExam, fetchExamById, loading, error, setCurrentExam, clearMessages } = useExam();

  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);

  useEffect(() => {
    clearMessages();
    if (isCreate) {
      setCurrentExam(null);
    } else if (id) {
      fetchExamById(id);
    }
    
    return () => {
      clearMessages();
      setCurrentExam(null);
    };
  }, [id, isCreate, fetchExamById, setCurrentExam, clearMessages]);

  if (isCreate) {
    return (
      <div className="container py-4">
        <header className="mb-4 pb-3 border-bottom d-flex align-items-center gap-3">
          <button className="btn btn-light rounded-circle" onClick={() => navigate('/exams')}>
            <i className="bi bi-arrow-left"></i>
          </button>
          <div>
            <h1 className="h3 mb-0 fw-bold">New Examination</h1>
            <p className="text-muted mb-0">Start by providing basic exam details.</p>
          </div>
        </header>
        <div className="row justify-content-center">
          <div className="col-lg-8">
            <ExamCreateForm />
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="container py-5 text-center">
        <div className="spinner-border text-primary" role="status"></div>
        <p className="mt-3 text-muted">Loading exam details...</p>
      </div>
    );
  }

  if (error || !currentExam) {
    return (
      <div className="container py-5">
        <div className="alert alert-danger rounded-4 p-4 text-center">
          <h4 className="alert-heading"><i className="bi bi-exclamation-triangle-fill"></i> Error</h4>
          <p>{error || 'Exam not found.'}</p>
          <button className="btn btn-outline-danger mt-3" onClick={() => navigate('/exams')}>
            Back to Exams
          </button>
        </div>
      </div>
    );
  }

  const isPublished = currentExam.status === 'published';

  return (
    <div className="container py-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div className="d-flex align-items-center gap-3">
          <button className="btn btn-light rounded-circle" onClick={() => navigate('/exams')}>
            <i className="bi bi-arrow-left"></i>
          </button>
          <div>
            <div className="d-flex align-items-center gap-2 mb-1">
              <h1 className="h3 mb-0 fw-bold text-truncate" style={{ maxWidth: '400px' }}>
                {currentExam.title}
              </h1>
              {isPublished ? (
                <span className="badge bg-success bg-opacity-10 text-success">Published</span>
              ) : (
                <span className="badge bg-secondary bg-opacity-10 text-secondary">Draft</span>
              )}
            </div>
            <p className="text-muted mb-0 small">ID: {currentExam.id}</p>
          </div>
        </div>
        
        <div className="d-flex gap-2">
          <button 
            className="btn btn-outline-primary"
            onClick={() => setShowAssignModal(true)}
          >
            <i className="bi bi-people"></i> Assign
          </button>
          
          <button 
            className="btn btn-outline-info"
            onClick={() => navigate(`/exams/${currentExam.id}/questions`)}
          >
            <i className="bi bi-list-check"></i> Questions
          </button>
          
          {!isPublished && (
            <button 
              className="btn btn-success"
              onClick={() => setShowPublishModal(true)}
            >
              <i className="bi bi-send-check"></i> Publish
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="row g-4">
        <div className="col-lg-6">
          <ExamEditForm />
        </div>
        <div className="col-lg-6">
          <ExamSettingsPanel />
        </div>
      </div>

      {/* Modals */}
      <ExamPublishModal 
        show={showPublishModal} 
        onClose={() => setShowPublishModal(false)} 
      />
      <AssignExamToStudentsModal 
        show={showAssignModal} 
        onClose={() => setShowAssignModal(false)} 
      />
    </div>
  );
};

export default ExamEditPage;
