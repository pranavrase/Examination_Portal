import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getStudentProfile, updateStudentProfile, changeStudentPassword } from '../../api/studentApi';

const StudentProfilePage = () => {
  const { user, updateUser } = useAuth();

  const [profileData, setProfileData] = useState({
    name: user?.full_name || user?.name || 'Student',
    email: user?.email || '',
    phone: '',
    college: '',
    rollNumber: '',
    avatar: '👨‍🎓',
  });

  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const [isSaved, setIsSaved] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const avatars = ['👨‍🎓', '👩‍🎓', '🧑‍💻', '👩‍💻', '🚀', '⭐', '🧠', '💼'];

  useEffect(() => {
    loadProfileData();
  }, []);

  const loadProfileData = async () => {
    try {
      const data = await getStudentProfile();
      setProfileData(prev => ({
        ...prev,
        name: data.full_name || user?.full_name || user?.name || 'Student',
        email: data.email || user?.email || '',
        phone: data.phone || '',
        college: data.college || '',
        rollNumber: data.roll_number || '',
      }));
    } catch (err) {
      console.error('Failed to load profile data:', err);
    }
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await updateStudentProfile({
        full_name: profileData.name,
        phone: profileData.phone,
        roll_number: profileData.rollNumber,
        college: profileData.college,
      });
      
      // Update user context if available
      if (updateUser) {
        updateUser({ full_name: profileData.name });
      }
      
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError('');

    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      setPasswordError('Passwords do not match.');
      return;
    }

    if (passwordForm.newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters long.');
      return;
    }

    setLoading(true);

    try {
      await changeStudentPassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      });
      
      setPasswordSuccess(true);
      setPasswordForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
      setTimeout(() => setPasswordSuccess(false), 3000);
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password. Please check your current password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-secondary text-uppercase tracking-wider">Account Settings</span>
            <span className="badge bg-light text-secondary border">Role: Student</span>
          </div>
          <h1 className="h4 mb-0 fw-bold">Student Profile & Credentials</h1>
          <p className="text-muted mb-0 small">Manage your academic identification, contact info, security credentials, and active sessions.</p>
        </div>
      </header>

      {/* Profile Form Grid */}
      <div className="row g-4">
        {/* Left Column: Personal Information & Avatar */}
        <div className="col-12 col-lg-7">
          <div className="card shadow-sm border-0 rounded-4 mb-4">
            <div className="card-header bg-white border-bottom p-3">
              <h6 className="mb-0 fw-bold"><i className="bi bi-person-badge-fill text-primary me-2"></i>Personal & Academic Identification</h6>
            </div>
            <div className="card-body p-4">
              {isSaved && (
                <div className="alert alert-success alert-dismissible fade show rounded-3 small mb-3">
                  <i className="bi bi-check-circle-fill me-2"></i>Profile details saved successfully!
                </div>
              )}
              
              {error && (
                <div className="alert alert-danger rounded-3 small mb-3">
                  <i className="bi bi-exclamation-triangle-fill me-2"></i>{error}
                </div>
              )}

              <form onSubmit={handleProfileSubmit}>
                {/* Avatar Picker */}
                <div className="mb-4">
                  <label className="form-label d-block">Candidate Avatar</label>
                  <div className="d-flex align-items-center gap-2 flex-wrap">
                    {avatars.map((av) => (
                      <button
                        key={av}
                        type="button"
                        className={`btn btn-sm rounded-circle fs-4 d-flex align-items-center justify-content-center p-2 ${
                          profileData.avatar === av ? 'btn-primary border-3 shadow-sm' : 'btn-light border'
                        }`}
                        style={{ width: '48px', height: '48px' }}
                        onClick={() => setProfileData((prev) => ({ ...prev, avatar: av }))}
                      >
                        {av}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="row g-3">
                  <div className="col-md-6">
                    <label className="form-label">Full Name</label>
                    <input
                      type="text"
                      className="form-control form-control-sm bg-light"
                      value={profileData.name}
                      onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                      required
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Email Address</label>
                    <input
                      type="email"
                      className="form-control form-control-sm bg-light"
                      value={profileData.email}
                      disabled
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Student ID / Roll Number</label>
                    <input
                      type="text"
                      className="form-control form-control-sm bg-light"
                      value={profileData.rollNumber}
                      onChange={(e) => setProfileData({ ...profileData, rollNumber: e.target.value })}
                      required
                    />
                  </div>

                  <div className="col-md-6">
                    <label className="form-label">Phone Number</label>
                    <input
                      type="text"
                      className="form-control form-control-sm bg-light"
                      value={profileData.phone}
                      onChange={(e) => setProfileData({ ...profileData, phone: e.target.value })}
                    />
                  </div>

                  <div className="col-12">
                    <label className="form-label">College / Department</label>
                    <input
                      type="text"
                      className="form-control form-control-sm bg-light"
                      value={profileData.college}
                      onChange={(e) => setProfileData({ ...profileData, college: e.target.value })}
                    />
                  </div>
                </div>

                <div className="mt-4 text-end">
                  <button type="submit" className="btn btn-primary btn-sm px-4 rounded-3 fw-semibold" disabled={loading}>
                    {loading ? (
                      <>
                        <span className="spinner-border spinner-border-sm me-1"></span>
                        Saving...
                      </>
                    ) : (
                      <>
                        <i className="bi bi-save me-1"></i> Save Changes
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* Right Column: Password Change & Security */}
        <div className="col-12 col-lg-5">
          {/* Password Reset Card */}
          <div className="card shadow-sm border-0 rounded-4 mb-4">
            <div className="card-header bg-white border-bottom p-3">
              <h6 className="mb-0 fw-bold"><i className="bi bi-key-fill text-warning me-2"></i>Update Password</h6>
            </div>
            <div className="card-body p-4">
              {passwordSuccess && (
                <div className="alert alert-success rounded-3 small mb-3">
                  <i className="bi bi-check-circle-fill me-2"></i>Password updated successfully!
                </div>
              )}
              
              {passwordError && (
                <div className="alert alert-danger rounded-3 small mb-3">
                  <i className="bi bi-exclamation-triangle-fill me-2"></i>{passwordError}
                </div>
              )}

              <form onSubmit={handlePasswordSubmit}>
                <div className="mb-3">
                  <label className="form-label">Current Password</label>
                  <input
                    type="password"
                    className="form-control form-control-sm bg-light"
                    value={passwordForm.currentPassword}
                    onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
                    required
                  />
                </div>

                <div className="mb-3">
                  <label className="form-label">New Password</label>
                  <input
                    type="password"
                    className="form-control form-control-sm bg-light"
                    value={passwordForm.newPassword}
                    onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
                    required
                  />
                </div>

                <div className="mb-4">
                  <label className="form-label">Confirm New Password</label>
                  <input
                    type="password"
                    className="form-control form-control-sm bg-light"
                    value={passwordForm.confirmPassword}
                    onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
                    required
                  />
                </div>

                <button type="submit" className="btn btn-outline-warning w-100 btn-sm rounded-3 fw-semibold" disabled={loading}>
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-1"></span>
                      Updating...
                    </>
                  ) : (
                    'Update Credentials'
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* Session Information */}
          <div className="card shadow-sm border-0 rounded-4">
            <div className="card-header bg-white border-bottom p-3">
              <h6 className="mb-0 fw-bold"><i className="bi bi-laptop text-info me-2"></i>Active Session & Device</h6>
            </div>
            <div className="card-body p-3 small">
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">Browser:</span>
                <span className="fw-semibold text-dark">Chrome on Windows</span>
              </div>
              <div className="d-flex justify-content-between mb-2">
                <span className="text-muted">IP Address:</span>
                <span className="fw-semibold text-dark">127.0.0.1 (Local)</span>
              </div>
              <div className="d-flex justify-content-between">
                <span className="text-muted">Security State:</span>
                <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25">Verified</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentProfilePage;
