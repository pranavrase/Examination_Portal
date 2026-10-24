import React, { createContext, useContext, useState, useCallback } from 'react';
import { getCodingQuestions, runCode as apiRunCode, submitCode as apiSubmitCode } from '../api/codingApi';

const DEFAULT_TEMPLATES = {
  python: `# Write your Python 3 solution here
# Read input from stdin and print output to stdout
import sys

def solve():
    # Read all input from stdin
    input_data = sys.stdin.read().strip()
    if not input_data:
        return
    
    # Process the input and compute result
    # Example: result = process(input_data)
    result = input_data  # Replace with your actual solution
    
    # Print the result
    print(result)

if __name__ == '__main__':
    solve()
`,
  cpp: `// Write your C++ 17 solution here
#include <iostream>
#include <string>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    // Read input from stdin
    string input;
    getline(cin, input);
    
    // Process the input and compute result
    // Example: string result = process(input);
    string result = input;  // Replace with your actual solution
    
    // Print the result
    cout << result << endl;
    
    return 0;
}
`,
  java: `// Write your Java solution here
import java.util.*;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        
        // Read input from stdin
        String input = sc.nextLine();
        
        // Process the input and compute result
        // Example: String result = process(input);
        String result = input;  // Replace with your actual solution
        
        // Print the result
        System.out.println(result);
    }
}
`,
  c: `// Write your C solution here
#include <stdio.h>
#include <string.h>

int main() {
    char input[100000];
    
    // Read input from stdin
    if (fgets(input, sizeof(input), stdin) == NULL) {
        return 0;
    }
    
    // Remove trailing newline
    input[strcspn(input, "\\n")] = '\\0';
    
    // Process the input and compute result
    // Example: char* result = process(input);
    char* result = input;  // Replace with your actual solution
    
    // Print the result
    printf("%s\\n", result);
    
    return 0;
}
`,
  javascript: `// Write your Node.js solution here
const fs = require('fs');

function main() {
    // Read input from stdin
    const input = fs.readFileSync('/dev/stdin', 'utf-8').trim();
    
    // Process the input and compute result
    // Example: const result = process(input);
    const result = input;  // Replace with your actual solution
    
    // Print the result
    console.log(result);
}

main();
`,
};

const CodingExamContext = createContext(null);

