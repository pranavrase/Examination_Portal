import axiosInstance from './axiosInstance';

export const getExams = async (params = {}) => {
  const response = await axiosInstance.get('/exams', { params });
  return response.data;
};

export const getExamById = async (examId) => {
  const response = await axiosInstance.get(`/exams/${examId}`);
  return response.data;
};

export const createExam = async (examData) => {
  const response = await axiosInstance.post('/exams', examData);
  return response.data;
};

export const updateExam = async (examId, examData) => {
  const response = await axiosInstance.put(`/exams/${examId}`, examData);
  return response.data;
};

export const deleteExam = async (examId) => {
  const response = await axiosInstance.delete(`/exams/${examId}`);
  return response.data;
};

export const publishExam = async (examId) => {
  const response = await axiosInstance.post(`/exams/${examId}/publish`);
  return response.data;
};

export const assignExam = async (examId, assignmentData) => {
  const response = await axiosInstance.post(`/exams/${examId}/assign`, assignmentData);
  return response.data;
};
