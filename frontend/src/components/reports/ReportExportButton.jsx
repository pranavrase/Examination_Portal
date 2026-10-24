import React, { useState } from 'react';
import { exportReport } from '../../api/reportApi';

/**
 * ReportExportButton
 *
 * Requests a backend-generated report export using the currently applied
 * filters, then triggers a browser file download.
 *
 * Props:
 *  filters    {Object}  – Active filter params to forward to /reports/export
 *  disabled   {boolean} – Disable button (e.g. while report is loading)
 *  className  {string}  – Additional CSS classes
 */
const ReportExportButton = ({ filters = {}, disabled = false, className = '' }) => {
  const [exporting, setExporting] = useState(null); // null | 'csv' | 'pdf'
  const [exportError, setExportError] = useState(null);

  const triggerDownload = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  };

  const handleExport = async (format) => {
    setExporting(format);
    setExportError(null);
    try {
      const response = await exportReport({ ...filters, format });
      const blob = response.data;

      // Derive filename from Content-Disposition header or fallback
      const disposition = response.headers?.['content-disposition'] || '';
      const nameMatch = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      const filename = nameMatch
        ? nameMatch[1].replace(/['"]/g, '')
        : `performance-report-${new Date().toISOString().split('T')[0]}.${format}`;

      triggerDownload(blob, filename);
    } catch (err) {
      const status = err?.response?.status;
      if (status === 403) {
        setExportError('You are not authorized to export this report.');
      } else if (status === 404) {
        setExportError('No data found for the selected filters.');
      } else {
        setExportError(
          err?.response?.data?.detail || 'Export failed. Please try again.'
        );
      }
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className={`d-flex flex-column align-items-end gap-1 ${className}`}>
      <div className="btn-group">
        {/* CSV */}
        <button
          id="report-export-csv"
          className="btn btn-success btn-sm rounded-start-3 d-flex align-items-center gap-2"
          onClick={() => handleExport('csv')}
          disabled={disabled || exporting !== null}
          title="Download filtered report as CSV"
        >
          {exporting === 'csv' ? (
            <>
              <span className="spinner-border spinner-border-sm" />
              Exporting…
            </>
          ) : (
            <>
              <i className="bi bi-filetype-csv" />
              CSV
            </>
          )}
        </button>

        {/* PDF */}
        <button
          id="report-export-pdf"
          className="btn btn-danger btn-sm rounded-end-3 d-flex align-items-center gap-2"
          onClick={() => handleExport('pdf')}
          disabled={disabled || exporting !== null}
          title="Download filtered report as PDF"
        >
          {exporting === 'pdf' ? (
            <>
              <span className="spinner-border spinner-border-sm" />
              Exporting…
            </>
          ) : (
            <>
              <i className="bi bi-filetype-pdf" />
              PDF
            </>
          )}
        </button>
      </div>

      {/* Inline error */}
      {exportError && (
        <div className="text-danger small d-flex align-items-center gap-1 mt-1" style={{ maxWidth: 280 }}>
          <i className="bi bi-exclamation-circle-fill flex-shrink-0" />
          <span>{exportError}</span>
          <button
            type="button"
            className="btn-close btn-close-sm ms-1"
            style={{ fontSize: '0.6rem' }}
            onClick={() => setExportError(null)}
          />
        </div>
      )}
    </div>
  );
};

export default ReportExportButton;
