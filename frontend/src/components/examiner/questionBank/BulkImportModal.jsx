import React, { useState } from 'react';

const BulkImportModal = ({ show, onClose, onImport }) => {
  const [file, setFile] = useState(null);
  const [parsedPreview, setParsedPreview] = useState([]);
  const [validationErrors, setValidationErrors] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  if (!show) return null;

  const handleReset = () => {
    setFile(null);
    setParsedPreview([]);
    setValidationErrors([]);
    setSubmitting(false);
  };

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;

    const fileName = selectedFile.name.toLowerCase();
    if (!fileName.endsWith('.csv') && !fileName.endsWith('.xlsx') && !fileName.endsWith('.xls')) {
      alert('Invalid file format. Please upload a .csv or Excel file.');
      return;
    }

    setFile(selectedFile);
    parseCSV(selectedFile);
  };

  const parseCSV = (fileObj) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const lines = text.split(/\r\n|\n/).filter((l) => l.trim() !== '');

      if (lines.length <= 1) {
        setValidationErrors(['File is empty or contains only a header row.']);
        setParsedPreview([]);
        return;
      }

      const headers = lines[0].split(',').map((h) => h.trim().toLowerCase().replace(/['"]/g, ''));
      const rows = [];
      const errors = [];

      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map((v) => v.trim().replace(/^["']|["']$/g, ''));
        if (values.length < 2) continue;

        const rowObj = {};
        headers.forEach((h, index) => {
          rowObj[h] = values[index] || '';
        });

        // Basic row validation
        const qText = rowObj.question_text || rowObj.question || rowObj.title;
        const category = rowObj.category || 'Aptitude';
        const type = rowObj.type || rowObj.question_type || 'mcq';

        if (!qText) {
          errors.push(`Row ${i}: Missing question text.`);
        }

        rows.push({
          rowNumber: i,
          question_text: qText || 'N/A',
          category: category,
          topic: rowObj.topic || 'General',
          difficulty: rowObj.difficulty || 'Medium',
          question_type: type,
          marks: rowObj.marks || '1',
        });
      }

      setParsedPreview(rows);
      setValidationErrors(errors);
    };

    reader.readAsText(fileObj);
  };

  const handleConfirmImport = async () => {
    if (!file || parsedPreview.length === 0) return;
    try {
      setSubmitting(true);
      const formData = new FormData();
      formData.append('file', file);
      await onImport(formData, parsedPreview);
      handleReset();
      onClose();
    } catch (err) {
      alert(err.message || 'Import failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const downloadSampleCSV = () => {
    const csvContent = `data:text/csv;charset=utf-8,question_text,category,topic,difficulty,question_type,marks,option_a,option_b,option_c,option_d,correct_option
"What is the average of 10, 20, 30?",Aptitude,Averages,Easy,mcq,1,"15","20","25","30","B"
"Solve: If X + Y = 10 and X - Y = 2, find X.",Reasoning,Algebra,Medium,mcq,2,"4","5","6","7","C"
"Write a function to reverse a string.",Coding,Strings,Hard,coding,10,"","","","",""`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'question_import_sample.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="modal d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1050 }}>
      <div className="modal-dialog modal-dialog-centered modal-lg">
        <div className="modal-content border-0 rounded-4 shadow">
          <div className="modal-header border-bottom-0 pb-0">
            <h5 className="modal-title fw-bold">
              <i className="bi bi-file-earmark-spreadsheet me-2 text-success"></i>
              Bulk Import Questions
            </h5>
            <button type="button" className="btn-close" onClick={onClose} disabled={submitting}></button>
          </div>

          <div className="modal-body p-4">
            {/* Instructions & Template */}
            <div className="d-flex justify-content-between align-items-center bg-light p-3 rounded-3 mb-4">
              <div>
                <span className="fw-bold small d-block">Upload CSV or Excel Spreadsheet</span>
                <span className="text-muted small">Import multiple MCQs or Coding questions at once.</span>
              </div>
              <button
                type="button"
                className="btn btn-sm btn-outline-success rounded-3 d-flex align-items-center gap-1"
                onClick={downloadSampleCSV}
              >
                <i className="bi bi-download"></i> Sample CSV
              </button>
            </div>

            {/* Drag & Drop Upload Box */}
            {!file ? (
              <div
                className={`border border-2 border-dashed rounded-4 p-5 text-center transition-all ${
                  isDragOver ? 'border-primary bg-primary bg-opacity-10' : 'border-secondary border-opacity-25 bg-light'
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileChange(e.dataTransfer.files[0]);
                  }
                }}
              >
                <i className="bi bi-cloud-arrow-up display-4 text-primary mb-2"></i>
                <h6 className="fw-bold mb-1">Drag and drop your file here</h6>
                <p className="text-muted small mb-3">Supports .csv, .xlsx, .xls format</p>
                <label className="btn btn-sm btn-primary px-4 rounded-3 cursor-pointer">
                  Browse File
                  <input
                    type="file"
                    accept=".csv, .xlsx, .xls"
                    className="d-none"
                    onChange={(e) => handleFileChange(e.target.files[0])}
                  />
                </label>
              </div>
            ) : (
              <div>
                {/* File Selected Card */}
                <div className="d-flex justify-content-between align-items-center border rounded-3 p-3 mb-3 bg-white">
                  <div className="d-flex align-items-center gap-3">
                    <i className="bi bi-file-earmark-text fs-2 text-success"></i>
                    <div>
                      <h6 className="fw-bold mb-0">{file.name}</h6>
                      <small className="text-muted">{(file.size / 1024).toFixed(1)} KB • {parsedPreview.length} rows detected</small>
                    </div>
                  </div>
                  <button type="button" className="btn btn-sm btn-outline-danger" onClick={handleReset}>
                    Remove
                  </button>
                </div>

                {/* Validation Errors */}
                {validationErrors.length > 0 && (
                  <div className="alert alert-warning py-2 px-3 small rounded-3 mb-3">
                    <i className="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>{validationErrors.length} Warnings Detected:</strong>
                    <ul className="mb-0 mt-1 ps-3">
                      {validationErrors.slice(0, 3).map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                      {validationErrors.length > 3 && <li>...and {validationErrors.length - 3} more.</li>}
                    </ul>
                  </div>
                )}

                {/* Preview Table */}
                <h6 className="fw-bold mb-2 small text-uppercase text-secondary">Parsed Questions Preview</h6>
                <div className="table-responsive border rounded-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                  <table className="table table-sm table-hover align-middle mb-0" style={{ fontSize: '0.78rem' }}>
                    <thead className="table-light sticky-top">
                      <tr>
                        <th>#</th>
                        <th>Question</th>
                        <th>Category</th>
                        <th>Topic</th>
                        <th>Difficulty</th>
                        <th>Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {parsedPreview.map((row) => (
                        <tr key={row.rowNumber}>
                          <td>{row.rowNumber}</td>
                          <td className="fw-semibold text-truncate" style={{ maxWidth: '200px' }}>{row.question_text}</td>
                          <td>{row.category}</td>
                          <td>{row.topic}</td>
                          <td>
                            <span className={`badge ${row.difficulty === 'Easy' ? 'bg-success' : row.difficulty === 'Hard' ? 'bg-danger' : 'bg-warning text-dark'}`}>
                              {row.difficulty}
                            </span>
                          </td>
                          <td className="text-uppercase fw-bold">{row.question_type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          <div className="modal-footer border-top-0 pt-0">
            <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-success px-4"
              disabled={!file || parsedPreview.length === 0 || submitting}
              onClick={handleConfirmImport}
            >
              {submitting ? (
                <><span className="spinner-border spinner-border-sm me-2"></span>Importing...</>
              ) : (
                `Import ${parsedPreview.length} Questions`
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkImportModal;
