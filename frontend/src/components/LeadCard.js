import React from 'react';
import './LeadCard.css';

const LeadCard = ({ lead }) => {
  const getScoreColor = (score) => {
    if (score >= 80) return '#2ecc71';
    if (score >= 60) return '#f39c12';
    return '#e74c3c';
  };

  const getIndustryIcon = (industry) => {
    const icons = {
      'ai': '🤖',
      'saas': '☁️',
      'fintech': '💰',
      'ecommerce': '🛒',
      'health-care': '🏥',
      'other': '🏢',
      'unknown': '❓'
    };
    return icons[industry] || icons.unknown;
  };

  const getCompanySizeLabel = (size) => {
    const labels = {
      'small': 'Small (<50)',
      'medium': 'Medium (50-250)',
      'large': 'Large (250-1000)',
      'enterprise': 'Enterprise (>1000)',
      'unknown': 'Unknown'
    };
    return labels[size] || size;
  };

  return (
    <div className="lead-card">
      <div className="lead-card-header">
        <div className="lead-title">
          <span className="lead-icon">{getIndustryIcon(lead.industry)}</span>
          <h3>{lead.company_name}</h3>
        </div>
        
        <div className="lead-score" style={{ color: getScoreColor(lead.research_confidence * 100) }}>
          {Math.round(lead.research_confidence * 100)}%
        </div>
      </div>

      <div className="lead-card-body">
        {/* Basic Info */}
        <div className="lead-info">
          <div className="info-row">
            <span className="info-label">Website:</span>
            <a 
              href={lead.company_website} 
              target="_blank" 
              rel="noopener noreferrer"
              className="info-value link"
            >
              {lead.domain}
            </a>
          </div>
          
          <div className="info-row">
            <span className="info-label">Industry:</span>
            <span className="info-value">
              <span className="badge">{lead.industry}</span>
            </span>
          </div>
          
          <div className="info-row">
            <span className="info-label">Size:</span>
            <span className="info-value">{getCompanySizeLabel(lead.company_size)}</span>
          </div>
          
          {lead.qualification_score !== undefined && (
            <div className="info-row">
              <span className="info-label">Qualification:</span>
              <span className="info-value">
                <span 
                  className="badge" 
                  style={{ 
                    backgroundColor: getScoreColor(lead.qualification_score),
                    color: 'white'
                  }}
                >
                  {lead.qualification_score} pts
                </span>
                {lead.qualified && <span className="qualified-badge">✓ Qualified</span>}
              </span>
            </div>
          )}
        </div>

        {/* Decision Makers */}
        {lead.decision_makers && lead.decision_makers.length > 0 && (
          <div className="lead-section">
            <div className="section-label">Decision Makers:</div>
            <div className="tags">
              {lead.decision_makers.map((role, idx) => (
                <span key={idx} className="tag">{role}</span>
              ))}
            </div>
          </div>
        )}

        {/* Intent Signals */}
        {lead.intent_signals && lead.intent_signals.length > 0 && (
          <div className="lead-section">
            <div className="section-label">Intent Signals:</div>
            <div className="tags">
              {lead.intent_signals.map((signal, idx) => (
                <span key={idx} className="tag tag-info">{signal}</span>
              ))}
            </div>
            <div className="intent-confidence">
              Confidence: <span className={`confidence-${lead.intent_confidence}`}>
                {lead.intent_confidence}
              </span>
            </div>
          </div>
        )}

        {/* Pain Points */}
        {lead.pain_points && lead.pain_points.length > 0 && (
          <div className="lead-section">
            <div className="section-label">Pain Points:</div>
            <div className="tags">
              {lead.pain_points.map((point, idx) => (
                <span key={idx} className="tag tag-warning">{point}</span>
              ))}
            </div>
          </div>
        )}

        {/* Emails */}
        {lead.validated_emails && lead.validated_emails.length > 0 && (
          <div className="lead-section">
            <div className="section-label">Emails:</div>
            <div className="emails">
              {lead.validated_emails.map((email, idx) => (
                <div key={idx} className="email">
                  <span className="email-address">{email}</span>
                  <span className={`email-quality ${lead.email_quality}`}>
                    {lead.email_quality}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Website Summary */}
        {lead.website_summary && (
          <div className="lead-section">
            <div className="section-label">Summary:</div>
            <div className="summary-text">
              {lead.website_summary}
            </div>
          </div>
        )}
      </div>

      <div className="lead-card-footer">
        <div className="source-badge">
          Source: {lead.source || 'web'}
        </div>
      </div>
    </div>
  );
};

export default LeadCard;