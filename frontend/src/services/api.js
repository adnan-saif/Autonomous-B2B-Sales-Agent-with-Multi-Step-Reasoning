import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Campaign API
export const campaignAPI = {
  // Start a new campaign
  startCampaign: async (data) => {
    const response = await api.post('/api/campaign/start', data);
    return response.data;
  },

  // Get campaign status
  getCampaignStatus: async (threadId) => {
    const response = await api.get(`/api/campaign/${threadId}/status`);
    return response.data;
  },

  // Continue campaign
  continueCampaign: async (threadId) => {
    const response = await api.post(`/api/campaign/${threadId}/continue`);
    return response.data;
  },

  // Approve emails
  approveEmails: async (threadId, decision) => {
    const response = await api.post(`/api/campaign/${threadId}/approve-emails`, {
      thread_id: threadId,
      decision: decision
    });
    return response.data;
  },

  // Schedule meeting
  scheduleMeeting: async (threadId, decision, meetingDatetime = null) => {
    const response = await api.post(`/api/campaign/${threadId}/schedule-meeting`, {
      thread_id: threadId,
      decision: decision,
      meeting_datetime: meetingDatetime
    });
    return response.data;
  },

  // Get leads
  getLeads: async (threadId) => {
    const response = await api.get(`/api/campaign/${threadId}/leads`);
    return response.data;
  },

  // Get emails
  getEmails: async (threadId) => {
    const response = await api.get(`/api/campaign/${threadId}/emails`);
    return response.data;
  },

  // Get monitoring data
  getMonitoring: async (threadId) => {
    const response = await api.get(`/api/campaign/${threadId}/monitoring`);
    return response.data;
  },

  // List all threads
  listThreads: async () => {
    const response = await api.get('/api/threads');
    return response.data;
  },
};

// WebSocket service
export class WebSocketService {
  constructor() {
    this.socket = null;
    this.listeners = new Map();
  }

  connect(threadId) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
    }

    this.socket = new WebSocket(`ws://localhost:8000/ws/${threadId}`);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.notifyListeners('connected', {});
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.notifyListeners('message', data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.notifyListeners('disconnected', {});
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.notifyListeners('error', error);
    };
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  addListener(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  removeListener(event, callback) {
    if (this.listeners.has(event)) {
      const callbacks = this.listeners.get(event);
      const index = callbacks.indexOf(callback);
      if (index > -1) {
        callbacks.splice(index, 1);
      }
    }
  }

  notifyListeners(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in WebSocket listener:', error);
        }
      });
    }
  }

  send(data) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }
}

export default api;