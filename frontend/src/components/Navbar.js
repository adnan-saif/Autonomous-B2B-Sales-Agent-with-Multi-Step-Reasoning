import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/dashboard" className="navbar-brand">
          B2B Lead Generator
        </Link>
        
        <div className="navbar-menu">
          <Link 
            to="/dashboard" 
            className={`nav-link ${location.pathname === '/dashboard' ? 'active' : ''}`}
          >
            Dashboard
          </Link>
          <Link 
            to="/campaign/new" 
            className={`nav-link ${location.pathname === '/campaign/new' ? 'active' : ''}`}
          >
            New Campaign
          </Link>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;