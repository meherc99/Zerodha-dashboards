import React from 'react';
import { MOCK_DATA } from '../data/mockData';
import { Building2, AlertCircle } from 'lucide-react';

const TableHeader = ({ columns }) => (
    <thead>
        <tr style={{ background: 'var(--bg-tertiary)', textAlign: 'left' }}>
            {columns.map((col, index) => (
                <th key={index} style={{ padding: '1rem', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid var(--border-light)' }}>
                    {col}
                </th>
            ))}
        </tr>
    </thead>
);

const FixedDeposits = ({ currentMember }) => {
    const { fixedDeposits } = MOCK_DATA[currentMember];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div>
                <h1 className="flex-center" style={{ gap: '0.75rem', marginBottom: '0.5rem', fontSize: '2.5rem', justifyContent: 'flex-start' }}>
                    <Building2 size={36} style={{ color: '#f59e0b' }} /> Fixed Deposits
                </h1>
                <p style={{ color: 'var(--text-secondary)' }}>Track your guaranteed return investments across various banks.</p>
            </div>

            <div className="glass-panel" style={{ padding: '0', overflowX: 'auto' }}>
                <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse' }}>
                    <TableHeader columns={['Bank/Institution', 'Principal Amount', 'Interest Rate', 'Maturity Date', 'Current Value', 'Status']} />
                    <tbody>
                        {fixedDeposits.map((fd, i) => {
                            const maturityDate = new Date(fd.maturityDate);
                            const isMaturingSoon = maturityDate.getTime() - new Date().getTime() < 90 * 24 * 60 * 60 * 1000;

                            return (
                                <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                                    <td style={{ padding: '1.5rem 1rem', fontWeight: 500 }}>
                                        {fd.bank}
                                    </td>
                                    <td style={{ padding: '1.5rem 1rem' }}>₹{fd.principal.toLocaleString('en-IN')}</td>
                                    <td style={{ padding: '1.5rem 1rem', color: 'var(--accent-secondary)', fontWeight: 600 }}>{fd.interestRate}%</td>
                                    <td style={{ padding: '1.5rem 1rem' }}>
                                        {maturityDate.toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })}
                                    </td>
                                    <td style={{ padding: '1.5rem 1rem', fontWeight: 500 }}>₹{fd.currentVal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                    <td style={{ padding: '1.5rem 1rem' }}>
                                        {isMaturingSoon ? (
                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: 'var(--status-warning)', fontSize: '0.875rem', background: 'var(--status-warning-bg)', padding: '0.25rem 0.5rem', borderRadius: '4px', width: 'fit-content' }}>
                                                <AlertCircle size={14} /> Maturing Soon
                                            </span>
                                        ) : (
                                            <span style={{ color: 'var(--status-success)', fontSize: '0.875rem', background: 'var(--status-success-bg)', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>
                                                Active
                                            </span>
                                        )}
                                    </td>
                                </tr>
                            )
                        })}
                        {fixedDeposits.length === 0 && (
                            <tr>
                                <td colSpan="6" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                    No Fixed Deposits found for this portfolio.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default FixedDeposits;