export const CodingExamProvider = ({ children, examId, attemptId: propAttemptId }) => {
  const [questions, setQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  
  // Storage per questionId
  const [questionCodes, setQuestionCodes] = useState({});
  const [questionLanguages, setQuestionLanguages] = useState({});
  const [runResults, setRunResults] = useState({});
  const [submissionResults, setSubmissionResults] = useState({});
  const [questionStatuses, setQuestionStatuses] = useState({});
  
  // Store attempt ID from prop
  const attemptId = propAttemptId;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const currentQuestion = questions[currentQuestionIndex] || null;

  // Initialize questions
  const fetchQuestions = useCallback(async (eId) => {
    const targetId = eId || examId;
    if (!targetId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getCodingQuestions(targetId);
      const qList = Array.isArray(data) ? data : data?.questions || data?.items || [];
      
      setQuestions(qList);

      // Pre-populate initial codes and statuses
      const initCodes = {};
      const initLangs = {};
      const initStatuses = {};

      qList.forEach((q) => {
        const qId = q.id;
        const defaultLang = q.allowed_languages && q.allowed_languages.length > 0 ? q.allowed_languages[0] : 'python';
        initLangs[qId] = defaultLang;
        initCodes[qId] = {
          [defaultLang]: q.starter_code || DEFAULT_TEMPLATES[defaultLang] || '# Write code here',
        };
        initStatuses[qId] = q.is_submitted ? 'submitted' : 'unattempted';
      });

      setQuestionCodes(initCodes);
      setQuestionLanguages(initLangs);
      setQuestionStatuses(initStatuses);
    } catch (err) {
      console.warn('Failed to load coding questions from backend:', err);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load examination questions.');
      setQuestions([]);
    } finally {
      setLoading(false);
    }
  }, [examId]);

  // Active Code for Current Question
  const getCurrentCode = useCallback(() => {
    if (!currentQuestion) return '';
    const qId = currentQuestion.id;
    const lang = questionLanguages[qId] || 'python';
    return questionCodes[qId]?.[lang] || DEFAULT_TEMPLATES[lang] || '';
  }, [currentQuestion, questionLanguages, questionCodes]);

  const getCurrentLanguage = useCallback(() => {
    if (!currentQuestion) return 'python';
    return questionLanguages[currentQuestion.id] || 'python';
  }, [currentQuestion, questionLanguages]);

  // Updates Code for current question & active language
  const setCode = useCallback((newCode) => {
    if (!currentQuestion) return;
    const qId = currentQuestion.id;
    const lang = questionLanguages[qId] || 'python';

    setQuestionCodes((prev) => ({
      ...prev,
      [qId]: {
        ...(prev[qId] || {}),
        [lang]: newCode,
      },
    }));

    // Update status to attempted if unattempted
    setQuestionStatuses((prev) => {
      if (prev[qId] !== 'submitted') {
        return { ...prev, [qId]: 'attempted' };
      }
      return prev;
    });
  }, [currentQuestion, questionLanguages]);

  // Updates Selected Language for current question
  const setLanguage = useCallback((newLang) => {
    if (!currentQuestion) return;
    const qId = currentQuestion.id;

    setQuestionLanguages((prev) => ({
      ...prev,
      [qId]: newLang,
    }));

    // Populate default template if code doesn't exist for this language
    setQuestionCodes((prev) => {
      const qCodeObj = prev[qId] || {};
      if (!qCodeObj[newLang]) {
        return {
          ...prev,
          [qId]: {
            ...qCodeObj,
            [newLang]: DEFAULT_TEMPLATES[newLang] || '',
          },
        };
      }
      return prev;
    });
  }, [currentQuestion]);

  const selectQuestion = useCallback((index) => {
    if (index >= 0 && index < questions.length) {
      setCurrentQuestionIndex(index);
    }
  }, [questions.length]);

  // Execute Code against Sample Test Cases
  const executeRunCode = useCallback(async () => {
    if (!currentQuestion || isRunning) return;
    const qId = currentQuestion.id;
    const code = getCurrentCode();
    const lang = getCurrentLanguage();

    if (!code.trim()) {
      alert('Code cannot be empty.');
      return;
    }

    setIsRunning(true);
    try {
      const res = await apiRunCode({
        question_id: qId,
        code,
        language: lang,
      });

      setRunResults((prev) => ({
        ...prev,
        [qId]: res,
      }));
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Code execution failed. Please check your code or try again.';

      setRunResults((prev) => ({
        ...prev,
        [qId]: {
          verdict: 'Execution Error',
          status: 'error',
          execution_time: '0ms',
          memory_used: '0 MB',
          test_cases: [],
          compile_error: errorMsg,
          error_message: errorMsg,
        },
      }));
    } finally {
      setIsRunning(false);
    }
  }, [currentQuestion, getCurrentCode, getCurrentLanguage, isRunning]);

  // Submit Code for Final Evaluation
  const executeSubmitCode = useCallback(async (attemptIdParam = null) => {
    if (!currentQuestion || isSubmitting) return;
    const qId = currentQuestion.id;
    const code = getCurrentCode();
    const lang = getCurrentLanguage();

    if (!code.trim()) {
      alert('Code cannot be empty.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Use the provided attempt ID, context attempt ID, or fall back to null (backend will find active attempt)
      const attemptIdToUse = attemptIdParam || attemptId || null;
      
      const res = await apiSubmitCode({
        question_id: qId,
        code,
        language: lang,
        attempt_id: attemptIdToUse,
      });

      setSubmissionResults((prev) => ({
        ...prev,
        [qId]: res,
      }));

      setQuestionStatuses((prev) => ({
        ...prev,
        [qId]: 'submitted',
      }));
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Final code submission failed.';

      setSubmissionResults((prev) => ({
        ...prev,
        [qId]: {
          verdict: 'Submission Error',
          status: 'error',
          total_test_cases: 0,
          passed_test_cases: 0,
          compile_error: errorMsg,
          error_message: errorMsg,
        },
      }));
    } finally {
      setIsSubmitting(false);
    }
  }, [currentQuestion, getCurrentCode, getCurrentLanguage, isSubmitting, attemptId]);

  const value = {
    questions,
    currentQuestionIndex,
    currentQuestion,
    loading,
    error,
    isRunning,
    isSubmitting,
    runResults,
    submissionResults,
    questionStatuses,
    // Expose raw maps so AutoSave can snapshot all drafts at once
    questionCodes,
    questionLanguages,
    getCurrentCode,
    getCurrentLanguage,
    setCode,
    setLanguage,
    selectQuestion,
    executeRunCode,
    executeSubmitCode,
    fetchQuestions,
  };

  return <CodingExamContext.Provider value={value}>{children}</CodingExamContext.Provider>;
};

export const useCodingExam = () => {
  const ctx = useContext(CodingExamContext);
  if (!ctx) throw new Error('useCodingExam must be used within CodingExamProvider');
  return ctx;
};

export default CodingExamContext;