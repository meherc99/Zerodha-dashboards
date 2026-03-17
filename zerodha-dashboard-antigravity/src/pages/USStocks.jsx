import React from 'react';
import { MOCK_DATA, USD_TO_INR } from '../data/mockData';
import { Globe, ArrowUpRight, ArrowDownRight } from 'lucide-react';

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

const USStocks = ({ currentMember }) => {
    const { usStocks } = MOCK_DATA[currentMember];

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div>
                <h1 className="flex-center" style={{ gap: '0.75rem', marginBottom: '0.5rem', fontSize: '2.5rem', justifyContent: 'flex-start' }}>
                    <Globe size={36} style={{ color: '#10b981' }} /> US Equity
                </h1>
                <p style={{ color: 'var(--text-secondary)' }}>International investments tracked in USD and INR. (1 USD = ₹{USD_TO_INR})</p>
            </div>

            <div className="glass-panel" style={{ padding: '1.5rem', overflowX: 'auto' }}>
                <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse' }}>
                    <TableHeader columns={['Symbol', 'Quantity', 'Avg. Price', 'Current Price', 'Invested (USD)', 'Invested (INR)', 'Current Value (INR)', 'P&L']} />
                    <tbody>
                        {usStocks.map((stock, i) => {
                            const currentValUsd = stock.qty * stock.ltp;
                            const currentValInr = currentValUsd * USD_TO_INR;
                            const investedInr = stock.invested * USD_TO_INR;
                            const plInr = currentValInr - investedInr;
                            const plPercent = (plInr / investedInr) * 100;
                            const isPositive = plInr >= 0;

                            return (
                                <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                                    <td style={{ padding: '1rem' }}>
                                        <div style={{ fontWeight: 500 }}>{stock.symbol}</div>
                                        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{stock.name}</div>
                                    </td>
                                    <td style={{ padding: '1rem' }}>{stock.qty}</td>
                                    <td style={{ padding: '1rem' }}>${stock.avgPrice.toFixed(2)}</td>
                                    <td style={{ padding: '1rem' }}>${stock.ltp.toFixed(2)}</td>
                                    <td style={{ padding: '1rem' }}>${stock.invested.toLocaleString()}</td>
                                    <td style={{ padding: '1rem' }}>₹{investedInr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                    <td style={{ padding: '1rem', fontWeight: 500 }}>₹{currentValInr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                    <td style={{ padding: '1rem' }}>
                                        <div className={isPositive ? 'positive' : 'negative'} style={{ fontWeight: 500 }}>
                                            {isPositive ? '+' : ''}₹{plInr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                        </div>
                                        <div className={isPositive ? 'positive' : 'negative'} style={{ fontSize: '0.875rem' }}>
                                            {isPositive ? '+' : ''}{plPercent.toFixed(2)}%
                                        </div>
                                    </td>
                                </tr>
                            )
                        })}
                        {usStocks.length === 0 && (
                            <tr>
                                <td colSpan="8" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                    No US Equity found for this portfolio.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default USStocks;
