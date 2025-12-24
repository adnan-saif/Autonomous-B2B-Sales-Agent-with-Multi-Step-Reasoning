import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import CampaignSetup from './pages/CampaignSetup';
import CampaignView from './pages/CampaignView';
import Monitoring from './pages/Monitoring';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/campaign/new" element={<CampaignSetup />} />
            <Route path="/campaign/:threadId" element={<CampaignView />} />
            <Route path="/monitoring/:threadId" element={<Monitoring />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;