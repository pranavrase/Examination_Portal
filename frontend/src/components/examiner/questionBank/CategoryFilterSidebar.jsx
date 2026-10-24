import React from 'react';

const CATEGORIES = [
  { id: '', label: 'All Categories', icon: 'bi-grid-fill' },
  { id: 'Aptitude', label: 'Aptitude', icon: 'bi-calculator-fill', badge: 'bg-primary' },
  { id: 'Reasoning', label: 'Reasoning', icon: 'bi-puzzle-fill', badge: 'bg-info' },
  { id: 'Technical', label: 'Technical MCQ', icon: 'bi-cpu-fill', badge: 'bg-warning text-dark' },
  { id: 'Coding', label: 'Coding Challenges', icon: 'bi-code-square', badge: 'bg-danger' },
];

const DIFFICULTIES = ['All', 'Easy', 'Medium', 'Hard'];
const QUESTION_TYPES = [
  { id: '', label: 'All Types' },
  { id: 'mcq', label: 'Multiple Choice (MCQ)' },
  { id: 'coding', label: 'Coding Question' },
];

const CategoryFilterSidebar = ({ filters, onFilterChange, onResetFilters }) => {
  return (
    <div className="card shadow-sm border-0 rounded-4 p-3 bg-white">
      <div className="d-flex justify-content-between align-items-center mb-3 px-2">
        <h6 className="fw-bold mb-0 text-uppercase text-secondary tracking-wider" style={{ fontSize: '0.78rem' }}>
          <i className="bi bi-funnel me-1"></i> Filter Questions
        </h6>
        {(filters.category || filters.difficulty || filters.question_type || filters.topic || filters.search) && (
          <button 
            className="btn btn-link btn-sm text-decoration-none p-0 text-danger small fw-semibold"
            onClick={onResetFilters}
          >
            Reset All
          </button>
        )}
      </div>

      {/* Category List */}
      <div className="mb-4">
        <label className="form-label fw-bold text-dark small mb-2">Category</label>
        <div className="list-group list-group-flush border-0">
          {CATEGORIES.map((cat) => {
            const isActive = filters.category === cat.id;
            return (
              <button
                key={cat.id || 'all'}
                type="button"
                className={`list-group-item list-group-item-action d-flex align-items-center justify-content-between rounded-3 mb-1 border-0 py-2 px-3 transition-all ${
                  isActive ? 'bg-primary text-white fw-bold shadow-sm' : 'text-secondary hover-bg-light'
                }`}
                onClick={() => onFilterChange({ category: cat.id })}
              >
                <div className="d-flex align-items-center gap-2">
                  <i className={`bi ${cat.icon} ${isActive ? 'text-white' : 'text-primary'}`}></i>
                  <span className="small">{cat.label}</span>
                </div>
                {cat.badge && !isActive && (
                  <span className={`badge rounded-pill ${cat.badge}`} style={{ fontSize: '0.65rem' }}>
                    {cat.id[0]}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Difficulty Filter */}
      <div className="mb-4">
        <label className="form-label fw-bold text-dark small mb-2">Difficulty</label>
        <div className="d-flex flex-wrap gap-1">
          {DIFFICULTIES.map((diff) => {
            const val = diff === 'All' ? '' : diff;
            const isActive = filters.difficulty === val;
            return (
              <button
                key={diff}
                type="button"
                className={`btn btn-sm flex-fill rounded-3 border-0 transition-all ${
                  isActive
                    ? 'btn-primary fw-bold shadow-sm'
                    : 'btn-light text-secondary hover-bg-light'
                }`}
                style={{ fontSize: '0.78rem' }}
                onClick={() => onFilterChange({ difficulty: val })}
              >
                {diff}
              </button>
            );
          })}
        </div>
      </div>

      {/* Question Type Filter */}
      <div className="mb-4">
        <label className="form-label fw-bold text-dark small mb-2">Question Type</label>
        <select
          className="form-select form-select-sm border-0 bg-light rounded-3"
          value={filters.question_type || ''}
          onChange={(e) => onFilterChange({ question_type: e.target.value })}
        >
          {QUESTION_TYPES.map((type) => (
            <option key={type.id} value={type.id}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {/* Topic Filter */}
      <div>
        <label className="form-label fw-bold text-dark small mb-2">Topic Keyword</label>
        <div className="input-group input-group-sm">
          <span className="input-group-text bg-light border-0">
            <i className="bi bi-tag text-muted"></i>
          </span>
          <input
            type="text"
            className="form-control border-0 bg-light"
            placeholder="e.g. Arrays, Syllogism..."
            value={filters.topic || ''}
            onChange={(e) => onFilterChange({ topic: e.target.value })}
          />
        </div>
      </div>
    </div>
  );
};

export default CategoryFilterSidebar;
