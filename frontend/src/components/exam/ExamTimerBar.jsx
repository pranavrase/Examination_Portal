import React from 'react';
import { useExamAttempt } from '../../context/ExamAttemptContext';
import useExamTimer from '../../hooks/useExamTimer';

const ExamTimerBar = () => {
  // Drives the 1s tick & server resync hooks
  useExamTimer();

  const {
    remainingSeconds,
    totalDurationSeconds,
    isExpired,
    isSyncing,
    syncError,
    formatTime,
  } = useExamAttempt();

  const { formatted } = formatTime(remainingSeconds);
  const percentRemaining = totalDurationSeconds > 0
    ? Math.max(0, Math.min(100, (remainingSeconds / totalDurationSeconds) * 100))
    : 0;

  // Determine Urgency Styles
  let colorBadge = 'bg-primary';
  let isPulsing = false;

  if (isExpired) {
    colorBadge = 'bg-secondary';
  } else if (remainingSeconds <= 60) {
    colorBadge = 'bg-danger';
    isPulsing = true;
  } else if (remainingSeconds <= 300) {
    colorBadge = 'bg-warning text-dark';
  }

  return (
    <div className="exam-timer-bar d-flex align-items-center gap-2 font-monospace">
      {/* Timer Container */}
      <div className={`d-flex align-items-center gap-2 px-3 py-1 rounded-3 ${colorBadge} shadow-sm ${isPulsing ? 'animate-pulse' : ''}`}>
        <i className="bi bi-clock-history fs-6"></i>
        <div className="d-flex flex-column text-start" style={{ lineHeight: '1.1' }}>
          <span className="text-uppercase tracking-wider opacity-75" style={{ fontSize: '0.65rem' }}>
            Time Remaining
          </span>
          <span className="fw-bold fs-6">{isExpired ? '00:00:00' : formatted}</span>
        </div>

        {/* Server Sync Status Indicator */}
        {isSyncing ? (
          <span className="spinner-border spinner-border-sm ms-1 opacity-75" title="Resynchronizing with server clock..." style={{ width: '12px', height: '12px' }}></span>
        ) : syncError ? (
          <i className="bi bi-wifi-off text-warning ms-1" title="Offline countdown active (server resync retrying)"></i>
        ) : null}
      </div>

      {/* Progress Bar (Compact) */}
      <div className="progress d-none d-sm-block" style={{ width: '60px', height: '6px' }}>
        <div
          className={`progress-bar ${remainingSeconds <= 60 ? 'bg-danger' : remainingSeconds <= 300 ? 'bg-warning' : 'bg-primary'}`}
          role="progressbar"
          style={{ width: `${percentRemaining}%` }}
        ></div>
      </div>
    </div>
  );
};

export default ExamTimerBar;
