import axiosInstance from './axiosInstance';

// ─── 1. Stats & Overview ───────────────────────────────────────────────────────

export const getExaminerStats = async () => {
  const response = await axiosInstance.get('/examiner/stats');
  return response.data;
};

// ─── 2. Examinations Management ────────────────────────────────────────────────

export const getMyExams = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/exams', { params });
  return response.data;
};

export const getExamById = async (examId) => {
  const response = await axiosInstance.get(`/examiner/exams/${examId}`);
  return response.data;
};

export const createExam = async (examData) => {
  const response = await axiosInstance.post('/examiner/exams', examData);
  return response.data;
};

export const updateExam = async (examId, examData) => {
  const response = await axiosInstance.put(`/examiner/exams/${examId}`, examData);
  return response.data;
};

export const deleteExam = async (examId) => {
  const response = await axiosInstance.delete(`/examiner/exams/${examId}`);
  return response.data;
};

export const duplicateExam = async (examId) => {
  const response = await axiosInstance.post(`/examiner/exams/${examId}/duplicate`);
  return response.data;
};

export const publishExam = async (examId) => {
  const response = await axiosInstance.patch(`/examiner/exams/${examId}/publish`);
  return response.data;
};

export const generateExamPaper = async (examId, distributionData) => {
  const response = await axiosInstance.post(`/examiner/exams/${examId}/generate-paper`, distributionData);
  return response.data;
};

// ─── 3. Questions (Exam-Specific & Bank) ────────────────────────────────────────

export const getQuestionsByExam = async (examId, params = {}) => {
  const response = await axiosInstance.get(`/examiner/exams/${examId}/questions`, { params });
  return response.data;
};

export const createQuestion = async (examId, questionData) => {
  const response = await axiosInstance.post(`/examiner/exams/${examId}/questions`, questionData);
  return response.data;
};

export const updateQuestion = async (examId, questionId, questionData) => {
  const response = await axiosInstance.put(
    `/examiner/exams/${examId}/questions/${questionId}`,
    questionData
  );
  return response.data;
};

export const deleteQuestion = async (examId, questionId) => {
  const response = await axiosInstance.delete(
    `/examiner/exams/${examId}/questions/${questionId}`
  );
  return response.data;
};

// ─── 4. Candidate Management & Assignments ─────────────────────────────────────

export const getCandidates = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/candidates', { params });
  return response.data;
};

export const assignCandidatesToExam = async (examId, assignmentData) => {
  const response = await axiosInstance.post(`/examiner/exams/${examId}/assign`, assignmentData);
  return response.data;
};

export const unassignCandidateFromExam = async (examId, studentId) => {
  const response = await axiosInstance.delete(`/examiner/exams/${examId}/assignments/${studentId}`);
  return response.data;
};

// ─── 5. Live Monitoring ────────────────────────────────────────────────────────

export const getLiveMonitoring = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/monitoring', { params });
  return response.data;
};

// ─── 6. Activity Logs ──────────────────────────────────────────────────────────

export const getExaminerActivityLogs = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/activity-logs', { params });
  return response.data;
};

// ─── 7. Results Management ─────────────────────────────────────────────────────

export const getSubmissionsByExam = async (examId, params = {}) => {
  const response = await axiosInstance.get(`/examiner/exams/${examId}/submissions`, { params });
  return response.data;
};

export const getAllResults = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/results', { params });
  return response.data;
};

export const toggleResultVisibility = async (resultId) => {
  const response = await axiosInstance.post(`/examiner/results/${resultId}/toggle-visibility`);
  return response.data;
};

// ─── 8. Performance Reports ────────────────────────────────────────────────────

export const getPerformanceAnalysis = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/performance', { params });
  return response.data;
};

// ─── 9. Rankings & Leaderboard ─────────────────────────────────────────────────

export const getExaminerRankings = async (params = {}) => {
  const response = await axiosInstance.get('/examiner/rankings', { params });
  return response.data;
};

// ─── 10. Notifications ─────────────────────────────────────────────────────────

export const getExaminerNotifications = async () => {
  const response = await axiosInstance.get('/examiner/notifications');
  return response.data;
};

export const sendExaminerNotification = async (notificationData) => {
  const response = await axiosInstance.post('/examiner/notifications', notificationData);
  return response.data;
};

// ─── 11. Examiner Profile & Password ───────────────────────────────────────────

export const getExaminerProfile = async () => {
  const response = await axiosInstance.get('/examiner/profile');
  return response.data;
};

export const updateExaminerProfile = async (profileData) => {
  const response = await axiosInstance.put('/examiner/profile', profileData);
  return response.data;
};

export const changeExaminerPassword = async (passwordData) => {
  const response = await axiosInstance.put('/examiner/change-password', passwordData);
  return response.data;
};
