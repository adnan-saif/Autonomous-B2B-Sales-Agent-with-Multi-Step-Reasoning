import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { campaignAPI } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchThreads();
  }, []);

  const fetchThreads = async () => {
    try {
      setLoading(true);
      const data = await campaignAPI.listThreads();
      setThreads(data.threads || []);
    } catch (err) {
      setError('Failed to fetch campaigns');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="dashboard">
      {/* Hero Section */}
      <div className="hero-section">
        <h1 className="hero-title">B2B Lead Generator</h1>
        <p className="hero-tagline">AI-powered lead generation and outreach automation</p>
      </div>

      {/* Create Campaign Section */}
      <div className="section create-campaign-section">
        <div className="section-content">
          <h2 className="section-title">Start Your Campaign</h2>
          <p className="section-description">
            Begin your B2B outreach journey with our AI-powered platform. Generate qualified leads,
            craft personalized emails, and automate follow-ups.
          </p>
           <Link to="/campaign/new" className="btn btn-primary btn-large">
            Create New Campaign
          </Link>
        </div>
      </div>

      {/* How It Works Section - No Title, Single Row */}
      <div className="how-it-works-section">
        <div className="steps-container">
          <div className="step">
            <div className="step-number">1</div>
            <h3 className="step-title">Define Target</h3>
            <p className="step-description">
              Specify companies with a simple search query
            </p>
          </div>
          <div className="step">
            <div className="step-number">2</div>
            <h3 className="step-title">AI Research</h3>
            <p className="step-description">
              AI finds decision-makers & qualifies leads
            </p>
          </div>
          <div className="step">
            <div className="step-number">3</div>
            <h3 className="step-title">Personalized Outreach</h3>
            <p className="step-description">
              AI crafts & sends personalized emails
            </p>
          </div>
          <div className="step">
            <div className="step-number">4</div>
            <h3 className="step-title">Monitor & Engage</h3>
            <p className="step-description">
              Track replies & automate follow-ups
            </p>
          </div>
        </div>
      </div>

      {/* Our Aim Section */}
      <div className="section aim-section">
        <h2 className="section-title">Our Aim</h2>
        <p className="aim-description">
          We aim to democratize B2B lead generation by making it accessible, efficient, and 
          effective for businesses of all sizes. Our platform combines AI intelligence with 
          human oversight to create meaningful business connections.
        </p>
      </div>

      {/* Campaigns Dashboard */}
      <div className="section campaigns-section">
        <div className="section-header">
          <h2 className="section-title">Your Campaigns</h2>
          <button onClick={fetchThreads} className="btn btn-secondary">
            Refresh
          </button>
        </div>

        {error && (
          <div className="alert alert-error">
            {error}
          </div>
        )}

        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
            <p>Loading campaigns...</p>
          </div>
        ) : threads.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"></div>
            <h3>Campaigns</h3>
            <p>Start your first campaign to begin generating leads</p>
          </div>
        ) : (
          <div className="campaigns-grid">
            {threads.map((thread) => (
              <div key={thread.id} className="campaign-card">
                <div className="campaign-card-header">
                  <h3>{thread.name || 'Untitled Campaign'}</h3>
                  <span className={`status-badge status-${thread.status}`}>
                    {thread.status || 'unknown'}
                  </span>
                </div>
                
                <div className="campaign-card-body">
                  <div className="campaign-info">
                    <div className="info-item">
                      <span className="info-label">Query:</span>
                      <span className="info-value">{thread.query || 'N/A'}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Leads Found:</span>
                      <span className="info-value">{thread.leads_count || 0}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Emails Sent:</span>
                      <span className="info-value">{thread.emails_sent || 0}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Created:</span>
                      <span className="info-value">{formatDate(thread.created_at)}</span>
                    </div>
                  </div>
                  
                  <div className="campaign-actions">
                    <Link 
                      to={`/campaign/${thread.id}`} 
                      className="btn btn-secondary btn-sm"
                    >
                      View Details
                    </Link>
                    <Link 
                      to={`/monitoring/${thread.id}`} 
                      className="btn btn-primary btn-sm"
                    >
                      Monitor
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Contact Us Section */}
      <div className="section contact-section">
        <h2 className="contact-title">Contact Us</h2>
        <p className="contact-description">
          Have questions or need assistance? Reach out to our team.
        </p>
        <div className="contact-info">
          <p className="contact-email">Email: support@b2bleadgenerator.com</p>
          <p className="contact-hours">Support Hours: Mon-Fri, 9AM-6PM EST</p>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;