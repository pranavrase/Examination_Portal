import React, { useState } from 'react';

const TestCaseEditor = ({ testCases = [], onChange }) => {
  const [editingIndex, setEditingIndex] = useState(null);
  const [formInput, setFormInput] = useState('');
  const [formOutput, setFormOutput] = useState('');
  const [isSample, setIsSample] = useState(false);
  const [formExplanation, setFormExplanation] = useState('');
  const [showForm, setShowForm] = useState(false);

  const resetForm = () => {
    setFormInput('');
    setFormOutput('');
    setIsSample(false);
    setFormExplanation('');
    setEditingIndex(null);
    setShowForm(false);
  };

  const handleOpenAdd = () => {
    resetForm();
    setShowForm(true);
  };

  const handleOpenEdit = (index) => {
    const tc = testCases[index];
    setFormInput(tc.input || '');
    setFormOutput(tc.expected_output || tc.output || '');
    setIsSample(!!tc.is_sample);
    setFormExplanation(tc.explanation || '');
    setEditingIndex(index);
    setShowForm(true);
  };

  const handleSave = () => {
    if (!formInput.trim() || !formOutput.trim()) {
      alert('Input and Expected Output are required.');
      return;
    }

    const newTC = {
      input: formInput,
      expected_output: formOutput,
      is_sample: isSample,
      explanation: formExplanation
    };

    let updated = [];
    if (editingIndex !== null) {
      updated = [...testCases];
      updated[editingIndex] = newTC;
    } else {
      updated = [...testCases, newTC];
    }

    onChange(updated);
    resetForm();
  };

  const handleDelete = (index) => {
    const updated = testCases.filter((_, i) => i !== index);
    onChange(updated);
  };

  return (
    <div className="card border-0 bg-light rounded-4 p-3 mb-3">
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h6 className="fw-bold mb-0 text-dark">
            <i className="bi bi-file-earmark-code me-2 text-primary"></i>
            Test Cases ({testCases.length})
          </h6>
          <small className="text-muted">Define sample & evaluation test cases for code execution</small>
        </div>
        {!showForm && (
          <button 
            type="button" 
            className="btn btn-sm btn-outline-primary rounded-3 d-flex align-items-center gap-1"
            onClick={handleOpenAdd}
          >
            <i className="bi bi-plus-circle"></i> Add Test Case
          </button>
        )}
      </div>

      {/* Test Cases List */}
      {testCases.length === 0 && !showForm ? (
        <div className="text-center py-4 bg-white rounded-3 border border-dashed">
          <i className="bi bi-terminal fs-3 text-muted"></i>
          <p className="small text-muted mb-0 mt-1">No test cases added yet. Click "Add Test Case" to begin.</p>
        </div>
      ) : (
        <div className="row g-2 mb-3">
          {testCases.map((tc, idx) => (
            <div key={idx} className="col-12">
              <div className="card border-0 shadow-sm rounded-3 bg-white p-3">
                <div className="d-flex justify-content-between align-items-start mb-2">
                  <div className="d-flex align-items-center gap-2">
                    <span className="badge bg-secondary">Case #{idx + 1}</span>
                    {tc.is_sample ? (
                      <span className="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25">
                        <i className="bi bi-eye me-1"></i> Sample Test Case
                      </span>
                    ) : (
                      <span className="badge bg-purple bg-opacity-10 text-purple border border-purple border-opacity-25">
                        <i className="bi bi-eye-slash me-1"></i> Hidden Test Case
                      </span>
                    )}
                  </div>
                  <div className="d-flex gap-1">
                    <button 
                      type="button" 
                      className="btn btn-sm btn-light text-primary py-0 px-2"
                      onClick={() => handleOpenEdit(idx)}
                      title="Edit"
                    >
                      <i className="bi bi-pencil-fill"></i>
                    </button>
                    <button 
                      type="button" 
                      className="btn btn-sm btn-light text-danger py-0 px-2"
                      onClick={() => handleDelete(idx)}
                      title="Delete"
                    >
                      <i className="bi bi-trash-fill"></i>
                    </button>
                  </div>
                </div>

                <div className="row g-2 font-monospace small">
                  <div className="col-md-6">
                    <div className="bg-light p-2 rounded border">
                      <div className="text-muted fw-bold mb-1 font-sans-serif" style={{ fontSize: '0.72rem' }}>STDIN INPUT</div>
                      <pre className="mb-0 text-dark" style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>{tc.input}</pre>
                    </div>
                  </div>
                  <div className="col-md-6">
                    <div className="bg-light p-2 rounded border">
                      <div className="text-muted fw-bold mb-1 font-sans-serif" style={{ fontSize: '0.72rem' }}>EXPECTED STDOUT</div>
                      <pre className="mb-0 text-success fw-bold" style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>{tc.expected_output || tc.output}</pre>
                    </div>
                  </div>
                </div>

                {tc.explanation && (
                  <div className="small text-muted mt-2">
                    <strong>Explanation:</strong> {tc.explanation}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Form */}
      {showForm && (
        <div className="card border-primary rounded-3 p-3 bg-white shadow-sm mt-2">
          <h6 className="fw-bold mb-3 text-primary">
            {editingIndex !== null ? `Edit Test Case #${editingIndex + 1}` : 'New Test Case'}
          </h6>

          <div className="mb-3">
            <label className="form-label small fw-bold">Input (stdin) <span className="text-danger">*</span></label>
            <textarea
              className="form-control font-monospace small bg-light"
              rows="3"
              placeholder="e.g. 5&#10;1 2 3 4 5"
              value={formInput}
              onChange={(e) => setFormInput(e.target.value)}
            ></textarea>
          </div>

          <div className="mb-3">
            <label className="form-label small fw-bold">Expected Output (stdout) <span className="text-danger">*</span></label>
            <textarea
              className="form-control font-monospace small bg-light"
              rows="3"
              placeholder="e.g. 15"
              value={formOutput}
              onChange={(e) => setFormOutput(e.target.value)}
            ></textarea>
          </div>

          <div className="mb-3">
            <label className="form-label small fw-bold">Explanation (Optional)</label>
            <input
              type="text"
              className="form-control form-control-sm bg-light"
              placeholder="Explanation shown for sample test cases..."
              value={formExplanation}
              onChange={(e) => setFormExplanation(e.target.value)}
            />
          </div>

          <div className="form-check form-switch mb-3">
            <input
              className="form-check-input"
              type="checkbox"
              id="isSampleCheck"
              checked={isSample}
              onChange={(e) => setIsSample(e.target.checked)}
            />
            <label className="form-check-label small fw-semibold" htmlFor="isSampleCheck">
              Mark as Sample Test Case (Visible to candidate during examination)
            </label>
          </div>

          <div className="d-flex justify-content-end gap-2">
            <button type="button" className="btn btn-sm btn-light" onClick={resetForm}>
              Cancel
            </button>
            <button type="button" className="btn btn-sm btn-primary" onClick={handleSave}>
              <i className="bi bi-check-lg me-1"></i> {editingIndex !== null ? 'Update Case' : 'Add Case'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TestCaseEditor;
