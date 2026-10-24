import axiosInstance from './axiosInstance';

/**
 * Get all exams assigned to a student
 * @param {string|number} studentId
 */
export const getStudentExams = async (studentId) => {
  const response = await axiosInstance.get(`/students/${studentId}/exams`);
  return response.data;
};

/**
 * Get all past exam results for a student
 * @param {string|number} studentId
 */
export const getStudentResults = async (studentId) => {
  const response = await axiosInstance.get(`/students/${studentId}/results`);
  return response.data;
};

/**
 * Get student leaderboard data
 * @param {string|number} examId - Optional exam ID for specific exam leaderboard
 */
export const getStudentLeaderboard = async (examId = null) => {
  const params = examId ? { exam_id: examId } : {};
  const response = await axiosInstance.get('/students/leaderboard', { params });
  return response.data;
};

/**
 * Get student profile data
 */
export const getStudentProfile = async () => {
  const response = await axiosInstance.get('/students/profile');
  return response.data;
};

/**
 * Update student profile data
 * @param {Object} profileData - Profile data to update
 */
export const updateStudentProfile = async (profileData) => {
  const response = await axiosInstance.put('/students/profile', profileData);
  return response.data;
};

/**
 * Change student password
 * @param {Object} passwordData - Password change data
 */
export const changeStudentPassword = async (passwordData) => {
  const response = await axiosInstance.post('/students/change-password', passwordData);
  return response.data;
};
