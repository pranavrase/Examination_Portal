import React, { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { CodingExamProvider, useCodingExam } from '../../context/CodingExamContext';
import { ExamAttemptProvider, useExamAttempt } from '../../context/ExamAttemptContext';
import CodingExamLayout from '../../layouts/CodingExamLayout';

const CodingExamContent = ({ examId }) => {
  const { fetchQuestions } = useCodingExam();

  useEffect(() => {
    fetchQuestions(examId);
  }, [examId, fetchQuestions]);

  return <CodingExamLayout />;
};

const CodingExamPageInner = ({ examId }) => {
  const { attemptId } = useExamAttempt();
  
  return (
    <CodingExamProvider examId={examId} attemptId={attemptId}>
      <CodingExamContent examId={examId} />
    </CodingExamProvider>
  );
};

const CodingExamPage = () => {
  const { examId } = useParams();

  return (
    <ExamAttemptProvider attemptId={examId || 'attempt_101'} initialDurationMinutes={60}>
      <CodingExamPageInner examId={examId || 'default'} />
    </ExamAttemptProvider>
  );
};

export default CodingExamPage;
