import React from 'react';
import { MdSearch } from 'react-icons/md';
import './Topbar.css';

const Topbar: React.FC<{ onSearch: (query: string) => void }> = ({ onSearch }) => {
  const [search, setSearch] = React.useState('');

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    onSearch(e.target.value);
  };

  return (
    <header className="topbar">
      <div className="topbar-title">Smart Email Classifier</div>
      <div className="topbar-search">
        <MdSearch className="search-icon" />
        <input
          type="text"
          placeholder="Search emails..."
          value={search}
          onChange={handleInput}
        />
      </div>
    </header>
  );
};

export default Topbar;
