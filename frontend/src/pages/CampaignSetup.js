import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { campaignAPI } from '../services/api';
import './CampaignSetup.css';

const CampaignSetup = () => {
  const navigate = useNavigate();
  
  // Form state
  const [mode, setMode] = useState('test');
  const [query, setQuery] = useState('');
  const [threadId, setThreadId] = useState('');
  const [senderProfile, setSenderProfile] = useState({
    company_name: '',
    sender_name: '',
    sender_role: '',
    company_description: ''
  });

  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [useExistingThread, setUseExistingThread] = useState(false);

  const handleSenderProfileChange = (e) => {
    const { name, value } = e.target;
    setSenderProfile(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    if (!senderProfile.company_name.trim() || 
        !senderProfile.sender_name.trim() || 
        !senderProfile.sender_role.trim() || 
        !senderProfile.company_description.trim()) {
      setError('Please fill in all sender profile fields');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const requestData = {
        query: query.trim(),
        mode: mode,
        thread_id: useExistingThread ? threadId.trim() : null,
        sender_profile: senderProfile
      };

      const response = await campaignAPI.startCampaign(requestData);
      
      navigate(`/campaign/${response.thread_id}`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start campaign');
      console.error('Campaign start error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="campaign-setup">
      <h1>Start New Campaign</h1>
      
      <form onSubmit={handleSubmit} className="campaign-form">
        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        {/* Mode Selection */}
        <div className="form-section">
          <h3>Campaign Mode</h3>
          <div className="mode-selector">
            <label className="mode-option">
              <input
                type="radio"
                name="mode"
                value="test"
                checked={mode === 'test'}
                onChange={(e) => setMode(e.target.value)}
              />
              <div className="mode-content">
                <div className="mode-icon"></div>
                <div>
                  <div className="mode-title">Test Mode</div>
                  <div className="mode-description">
                    Use test data to preview the workflow. No real emails will be sent.
                  </div>
                </div>
              </div>
            </label>
            
            <label className="mode-option">
              <input
                type="radio"
                name="mode"
                value="live"
                checked={mode === 'live'}
                onChange={(e) => setMode(e.target.value)}
              />
              <div className="mode-content">
                <div className="mode-icon"></div>
                <div>
                  <div className="mode-title">Live Mode</div>
                  <div className="mode-description">
                    Real lead generation with actual email sending. Uses Apollo and web search.
                  </div>
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Search Query */}
        <div className="form-section">
          <h3>Search Query</h3>
          <div className="form-group">
            <label className="form-label">
              What companies are you looking for?
            </label>
            <input
              type="text"
              className="form-control"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., AI startups in India, SaaS companies in healthcare"
              required
            />
            <small className="form-hint">
              Be specific for better results. Example: "Fintech companies with 50-200 employees"
            </small>
          </div>
        </div>

        {/* Thread Management */}
        <div className="form-section">
          <h3>Thread Management</h3>
          <div className="form-group">
            <label className="form-check">
              <input
                type="checkbox"
                checked={useExistingThread}
                onChange={(e) => setUseExistingThread(e.target.checked)}
              />
              <span>Resume existing campaign thread</span>
            </label>
          </div>
          
          {useExistingThread && (
            <div className="form-group">
              <label className="form-label">Existing Thread ID</label>
              <input
                type="text"
                className="form-control"
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
                placeholder="Enter thread ID from previous campaign"
              />
            </div>
          )}
        </div>

        {/* Sender Profile */}
        <div className="form-section">
          <h3>Your Information</h3>
          <div className="row">
            <div className="col">
              <div className="form-group">
                <label className="form-label">Your Company Name</label>
                <input
                  type="text"
                  className="form-control"
                  name="company_name"
                  value={senderProfile.company_name}
                  onChange={handleSenderProfileChange}
                  placeholder="Your Company Inc."
                  required
                />
              </div>
            </div>
            
            <div className="col">
              <div className="form-group">
                <label className="form-label">Your Name</label>
                <input
                  type="text"
                  className="form-control"
                  name="sender_name"
                  value={senderProfile.sender_name}
                  onChange={handleSenderProfileChange}
                  placeholder="John Doe"
                  required
                />
              </div>
            </div>
          </div>

          <div className="row">
            <div className="col">
              <div className="form-group">
                <label className="form-label">Your Role</label>
                <input
                  type="text"
                  className="form-control"
                  name="sender_role"
                  value={senderProfile.sender_role}
                  onChange={handleSenderProfileChange}
                  placeholder="e.g., Founder, Growth Lead, Sales Director"
                  required
                />
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">What does your company do?</label>
            <textarea
              className="form-control"
              name="company_description"
              value={senderProfile.company_description}
              onChange={handleSenderProfileChange}
              placeholder="Briefly describe your company's products/services (1-2 sentences)"
              rows="3"
              required
            />
            <small className="form-hint">
              This will be used in email templates to personalize outreach.
            </small>
          </div>
        </div>

        {/* Submit */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={loading}
          >
            {loading ? (
              <>
                <div className="spinner spinner-sm"></div>
                Starting Campaign...
              </>
            ) : (
              'Start Campaign'
            )}
          </button>
          
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => navigate('/dashboard')}
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default CampaignSetup;