import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { campaignAPI, WebSocketService } from '../services/api';
import './Monitoring.css';

const Monitoring = () => {
  const { threadId } = useParams();
  const navigate = useNavigate();
  
  const [monitoringData, setMonitoringData] = useState([]);
  const [activeMonitor, setActiveMonitor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showMeetingModal, setShowMeetingModal] = useState(false);
  const [meetingDate, setMeetingDate] = useState('');
  const [meetingTime, setMeetingTime] = useState('');
  const [wsService, setWsService] = useState(null);
  const [hasProcessedReply, setHasProcessedReply] = useState(false);

  useEffect(() => {
    setHasProcessedReply(false);
    fetchMonitoringData();
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
    
    service.addListener('message', (data) => {
      if (data.type === 'campaign_updated' || data.type === 'reply_received') {
        fetchMonitoringData();
      }
    });
    
    setWsService(service);
  };

  const fetchMonitoringData = async () => {
    try {
      setLoading(true);
      const data = await campaignAPI.getMonitoring(threadId);
      setMonitoringData(data.monitoring || []);
      setActiveMonitor(data.active_monitor || null);
      
      // Check if any reply needs meeting scheduling
      const replyNeedingMeeting = (data.monitoring || []).find(
        m => m.reply_received && !m.meet_link
      );
      
      // Only show modal if:
      // 1. There's a reply needing meeting
      // 2. Modal isn't already showing
      // 3. We haven't already processed a reply in this session
      // 4. WebSocket didn't just notify us (check wsService)
      if (replyNeedingMeeting && !showMeetingModal && !hasProcessedReply) {
        setActiveMonitor(replyNeedingMeeting);
        setShowMeetingModal(true);
        // Don't set hasProcessedReply here - wait until user actually makes a decision
      }
      
    } catch (err) {
      setError('Failed to fetch monitoring data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleScheduleMeeting = async (decision) => {
    try {
      if (decision === 'yes') {
        if (!meetingDate || !meetingTime) {
          alert('Please provide both date and time');
          return;
        }
        
        const meetingDatetime = `${meetingDate} ${meetingTime}`;
        await campaignAPI.scheduleMeeting(threadId, 'yes', meetingDatetime);
      } else {
        await campaignAPI.scheduleMeeting(threadId, 'no');
      }
      
      // Mark this reply as processed
      setHasProcessedReply(true);
      setShowMeetingModal(false);
      setMeetingDate('');
      setMeetingTime('');
      
      // Refresh data to show updated status
      fetchMonitoringData();
      
    } catch (err) {
      setError('Failed to schedule meeting');
      console.error(err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#3498db';
      case 'replied': return '#2ecc71';
      case 'meeting_created': return '#9b59b6';
      case 'expired': return '#95a5a6';
      default: return '#7f8c8d';
    }
  };

  const getStatusLabel = (status) => {
    const labels = {
      'active': '⏳ Monitoring',
      'replied': '✅ Reply Received',
      'meeting_created': '📅 Meeting Scheduled',
      'expired': '⌛️ Expired'
    };
    return labels[status] || status;
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>Loading monitoring data...</p>
      </div>
    );
  }

  return (
    <div className="monitoring">
      <div className="monitoring-header">
        <h1>
          Monitoring Campaign:
          <button 
            onClick={fetchMonitoringData}
            className="btn btn-secondary ml-3"
          >
            Refresh
          </button>
        </h1>
        
        <div className="monitoring-stats">
          <div className="stat">
            <div className="stat-value">{monitoringData.length}</div>
            <div className="stat-label">Total</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {monitoringData.filter(m => m.monitor_status === 'active').length}
            </div>
            <div className="stat-label">Active</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {monitoringData.filter(m => m.reply_received).length}
            </div>
            <div className="stat-label">Replies</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {monitoringData.filter(m => m.followup_1_sent).length}
            </div>
            <div className="stat-label">Follow-up 1</div>
          </div>
          <div className="stat">
            <div className="stat-value">
              {monitoringData.filter(m => m.followup_2_sent).length}
            </div>
            <div className="stat-label">Follow-up 2</div>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {/* Meeting Scheduling Modal */}
      {showMeetingModal && activeMonitor && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>📧 Reply Received!</h3>
            </div>
            <div className="modal-body">
              <div className="reply-alert">
                <div className="alert-icon">🎉</div>
                <div>
                  <p>
                    <strong>{activeMonitor.company_name}</strong> has replied to your email!
                  </p>
                  <p className="reply-email">
                    From: {activeMonitor.email}
                  </p>
                </div>
              </div>
              
              <div className="meeting-form">
                <h4>Schedule a Meeting?</h4>
                <p>Would you like to schedule a Google Meet call with them?</p>
                
                <div className="form-group">
                  <label className="form-label">Meeting Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={meetingDate}
                    onChange={(e) => setMeetingDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
                
                <div className="form-group">
                  <label className="form-label">Meeting Time (24-hour)</label>
                  <input
                    type="time"
                    className="form-control"
                    value={meetingTime}
                    onChange={(e) => setMeetingTime(e.target.value)}
                  />
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button
                onClick={() => handleScheduleMeeting('yes')}
                className="btn btn-success"
              >
                ✅ Schedule Meeting
              </button>
              <button
                onClick={() => handleScheduleMeeting('no')}
                className="btn btn-secondary"
              >
                Skip for Now
              </button>
            </div>
          </div>
        </div>
      )}

      {monitoringData.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"></div>
          <h3>No Monitoring Data Yet</h3>
          <p>Start a campaign and send emails to begin monitoring</p>
          <button 
            onClick={() => navigate(`/campaign/${threadId}`)}
            className="btn btn-primary mt-3"
          >
            Go to Campaign
          </button>
        </div>
      ) : (
        <div className="monitoring-grid">
          {monitoringData.map((item, index) => (
            <div key={index} className="monitor-card">
              <div className="monitor-card-header">
                <div className="monitor-company">
                  <h3>{item.company_name}</h3>
                  <span className="monitor-email">{item.email}</span>
                </div>
                
                <div 
                  className="monitor-status"
                  style={{ color: getStatusColor(item.monitor_status) }}
                >
                  {getStatusLabel(item.monitor_status)}
                </div>
              </div>

              <div className="monitor-card-body">
                <div className="monitor-info">
                  <div className="info-row">
                    <span className="info-label">Started:</span>
                    <span className="info-value">
                      {new Date(item.monitor_started_at).toLocaleString()}
                    </span>
                  </div>
                  
                  {item.last_checked_at && (
                    <div className="info-row">
                      <span className="info-label">Last Checked:</span>
                      <span className="info-value">
                        {new Date(item.last_checked_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  
                  <div className="info-row">
                    <span className="info-label">Message ID:</span>
                    <span className="info-value message-id">
                      {item.message_id?.substring(0, 20)}...
                    </span>
                  </div>
                </div>

                {/* Progress Indicators */}
                <div className="monitor-progress">
                  <div className="progress-item">
                    <div className={`progress-icon ${item.reply_received ? 'active' : ''}`}>
                      {item.reply_received ? '✅' : '📧'}
                    </div>
                    <div className="progress-label">Reply</div>
                  </div>
                  
                  <div className="progress-arrow">→</div>
                  
                  <div className="progress-item">
                    <div className={`progress-icon ${item.followup_1_sent ? 'active' : ''}`}>
                      {item.followup_1_sent ? '✅' : '1️⃣'}
                    </div>
                    <div className="progress-label">Follow-up 1</div>
                  </div>
                  
                  <div className="progress-arrow">→</div>
                  
                  <div className="progress-item">
                    <div className={`progress-icon ${item.followup_2_sent ? 'active' : ''}`}>
                      {item.followup_2_sent ? '✅' : '2️⃣'}
                    </div>
                    <div className="progress-label">Follow-up 2</div>
                  </div>
                </div>

                {/* Meeting Info */}
                {item.meet_link && (
                  <div className="meeting-info">
                    <div className="meeting-header">
                      <strong>Meeting Scheduled</strong>
                    </div>
                    <a 
                      href={item.meet_link} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="meet-link"
                    >
                      🔗 Join Google Meet
                    </a>
                    <div className="calendar-id">
                      Calendar Event: {item.calendar_event_id?.substring(0, 15)}...
                    </div>
                  </div>
                )}
              </div>

              <div className="monitor-card-footer">
                <div className="monitor-actions">
                  {item.reply_received && !item.meet_link && (
                    <button 
                      onClick={() => {
                        setActiveMonitor(item);
                        setShowMeetingModal(true);
                      }}
                      className="btn btn-success btn-sm"
                    >
                      Schedule Meeting
                    </button>
                  )}
                  
                  {item.meet_link && (
                    <button 
                      onClick={() => window.open(item.meet_link, '_blank')}
                      className="btn btn-primary btn-sm"
                    >
                      Join Meeting
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="monitoring-actions">
        <button
          onClick={() => navigate(`/campaign/${threadId}`)}
          className="btn btn-secondary"
        >
          Back to Campaign
        </button>
        
        <button
          onClick={fetchMonitoringData}
          className="btn btn-primary"
        >
          Refresh Data
        </button>
      </div>
    </div>
  );
};

export default Monitoring;