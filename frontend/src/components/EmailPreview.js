import React, { useState } from 'react';
import './EmailPreview.css';

const EmailPreview = ({ email }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`email-preview ${email.sent ? 'sent' : 'drafted'}`}>
      <div className="email-preview-header" onClick={() => setExpanded(!expanded)}>
        <div className="email-info">
          <div className="email-recipient">
            <strong>To:</strong> {email.email}
          </div>
          <div className="email-company">
            <strong>Company:</strong> {email.company_name}
          </div>
        </div>
        
        <div className="email-status">
          {email.sent ? (
            <span className="status-badge sent-badge">
              ✓ Sent {email.sent_at ? new Date(email.sent_at).toLocaleDateString() : ''}
            </span>
          ) : (
            <span className="status-badge draft-badge">📝 Drafted</span>
          )}
          <button className="expand-btn">
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>

      <div className="email-subject">
        <strong>Subject:</strong> {email.email_subject}
      </div>

      {expanded && (
        <div className="email-body-preview">
          <div className="email-body-header">Email Body:</div>
          <div className="email-body-content">
            {email.email_body.split('\n').map((line, idx) => (
              <div key={idx} className="email-body-line">
                {line || <br />}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EmailPreview;