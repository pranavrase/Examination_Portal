import React, { useEffect } from 'react';
import { useStudent } from '../../context/StudentContext';

const StudentPerformancePage = () => {
  const { results, exams, fetchResults, fetchExams } = useStudent();

  useEffect(() => {
    fetchResults();
    fetchExams();
  }, [fetchResults, fetchExams]);

  // Calculate actual performance metrics from results
  const calculateMetrics = () => {
    if (results.length === 0) {
      return {
        overallAccuracy: 0,
        overallRank: 'N/A',
        totalExamsCompleted: 0,
        avgScore: 0,
        passedCount: 0,
        topicData: []
      };
    }

    // Calculate overall accuracy (average percentage)
    const totalPercentage = results.reduce((sum, result) => {
      const percentage = result.percentage !== undefined 
        ? result.percentage 
        : (result.total_marks_possible ? ((result.score_obtained / result.total_marks_possible) * 100) : 0);
      return sum + percentage;
    }, 0);
    const overallAccuracy = (totalPercentage / results.length).toFixed(1);

    // Get overall rank from most recent result
    const recentResult = results[0];
    const overallRank = recentResult?.rank ? `#${recentResult.rank}` : 'N/A';

    // Count passed exams
    const passedCount = results.filter(r => r.is_passed || r.pass_fail).length;

    // Calculate average score
    const avgScore = (totalPercentage / results.length).toFixed(1);

    // Group by subject/topic for topic-wise performance
    const subjectMap = {};
    results.forEach(result => {
      const subject = result.subject || result.exam?.subject || 'General';
      const percentage = result.percentage !== undefined 
        ? result.percentage 
        : (result.total_marks_possible ? ((result.score_obtained / result.total_marks_possible) * 100) : 0);
      
      if (!subjectMap[subject]) {
        subjectMap[subject] = {
          topic: subject,
          totalScore: 0,
          totalExams: 0,
          percentage: 0
        };
      }
      subjectMap[subject].totalScore += percentage;
      subjectMap[subject].totalExams += 1;
    });

    // Convert to array and calculate averages
    const topicData = Object.values(subjectMap).map(item => ({
      topic: item.topic,
      score: (item.totalScore / item.totalExams).toFixed(1),
      total: 100,
      accuracy: (item.totalScore / item.totalExams).toFixed(1),
      strength: (item.totalScore / item.totalExams) >= 90 ? 'Mastery' : 
                (item.totalScore / item.totalExams) >= 80 ? 'High' : 
                (item.totalScore / item.totalExams) >= 70 ? 'Good' : 'Needs Improvement',
      icon: item.topic.toLowerCase().includes('aptitude') ? 'bi-calculator-fill' :
            item.topic.toLowerCase().includes('reasoning') ? 'bi-lightbulb-fill' :
            item.topic.toLowerCase().includes('technical') || item.topic.toLowerCase().includes('cs') ? 'bi-cpu-fill' :
            item.topic.toLowerCase().includes('coding') || item.topic.toLowerCase().includes('algorithm') ? 'bi-code-slash' :
            'bi-book-fill',
      color: (item.totalScore / item.totalExams) >= 90 ? 'success' :
             (item.totalScore / item.totalExams) >= 80 ? 'primary' :
             (item.totalScore / item.totalExams) >= 70 ? 'info' : 'warning'
    })).sort((a, b) => b.score - a.score);

    return {
      overallAccuracy,
      overallRank,
      totalExamsCompleted: results.length,
      avgScore,
      passedCount,
      topicData
    };
  };

  const metrics = calculateMetrics();

  return (
    <div className="container-fluid py-4 px-lg-4">
      {/* Header */}
      <header className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom gap-3">
        <div>
          <div className="d-flex align-items-center gap-2 mb-1">
            <span className="badge bg-indigo text-white text-uppercase tracking-wider">Skill Intelligence</span>
            <span className="badge bg-light text-secondary border">Continuous Analytics</span>
          </div>
          <h1 className="h4 mb-0 fw-bold">Performance & Competency Analysis</h1>
          <p className="text-muted mb-0 small">In-depth insights into your domain-wise strengths, accuracy rates, and areas for improvement.</p>
        </div>
      </header>

      {/* Top Metric Cards */}
      <div className="row g-3 mb-4">
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 rounded-4 p-3 h-100">
            <div className="text-muted small mb-1">Overall Accuracy</div>
            <h3 className="fw-bold text-success mb-1">{metrics.overallAccuracy}%</h3>
            <div className="small text-muted">
              {parseFloat(metrics.overallAccuracy) >= 80 ? (
                <><i className="bi bi-arrow-up-right text-success me-1"></i>Excellent performance</>
              ) : parseFloat(metrics.overallAccuracy) >= 60 ? (
                <><i className="bi bi-dash text-warning me-1"></i>Good progress</>
              ) : (
                <><i className="bi bi-arrow-down-right text-danger me-1"></i>Needs improvement</>
              )}
            </div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 rounded-4 p-3 h-100">
            <div className="text-muted small mb-1">Current Class Rank</div>
            <h3 className="fw-bold text-primary mb-1">{metrics.overallRank}</h3>
            <div className="small text-muted">
              {metrics.overallRank !== 'N/A' ? `Based on recent performance` : 'Rank not available'}
            </div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 rounded-4 p-3 h-100">
            <div className="text-muted small mb-1">Tests Completed</div>
            <h3 className="fw-bold text-dark mb-1">{metrics.totalExamsCompleted}</h3>
            <div className="small text-muted">{exams.length} total assigned</div>
          </div>
        </div>
        <div className="col-6 col-md-3">
          <div className="card shadow-sm border-0 rounded-4 p-3 h-100">
            <div className="text-muted small mb-1">Tests Passed</div>
            <h3 className="fw-bold text-info mb-1">{metrics.passedCount}</h3>
            <div className="small text-muted">
              {metrics.totalExamsCompleted > 0 
                ? `${((metrics.passedCount / metrics.totalExamsCompleted) * 100).toFixed(0)}% pass rate`
                : 'No completed tests'
              }
            </div>
          </div>
        </div>
      </div>

      {/* Domain Breakdown Section */}
      <div className="row g-4 mb-4">
        <div className="col-12 col-lg-8">
          <div className="card shadow-sm border-0 rounded-4 h-100">
            <div className="card-header bg-white border-bottom p-3 d-flex justify-content-between align-items-center">
              <h6 className="mb-0 fw-bold"><i className="bi bi-pie-chart-fill text-primary me-2"></i>Subject & Topic Performance Matrix</h6>
              <span className="badge bg-light text-dark border">Based on Actual Results</span>
            </div>
            <div className="card-body p-4">
              {metrics.topicData.length > 0 ? (
                <div className="d-flex flex-column gap-4">
                  {metrics.topicData.map((item) => (
                    <div key={item.topic}>
                      <div className="d-flex justify-content-between align-items-center mb-1.5">
                        <div className="d-flex align-items-center gap-2">
                          <div className={`p-1.5 rounded-2 bg-${item.color} bg-opacity-10 text-${item.color}`}>
                            <i className={`bi ${item.icon}`}></i>
                          </div>
                          <span className="fw-bold text-dark">{item.topic}</span>
                          <span className={`badge bg-${item.color} bg-opacity-10 text-${item.color} border border-${item.color} border-opacity-25`}>
                            {item.strength}
                          </span>
                        </div>
                        <div className="text-end">
                          <span className="fw-bold text-dark">{item.score}%</span>
                          <span className="text-muted small ms-2">({item.accuracy}% Accuracy)</span>
                        </div>
                      </div>
                      <div className="progress" style={{ height: '8px', borderRadius: '4px' }}>
                        <div
                          className={`progress-bar bg-${item.color}`}
                          role="progressbar"
                          style={{ width: `${item.score}%` }}
                          aria-valuenow={item.score}
                          aria-valuemin="0"
                          aria-valuemax="100"
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-5 text-muted">
                  <div className="display-4 text-muted mb-2">
                    <i className="bi bi-graph-up"></i>
                  </div>
                  <h6 className="fw-bold">No Performance Data</h6>
                  <p className="small mb-0">Complete some exams to see your subject-wise performance breakdown.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Strengths and Weak Areas */}
        <div className="col-12 col-lg-4">
          <div className="card shadow-sm border-0 rounded-4 h-100">
            <div className="card-header bg-white border-bottom p-3">
              <h6 className="mb-0 fw-bold"><i className="bi bi-bullseye text-danger me-2"></i>Strengths & Improvement Plan</h6>
            </div>
            <div className="card-body p-3">
              {metrics.topicData.length > 0 ? (
                <>
                  <div className="mb-3">
                    <div className="small fw-bold text-success text-uppercase mb-2 d-flex align-items-center gap-1">
                      <i className="bi bi-shield-check"></i> Key Strengths
                    </div>
                    <ul className="list-group list-group-flush small">
                      {metrics.topicData
                        .filter(item => parseFloat(item.score) >= 80)
                        .slice(0, 3)
                        .map((item, idx) => (
                          <li key={idx} className="list-group-item px-0 py-1.5 border-0 d-flex align-items-center gap-2">
                            <i className="bi bi-check-circle-fill text-success"></i> {item.topic} ({item.score}%)
                          </li>
                        ))}
                      {metrics.topicData.filter(item => parseFloat(item.score) >= 80).length === 0 && (
                        <li className="list-group-item px-0 py-1.5 border-0 text-muted">
                          Complete more exams to identify your strengths
                        </li>
                      )}
                    </ul>
                  </div>

                  <hr className="my-3 text-secondary opacity-25" />

                  <div>
                    <div className="small fw-bold text-warning text-uppercase mb-2 d-flex align-items-center gap-1">
                      <i className="bi bi-exclamation-triangle"></i> Target Growth Areas
                    </div>
                    <ul className="list-group list-group-flush small">
                      {metrics.topicData
                        .filter(item => parseFloat(item.score) < 80)
                        .slice(0, 3)
                        .map((item, idx) => (
                          <li key={idx} className="list-group-item px-0 py-1.5 border-0 d-flex align-items-center gap-2">
                            <i className="bi bi-arrow-right-circle text-warning"></i> {item.topic} ({item.score}%)
                          </li>
                        ))}
                      {metrics.topicData.filter(item => parseFloat(item.score) < 80).length === 0 && (
                        <li className="list-group-item px-0 py-1.5 border-0 text-muted">
                          Great job! No major areas for improvement identified
                        </li>
                      )}
                    </ul>
                  </div>
                </>
              ) : (
                <div className="text-center py-4 text-muted">
                  <div className="small">
                    Complete exams to generate personalized strengths and improvement recommendations
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentPerformancePage;
