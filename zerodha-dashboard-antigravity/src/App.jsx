import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { FAMILY_MEMBERS } from './data/mockData';
import Dashboard from './pages/Dashboard';
import Zerodha from './pages/Zerodha';
import USStocks from './pages/USStocks';
import FixedDeposits from './pages/FixedDeposits';

function App() {
  const [currentMember, setCurrentMember] = useState(FAMILY_MEMBERS[0].id);

  return (
    <Layout currentMember={currentMember} setCurrentMember={setCurrentMember}>
      <Routes>
        <Route path="/" element={<Dashboard currentMember={currentMember} />} />
        <Route path="/zerodha" element={<Zerodha currentMember={currentMember} />} />
        <Route path="/us-stocks" element={<USStocks currentMember={currentMember} />} />
        <Route path="/fds" element={<FixedDeposits currentMember={currentMember} />} />
      </Routes>
    </Layout>
  );
}

export default App;
