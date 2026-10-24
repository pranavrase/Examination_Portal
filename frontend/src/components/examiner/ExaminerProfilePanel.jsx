import React, { useEffect, useState } from 'react';
import { getExaminerProfile, updateExaminerProfile, changeExaminerPassword } from '../../api/examinerApi';

const ExaminerProfilePanel = () => {
  const [profile, setProfile] = useState({
    full_name: '',
    email: '',
    department: 'Computer Science & Engineering',
    contact_phone: '+91 98765 43210',
    institution: 'National Institute of Technology',
  });
  const [loading, setLoading] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);
  const [passSaving, setPassSaving] = useState(false);
  const [profileMsg, setProfileMsg] = useState(null);
  const [passMsg, setPassMsg] = useState(null);

  // Password fields
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const data = await getExaminerProfile();
      if (data) setProfile(data);
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    try {
      setProfileSaving(true);
      setProfileMsg(null);
      await updateExaminerProfile(profile);
      setProfileMsg({ type: 'success', text: 'Examiner profile details updated successfully!' });
    } catch (err) {
      setProfileMsg({ type: 'danger', text: err?.response?.data?.detail || 'Profile update failed' });
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPassMsg({ type: 'danger', text: 'New passwords do not match' });
      return;
    }
    try {
      setPassSaving(true);
      setPassMsg(null);
      await changeExaminerPassword({ current_password: currentPassword, new_password: newPassword });
      setPassMsg({ type: 'success', text: 'Security credentials updated successfully!' });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPassMsg({ type: 'danger', text: err?.response?.data?.detail || 'Failed to change password' });
    } finally {
      setPassSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="card border-0 shadow-sm rounded-4 p-5 text-center mb-4">
        <div className="spinner-border text-warning" role="status" />
        <p className="text-muted small mt-2">Loading profile settings...</p>
      </div>
    );
  }

  return (
    <div className="row g-4" id="examiner-profile-panel">
      {/* Profile Overview & Edit */}
      <div className="col-lg-7">
        <div className="card border-0 shadow-sm rounded-4 p-4">
          <div className="d-flex align-items-center gap-3 mb-4 pb-3 border-bottom">
            <div
              className="rounded-circle bg-warning bg-opacity-20 text-warning border border-warning border-opacity-25 fw-bold d-flex align-items-center justify-content-center fs-3"
              style={{ width: 64, height: 64 }}
            >
              {profile.full_name?.charAt(0) || 'E'}
            </div>
            <div>
              <span className="badge bg-warning text-dark mb-1 text-uppercase fw-semibold">
                Faculty / Test Creator Account
              </span>
              <h5 className="fw-bold mb-0 text-dark">{profile.full_name || 'Examiner'}</h5>
              <div className="text-muted small">{profile.email}</div>
            </div>
          </div>

          {profileMsg && (
            <div className={`alert alert-${profileMsg.type} alert-dismissible fade show py-2 small rounded-3 mb-3`} role="alert">
              <i className={`bi ${profileMsg.type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'} me-2`} />
              <span>{profileMsg.text}</span>
              <button type="button" className="btn-close py-2" onClick={() => setProfileMsg(null)} />
            </div>
          )}

          <form onSubmit={handleProfileSubmit} className="d-flex flex-column gap-3">
            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  className="form-control rounded-3"
                  value={profile.full_name || ''}
                  onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  required
                />
              </div>

              <div className="col-md-6">
                <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  className="form-control rounded-3"
                  value={profile.email || ''}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="row g-3">
              <div className="col-md-6">
                <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                  Academic Department
                </label>
                <input
                  type="text"
                  className="form-control rounded-3"
                  value={profile.department || ''}
                  onChange={(e) => setProfile({ ...profile, department: e.target.value })}
                />
              </div>

              <div className="col-md-6">
                <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                  Contact Phone
                </label>
                <input
                  type="text"
                  className="form-control rounded-3"
                  value={profile.contact_phone || ''}
                  onChange={(e) => setProfile({ ...profile, contact_phone: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Institution / University
              </label>
              <input
                type="text"
                className="form-control rounded-3"
                value={profile.institution || ''}
                onChange={(e) => setProfile({ ...profile, institution: e.target.value })}
              />
            </div>

            <button
              type="submit"
              className="btn btn-warning text-dark fw-semibold rounded-3 py-2 mt-2 align-self-start px-4 shadow-sm"
              disabled={profileSaving}
            >
              {profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}
            </button>
          </form>
        </div>
      </div>

      {/* Change Password & Security */}
      <div className="col-lg-5">
        <div className="card border-0 shadow-sm rounded-4 p-4 h-100">
          <span className="badge bg-danger text-white mb-1 text-uppercase fw-semibold align-self-start">
            Security & Authentication
          </span>
          <h5 className="fw-bold mb-1 text-dark">Change Password</h5>
          <p className="text-muted small mb-3">Ensure your account uses a strong cryptographic password</p>

          {passMsg && (
            <div className={`alert alert-${passMsg.type} alert-dismissible fade show py-2 small rounded-3 mb-3`} role="alert">
              <i className={`bi ${passMsg.type === 'success' ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill'} me-2`} />
              <span>{passMsg.text}</span>
              <button type="button" className="btn-close py-2" onClick={() => setPassMsg(null)} />
            </div>
          )}

          <form onSubmit={handlePasswordSubmit} className="d-flex flex-column gap-3">
            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Current Password <span className="text-danger">*</span>
              </label>
              <input
                type="password"
                className="form-control rounded-3"
                placeholder="••••••••"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                New Password <span className="text-danger">*</span>
              </label>
              <input
                type="password"
                className="form-control rounded-3"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <div>
              <label className="form-label small fw-semibold text-muted text-uppercase mb-1">
                Confirm New Password <span className="text-danger">*</span>
              </label>
              <input
                type="password"
                className="form-control rounded-3"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <button
              type="submit"
              className="btn btn-outline-danger rounded-3 py-2 mt-2"
              disabled={passSaving}
            >
              {passSaving ? 'Updating Password...' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ExaminerProfilePanel;
