import React from 'react';

const LANGUAGES = [
  { id: 'python', label: 'Python 3', icon: 'bi-filetype-py' },
  { id: 'cpp', label: 'C++ 17', icon: 'bi-filetype-cpp' },
  { id: 'java', label: 'Java 11', icon: 'bi-filetype-java' },
  { id: 'c', label: 'C', icon: 'bi-file-code' },
  { id: 'javascript', label: 'Node.js (JS)', icon: 'bi-filetype-js' },
];

const LanguageSelector = ({ selectedLanguage, allowedLanguages = [], onSelectLanguage }) => {
  // Filter allowed languages if specified by question
  const availableLangs = allowedLanguages && allowedLanguages.length > 0
    ? LANGUAGES.filter((l) => allowedLanguages.includes(l.id))
    : LANGUAGES;

  return (
    <div className="d-flex align-items-center gap-2">
      <span className="text-secondary small fw-semibold">Language:</span>
      <select
        className="form-select form-select-sm bg-dark text-white border-secondary border-opacity-50 font-monospace rounded-3"
        style={{ width: '150px' }}
        value={selectedLanguage || 'python'}
        onChange={(e) => onSelectLanguage(e.target.value)}
      >
        {availableLangs.map((lang) => (
          <option key={lang.id} value={lang.id}>
            {lang.label}
          </option>
        ))}
      </select>
    </div>
  );
};

export default LanguageSelector;
