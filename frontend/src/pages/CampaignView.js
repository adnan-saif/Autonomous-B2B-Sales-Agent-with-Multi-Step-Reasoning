import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { campaignAPI, WebSocketService } from '../services/api';
import LeadCard from '../components/LeadCard';
import EmailPreview from '../components/EmailPreview';
import './CampaignView.css';

const CampaignView = () => {
  const { threadId } = useParams();
  const navigate = useNavigate();
  
  // State
  const [campaign, setCampaign] = useState(null);
  const [leads, setLeads] = useState([]);
  const [emails, setEmails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [phase, setPhase] = useState('');
  const [showEmailApproval, setShowEmailApproval] = useState(false);
  const [wsService, setWsService] = useState(null);

  useEffect(() => {
    fetchCampaignData();
    setupWebSocket();
    
    return () => {
      if (wsService) {
        wsService.disconnect();
      }
    };
  }, [threadId]);

  const setupWebSocket = () => {
    const service = new WebSocketService();
    service.connect(threadId);
    
    service.addListener('message', handleWebSocketMessage);
    service.addListener('connected', () => {
      console.log('Connected to campaign updates');
    });
    
    setWsService(service);
  };

  const handleWebSocketMessage = (data) => {
    console.log('WebSocket update:', data);
    
    if (data.type === 'campaign_updated' || 
        data.type === 'campaign_started' ||
        data.type === 'emails_approved' ||
        data.type === 'meeting_scheduled') {
      fetchCampaignData();
    }
  };

  const fetchCampaignData = async () => {
    try {
      setLoading(true);
      
      // Get campaign status
      const status = await campaignAPI.getCampaignStatus(threadId);
      setCampaign(status);
      setPhase(status.phase || '');
      
      // Get leads
      const leadsData = await campaignAPI.getLeads(threadId);
      setLeads(leadsData.leads || []);
      
      // Get emails
      const emailsData = await campaignAPI.getEmails(threadId);
      setEmails(emailsData.emails || []);
      
      // Check if we need to show email approval
      if (status.current_state?.human_decision?.send_first_email === undefined &&
          emailsData.emails?.length > 0) {
        setShowEmailApproval(true);
      }
      
    } catch (err) {
      setError('Failed to fetch campaign data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveEmails = async (decision) => {
    try {
      await campaignAPI.approveEmails(threadId, decision);
      setShowEmailApproval(false);
      if (decision === 'yes') {
        setPhase('sending');
      }
    } catch (err) {
      setError('Failed to process email approval');
      console.error(err);
    }
  };

  const handleContinue = async () => {
    try {
      await campaignAPI.continueCampaign(threadId);
      fetchCampaignData();
    } catch (err) {
      console.error('Failed to continue campaign:', err);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading campaign data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert alert-error">
        {error}
        <button onClick={() => navigate('/dashboard')} className="btn btn-secondary ml-2">
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="campaign-view">
      <div className="campaign-header">
        <h1>
          Campaign:
          <span className="campaign-phase">({phase})</span>
        </h1>
        
        <div className="campaign-stats">
          <div className="stat">
            <div className="stat-value">{leads.length}</div>
            <div className="stat-label">Leads Found</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {leads.filter(l => l.qualified).length}
            </div>
            <div className="stat-label">Qualified</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {emails.filter(e => e.sent).length}
            </div>
            <div className="stat-label">Emails Sent</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {campaign?.replies_received || 0}
            </div>
            <div className="stat-label">Replies</div>
          </div>
        </div>
      </div>

      {/* Email Approval Modal */}
      {showEmailApproval && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Approve Email Sending</h3>
            </div>
            <div className="modal-body">
              <p>
                {emails.length} emails have been drafted and are ready to send.
                Review the emails below and approve or reject sending.
              </p>
              
              <div className="email-preview-list">
                {emails.slice(0, 2).map((email, index) => (
                  <EmailPreview key={index} email={email} />
                ))}
              </div>
              
              {emails.length > 2 && (
                <p className="text-center mt-2">
                  ... and {emails.length - 2} more emails
                </p>
              )}
            </div>
            <div className="modal-footer">
              <button
                onClick={() => handleApproveEmails('yes')}
                className="btn btn-success"
              >
                ✅ Approve & Send All
              </button>
              <button
                onClick={() => handleApproveEmails('no')}
                className="btn btn-danger"
              >
                ❌ Reject & Stop
              </button>
              <button
                onClick={() => navigate(`/monitoring/${threadId}`)}
                className="btn btn-secondary"
              >
                View All Emails
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Leads Section */}
      <section className="campaign-section">
        <div className="section-header">
          <h2>Discovered Leads</h2>
          <span className="badge">{leads.length} companies</span>
        </div>
        
        {leads.length === 0 ? (
          <div className="empty-state">
            <p>No leads found yet. The system is searching...</p>
            <button onClick={fetchCampaignData} className="btn btn-secondary">
              Refresh
            </button>
          </div>
        ) : (
          <div className="leads-grid">
            {leads.map((lead, index) => (
              <LeadCard key={index} lead={lead} />
            ))}
          </div>
        )}
      </section>

      {/* Emails Section */}
      {emails.length > 0 && (
        <section className="campaign-section">
          <div className="section-header">
            <h2>Drafted Emails</h2>
            <span className="badge">{emails.length} emails ready</span>
          </div>
          
          <div className="emails-list">
            {emails.map((email, index) => (
              <div key={index} className="email-item">
                <div className="email-header">
                  <strong>{email.company_name}</strong>
                  <span className="email-recipient">{email.email}</span>
                  {email.sent ? (
                    <span className="badge badge-success">Sent</span>
                  ) : (
                    <span className="badge badge-warning">Drafted</span>
                  )}
                </div>
                <div className="email-subject">
                  <strong>Subject:</strong> {email.email_subject}
                </div>
                <div className="email-preview">
                  {email.email_body.substring(0, 200)}...
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Actions */}
      <div className="campaign-actions">
        <button
          onClick={handleContinue}
          className="btn btn-primary"
          disabled={phase === 'monitor'}
        >
          Continue Execution
        </button>
        
        <button
          onClick={() => navigate(`/monitoring/${threadId}`)}
          className="btn btn-secondary"
        >
          Go to Monitoring
        </button>
        
        <button
          onClick={() => navigate('/dashboard')}
          className="btn"
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  );
};

export default CampaignView;