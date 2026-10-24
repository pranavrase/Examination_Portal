import React from 'react';

/**
 * AutoSaveIndicator
 *
 * A compact status badge displayed in the IDE header bar that shows
 * the current state of the auto-save system: idle, saving, saved, or error.
 *
 * Props:
 *  @param {'idle'|'saving'|'saved'|'error'} status   - Current save status
 *  @param {Date|null}                        lastSavedAt - Timestamp of last successful save
 *  @param {string|null}                      errorMsg    - Error message when status === 'error'
 */
const AutoSaveIndicator = ({ status = 'idle', lastSavedAt = null, errorMsg = null }) => {
  // --- Format relative "last saved" time ---
  const formatSavedAt = (date) => {
    if (!date) return '';
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);
    if (diffSec < 5) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin === 1) return '1 min ago';
    return `${diffMin} mins ago`;
  };

  // --- Render States ---
  if (status === 'saving') {
    return (
      <div
        className="d-flex align-items-center gap-2 px-3 py-1 rounded-3 bg-dark border border-secondary border-opacity-25 text-secondary"
        style={{ fontSize: '0.75rem', minWidth: '120px' }}
        title="Auto-saving your progress..."
      >
        <span
          className="spinner-border spinner-border-sm text-primary"
          role="status"
          style={{ width: '12px', height: '12px', borderWidth: '2px' }}
        />
        <span className="text-primary fw-semibold">Saving…</span>
      </div>
    );
  }

  if (status === 'saved') {
    return (
      <div
        className="d-flex align-items-center gap-2 px-3 py-1 rounded-3 bg-dark border border-success border-opacity-25 text-success"
        style={{ fontSize: '0.75rem', minWidth: '120px' }}
        title={`Progress saved at ${lastSavedAt?.toLocaleTimeString?.() || ''}`}
      >
        <i className="bi bi-cloud-check-fill text-success" style={{ fontSize: '0.85rem' }} />
        <span className="fw-semibold">
          Saved{' '}
          <span className="text-secondary fw-normal opacity-75">
            {formatSavedAt(lastSavedAt)}
          </span>
        </span>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div
        className="d-flex align-items-center gap-2 px-3 py-1 rounded-3 bg-dark border border-warning border-opacity-50 text-warning"
        style={{ fontSize: '0.75rem', minWidth: '120px', cursor: 'help' }}
        title={errorMsg || 'Auto-save failed. Will retry automatically.'}
      >
        <i className="bi bi-cloud-slash-fill" style={{ fontSize: '0.85rem' }} />
        <span className="fw-semibold">Save failed</span>
      </div>
    );
  }

  // 'idle' – show a subtle cloud icon, no text
  return (
    <div
      className="d-flex align-items-center gap-2 px-3 py-1 rounded-3 text-secondary"
      style={{ fontSize: '0.75rem', minWidth: '120px', opacity: 0.5 }}
      title="Auto-save active"
    >
      <i className="bi bi-cloud" style={{ fontSize: '0.85rem' }} />
      <span className="d-none d-sm-inline">Auto-save on</span>
    </div>
  );
};

export default AutoSaveIndicator;
