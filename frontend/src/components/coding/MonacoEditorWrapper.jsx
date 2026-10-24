import React, { useState, useEffect } from 'react';

// Exact mapping from application language identifiers to Monaco language IDs
const MONACO_LANGUAGE_MAP = {
  python: 'python',
  py: 'python',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  'c++': 'cpp',
  javascript: 'javascript',
  js: 'javascript',
  node: 'javascript',
};

/**
 * Production-Ready Monaco Editor Wrapper for Examination Portal
 *
 * @param {Object} props
 * @param {string} props.value - Controlled code string
 * @param {string} props.language - Language identifier ('python', 'java', 'c', 'cpp', 'javascript')
 * @param {Function} props.onChange - Callback fired when code changes (val: string) => void
 * @param {boolean} [props.readOnly=false] - Read-only mode for student view or completed exams
 * @param {string} [props.height='100%'] - Editor container height
 * @param {string} [props.width='100%'] - Editor container width
 * @param {string} [props.theme='vs-dark'] - Monaco theme ('vs-dark', 'light')
 * @param {Object} [props.options={}] - Custom Monaco options overrides
 */
const MonacoEditorWrapper = ({
  value = '',
  language = 'python',
  onChange = () => {},
  readOnly = false,
  height = '100%',
  width = '100%',
  theme = 'vs-dark',
  options = {},
}) => {
  const [EditorComponent, setEditorComponent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);

  // Normalize language identifier safely
  const monacoLang = MONACO_LANGUAGE_MAP[language?.toLowerCase()?.trim()] || 'python';

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    import('@monaco-editor/react')
      .then((mod) => {
        if (isMounted) {
          setEditorComponent(() => mod.default || mod.Editor);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.warn('Monaco Editor load warning, switching to fallback code editor:', err);
        if (isMounted) {
          setLoadFailed(true);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Default examination-optimized Monaco settings
  const defaultMonacoOptions = {
    readOnly,
    fontSize: 14,
    fontFamily: "'Fira Code', 'Cascadia Code', Consolas, Monaco, monospace",
    minimap: { enabled: false }, // Disabled for clean examination UI
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 4,
    insertSpaces: true,
    lineNumbers: 'on',
    folding: true,
    lineDecorationsWidth: 12,
    lineNumbersMinChars: 3,
    wordWrap: 'on',
    autoIndent: 'full',
    formatOnPaste: true,
    formatOnType: true,
    cursorBlinking: 'smooth',
    cursorSmoothCaretAnimation: 'on',
    bracketPairColorization: { enabled: true },
    guides: {
      bracketPairs: true,
      indentation: true,
    },
    scrollbar: {
      vertical: 'visible',
      horizontal: 'visible',
      verticalScrollbarSize: 10,
      horizontalScrollbarSize: 10,
    },
    suggest: {
      showKeywords: true,
      showSnippets: true,
    },
    renderLineHighlight: 'all',
    ...options,
  };

  // Loading spinner during initialization
  if (loading) {
    return (
      <div
        className="monaco-loading-wrapper d-flex flex-column align-items-center justify-content-center bg-dark text-white rounded-3 border border-secondary border-opacity-25"
        style={{ height, width, minHeight: '350px', background: '#1e1e1e' }}
      >
        <div className="spinner-border text-info mb-2" role="status" style={{ width: '2rem', height: '2rem' }}></div>
        <div className="small font-monospace text-info">Initializing Monaco Code Editor ({monacoLang})...</div>
      </div>
    );
  }

  // Render Monaco Editor when available
  if (EditorComponent && !loadFailed) {
    return (
      <div
        className="monaco-editor-container rounded-3 overflow-hidden border border-secondary border-opacity-25 shadow-sm"
        style={{ height, width, minHeight: '350px' }}
      >
        <EditorComponent
          height="100%"
          width="100%"
          language={monacoLang}
          theme={theme}
          value={value}
          onChange={(newVal) => onChange(newVal || '')}
          options={defaultMonacoOptions}
          loading={
            <div className="d-flex align-items-center justify-content-center h-100 bg-dark text-info font-monospace small">
              <span className="spinner-border spinner-border-sm me-2"></span> Loading Editor Engine...
            </div>
          }
        />
      </div>
    );
  }

  // Fallback Code Editor Textarea (Robust & Offline-Safe)
  const lines = (value || '').split('\n');

  return (
    <div
      className="fallback-code-editor h-100 w-100 d-flex bg-dark text-white rounded-3 overflow-hidden border border-secondary border-opacity-25 font-monospace"
      style={{ height, width, minHeight: '350px', background: '#1e1e1e' }}
    >
      {/* Line Numbers Bar */}
      <div
        className="line-numbers text-secondary text-end select-none py-3 px-2 border-end border-secondary border-opacity-25 bg-black bg-opacity-30"
        style={{ width: '48px', fontSize: '13px', lineHeight: '1.5rem' }}
      >
        {lines.map((_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>

      {/* Code Input Area */}
      <textarea
        className="w-100 h-100 border-0 bg-transparent text-light p-3 font-monospace outline-none resize-none"
        style={{
          fontSize: '13.5px',
          lineHeight: '1.5rem',
          outline: 'none',
          resize: 'none',
          tabSize: 4,
          caretColor: '#38bdf8',
          color: '#e2e8f0',
        }}
        value={value}
        readOnly={readOnly}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (readOnly) return;
          // Tab key indentation handling
          if (e.key === 'Tab') {
            e.preventDefault();
            const start = e.target.selectionStart;
            const end = e.target.selectionEnd;
            const updated = value.substring(0, start) + '    ' + value.substring(end);
            onChange(updated);
            setTimeout(() => {
              e.target.selectionStart = e.target.selectionEnd = start + 4;
            }, 0);
          }
        }}
        placeholder={readOnly ? '// Code viewing mode (Read Only)' : `// Write your ${monacoLang} solution here...`}
        spellCheck="false"
      />
    </div>
  );
};

export default MonacoEditorWrapper;
