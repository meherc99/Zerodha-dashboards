import React, { useState, useEffect, useRef } from 'react';
import { MOCK_DATA } from '../data/mockData';
import { TrendingUp, ArrowUpRight, ArrowDownRight, Layers, Link as LinkIcon, RefreshCw, AlertCircle, Upload, FileSpreadsheet } from 'lucide-react';

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

const NetworthSummary = ({ title, invested, currentValue, dayChange }) => {
    const isPositive = currentValue >= invested;
    const overallReturn = invested > 0 ? ((currentValue - invested) / invested) * 100 : 0;

    return (
        <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h3 style={{ color: 'var(--text-secondary)', fontSize: '1rem', fontWeight: 500 }}>{title}</h3>
            <div className="flex-between">
                <h2 style={{ fontSize: '1.75rem' }}>₹{currentValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</h2>
                <div style={{ textAlign: 'right' }}>
                    <div className={isPositive ? 'positive' : 'negative'} style={{ display: 'flex', alignItems: 'center', fontWeight: 600 }}>
                        {isPositive ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                        {Math.abs(overallReturn).toFixed(2)}%
                    </div>
                    <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Overall</span>
                </div>
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.875rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Invested: <span style={{ color: 'var(--text-primary)' }}>₹{invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span></span>
                <span style={{ color: 'var(--text-secondary)' }}>Day Chg: <span className={dayChange >= 0 ? 'positive' : 'negative'}>{dayChange >= 0 ? '+' : ''}{dayChange}%</span></span>
            </div>
        </div>
    );
};

const Zerodha = ({ currentMember }) => {
    const [activeTab, setActiveTab] = useState('stocks');
    const [isLive, setIsLive] = useState(false);
    const [isImported, setIsImported] = useState(false);
    const [hasLivePrices, setHasLivePrices] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [importInfo, setImportInfo] = useState(null); // { originalFile, uploadedAt }
    const fileInputRef = useRef(null);

    // State to hold active portfolio data
    const [portfolioData, setPortfolioData] = useState({
        zerodhaStocks: MOCK_DATA[currentMember].zerodhaStocks,
        zerodhaMFs: MOCK_DATA[currentMember].zerodhaMFs
    });

    // When family member changes, reset and load appropriate data
    useEffect(() => {
        setError(null);
        setImportInfo(null);

        if (currentMember === 'meher') {
            setIsImported(false);
            checkAuthStatus();
        } else {
            setIsLive(false);
            // Check if this member has imported data
            checkImportedData();
        }
    }, [currentMember]);

    const checkAuthStatus = async () => {
        try {
            const res = await fetch('/api/auth/status', { credentials: 'include' });
            const data = await res.json();
            if (data.authenticated && currentMember === 'meher') {
                setIsLive(true);
                fetchLiveHoldings();
            } else {
                setIsLive(false);
                setPortfolioData({
                    zerodhaStocks: MOCK_DATA[currentMember].zerodhaStocks,
                    zerodhaMFs: MOCK_DATA[currentMember].zerodhaMFs
                });
            }
        } catch (err) {
            console.error("Could not check auth status", err);
            setPortfolioData({
                zerodhaStocks: MOCK_DATA[currentMember].zerodhaStocks,
                zerodhaMFs: MOCK_DATA[currentMember].zerodhaMFs
            });
        }
    };

    const checkImportedData = async () => {
        try {
            const res = await fetch(`/api/portfolio/imported/${currentMember}`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                setPortfolioData({
                    zerodhaStocks: data.zerodhaStocks,
                    zerodhaMFs: data.zerodhaMFs
                });
                setIsImported(true);
                setHasLivePrices(data.livePrices);
                setImportInfo({ originalFile: data.originalFile, uploadedAt: data.uploadedAt });
            } else {
                // No imported data — show mock
                setIsImported(false);
                setPortfolioData({
                    zerodhaStocks: MOCK_DATA[currentMember].zerodhaStocks,
                    zerodhaMFs: MOCK_DATA[currentMember].zerodhaMFs
                });
            }
        } catch (err) {
            setIsImported(false);
            setPortfolioData({
                zerodhaStocks: MOCK_DATA[currentMember].zerodhaStocks,
                zerodhaMFs: MOCK_DATA[currentMember].zerodhaMFs
            });
        }
    };

    const handleConnect = () => {
        window.location.href = '/api/auth/login';
    };

    const fetchLiveHoldings = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch('/api/portfolio/holdings', { credentials: 'include' });

            if (res.status === 401) {
                setIsLive(false);
                throw new Error("Session expired. Please reconnect.");
            }

            if (!res.ok) throw new Error("Failed to fetch live data");

            const data = await res.json();
            setPortfolioData({
                zerodhaStocks: data.zerodhaStocks,
                zerodhaMFs: data.zerodhaMFs.length > 0 ? data.zerodhaMFs : MOCK_DATA[currentMember].zerodhaMFs
            });
            setIsLive(true);
        } catch (err) {
            setError(err.message);
            setIsLive(false);
        } finally {
            setLoading(false);
        }
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setLoading(true);
        setError(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('member', currentMember);

        try {
            const res = await fetch('/api/portfolio/import', {
                method: 'POST',
                credentials: 'include',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.error || 'Failed to import file');
            }

            const data = await res.json();
            setPortfolioData({
                zerodhaStocks: data.zerodhaStocks,
                zerodhaMFs: data.zerodhaMFs
            });
            setIsImported(true);
            setHasLivePrices(data.livePrices);
            setImportInfo({ originalFile: file.name, uploadedAt: new Date().toISOString() });
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
            // Reset file input so the same file can be re-uploaded
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const refreshImportedPrices = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`/api/portfolio/imported/${currentMember}`, { credentials: 'include' });
            if (!res.ok) throw new Error("Failed to refresh prices");

            const data = await res.json();
            setPortfolioData({
                zerodhaStocks: data.zerodhaStocks,
                zerodhaMFs: data.zerodhaMFs
            });
            setHasLivePrices(data.livePrices);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const calcTotal = (arr, key1, key2) => arr.reduce((acc, curr) => acc + (curr[key1] * curr[key2]), 0);
    const calcInvested = (arr) => arr.reduce((acc, curr) => acc + curr.invested, 0);

    const { zerodhaStocks, zerodhaMFs } = portfolioData;

    const stocksCurrent = calcTotal(zerodhaStocks, 'qty', 'ltp');
    const stocksInvested = calcInvested(zerodhaStocks);
    const mfCurrent = calcTotal(zerodhaMFs, 'units', 'ltp');
    const mfInvested = calcInvested(zerodhaMFs);

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="flex-between" style={{ alignItems: 'flex-start' }}>
                <div>
                    <h1 className="flex-center" style={{ gap: '0.75rem', marginBottom: '0.5rem', fontSize: '2.5rem', justifyContent: 'flex-start' }}>
                        <TrendingUp size={36} style={{ color: 'var(--accent-primary)' }} /> Zerodha Portfolio
                    </h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Indian Equities and Mutual Fund holdings.</p>
                </div>

                {/* Integration Controls — Meher: API connect | Others: Excel import */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
                    {currentMember === 'meher' ? (
                        // Meher: Kite Connect API flow
                        <>
                            {!isLive ? (
                                <button onClick={handleConnect} className="glass-panel" style={{ padding: '0.75rem 1.5rem', background: 'var(--accent-glow)', color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem', borderRadius: '12px', fontWeight: 600 }}>
                                    <LinkIcon size={18} /> Connect Zerodha API
                                </button>
                            ) : (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{ fontSize: '0.875rem', color: 'var(--status-success)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-success)' }}></span> Live Data Active
                                    </span>
                                    <button onClick={fetchLiveHoldings} disabled={loading} className="glass-panel" style={{ padding: '0.5rem', borderRadius: '8px' }}>
                                        <RefreshCw size={18} style={{ color: 'var(--text-secondary)' }} className={loading ? 'spinning' : ''} />
                                    </button>
                                </div>
                            )}
                        </>
                    ) : (
                        // Family members: Excel import flow
                        <>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".xlsx,.xls,.csv"
                                onChange={handleFileUpload}
                                style={{ display: 'none' }}
                                id="excel-upload"
                            />
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={loading}
                                    className="glass-panel"
                                    style={{ padding: '0.75rem 1.5rem', background: 'var(--accent-glow)', color: 'var(--accent-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem', borderRadius: '12px', fontWeight: 600 }}
                                >
                                    <Upload size={18} /> Import Holdings (Excel)
                                </button>
                                {isImported && (
                                    <button onClick={refreshImportedPrices} disabled={loading} className="glass-panel" style={{ padding: '0.5rem', borderRadius: '8px' }} title="Refresh live prices">
                                        <RefreshCw size={18} style={{ color: 'var(--text-secondary)' }} className={loading ? 'spinning' : ''} />
                                    </button>
                                )}
                            </div>
                            {isImported && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }}>
                                    <FileSpreadsheet size={14} style={{ color: 'var(--accent-primary)' }} />
                                    <span style={{ color: 'var(--text-muted)' }}>
                                        Imported: {importInfo?.originalFile}
                                    </span>
                                    <span style={{
                                        fontSize: '0.75rem',
                                        padding: '0.15rem 0.5rem',
                                        borderRadius: '6px',
                                        background: hasLivePrices ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                                        color: hasLivePrices ? 'var(--status-success)' : '#f59e0b'
                                    }}>
                                        {hasLivePrices ? '● Live Prices' : '● Excel Prices'}
                                    </span>
                                </div>
                            )}
                        </>
                    )}
                    {error && <span style={{ color: 'var(--status-danger)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}><AlertCircle size={14} /> {error}</span>}
                </div>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                <NetworthSummary
                    title="Stocks Total"
                    invested={stocksInvested}
                    currentValue={stocksCurrent}
                    dayChange={isLive && zerodhaStocks.length > 0 ? (zerodhaStocks.reduce((sum, stock) => sum + (stock.dayChange || 0), 0) / zerodhaStocks.length).toFixed(2) : 0.8}
                />
                <NetworthSummary
                    title="Mutual Funds Total"
                    invested={mfInvested}
                    currentValue={mfCurrent}
                    dayChange={0.4}
                />
            </div>

            <div className="glass-panel" style={{ padding: '0' }}>
                <div style={{ display: 'flex', borderBottom: '1px solid var(--border-light)' }}>
                    <button
                        onClick={() => setActiveTab('stocks')}
                        style={{
                            padding: '1.25rem 2rem',
                            color: activeTab === 'stocks' ? 'var(--text-primary)' : 'var(--text-secondary)',
                            borderBottom: activeTab === 'stocks' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                            fontWeight: activeTab === 'stocks' ? 600 : 400,
                            fontSize: '1rem'
                        }}
                    >
                        Indian Equity
                    </button>
                    <button
                        onClick={() => setActiveTab('mf')}
                        style={{
                            padding: '1.25rem 2rem',
                            color: activeTab === 'mf' ? 'var(--text-primary)' : 'var(--text-secondary)',
                            borderBottom: activeTab === 'mf' ? '2px solid var(--accent-primary)' : '2px solid transparent',
                            fontWeight: activeTab === 'mf' ? 600 : 400,
                            fontSize: '1rem'
                        }}
                    >
                        Mutual Funds
                    </button>
                </div>

                <div style={{ overflowX: 'auto', padding: '1.5rem', position: 'relative' }}>
                    {loading && (
                        <div style={{ position: 'absolute', inset: 0, background: 'rgba(10, 10, 15, 0.7)', backdropFilter: 'blur(2px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10 }}>
                            <RefreshCw size={32} style={{ color: 'var(--accent-primary)' }} className="spinning" />
                        </div>
                    )}
                    {activeTab === 'stocks' ? (
                        <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse' }}>
                            <TableHeader columns={['Symbol', 'Quantity', 'Avg. Price', 'LTP', 'Invested', 'Current Value', 'P&L']} />
                            <tbody>
                                {zerodhaStocks.map((stock, i) => {
                                    const currentValue = stock.qty * stock.ltp;
                                    const pl = currentValue - stock.invested;
                                    // Handle edge case where invested is 0 (like free shares)
                                    const plPercent = stock.invested > 0 ? (pl / stock.invested) * 100 : 0;
                                    const isPositive = pl >= 0;

                                    return (
                                        <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                                            <td style={{ padding: '1rem' }}>
                                                <div style={{ fontWeight: 500 }}>{stock.symbol}</div>
                                                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{stock.name}</div>
                                            </td>
                                            <td style={{ padding: '1rem' }}>{stock.qty}</td>
                                            <td style={{ padding: '1rem' }}>₹{stock.avgPrice.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                            <td style={{ padding: '1rem' }}>₹{stock.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                            <td style={{ padding: '1rem' }}>₹{stock.invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                            <td style={{ padding: '1rem', fontWeight: 500 }}>₹{currentValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                            <td style={{ padding: '1rem' }}>
                                                <div className={isPositive ? 'positive' : 'negative'} style={{ fontWeight: 500 }}>
                                                    {isPositive ? '+' : ''}₹{pl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                                </div>
                                                <div className={isPositive ? 'positive' : 'negative'} style={{ fontSize: '0.875rem' }}>
                                                    {isPositive ? '+' : ''}{plPercent.toFixed(2)}%
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                                {zerodhaStocks.length === 0 && (
                                    <tr>
                                        <td colSpan="7" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                            {isLive ? 'No stock holdings currently found in Zerodha Api.' : 'No stocks found for this portfolio.'}
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    ) : (
                        <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse' }}>
                            <TableHeader columns={['Fund Name', 'Type', 'Units', 'Avg. NAV', 'Current NAV', 'Invested', 'Current Value', 'P&L']} />
                            <tbody>
                                {zerodhaMFs.map((mf, i) => {
                                    const currentValue = mf.units * mf.ltp;
                                    const pl = currentValue - mf.invested;
                                    const plPercent = mf.invested > 0 ? (pl / mf.invested) * 100 : 0;
                                    const isPositive = pl >= 0;

                                    return (
                                        <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                                            <td style={{ padding: '1rem' }}>
                                                <div style={{ fontWeight: 500 }}>{mf.name}</div>
                                            </td>
                                            <td style={{ padding: '1rem' }}>
                                                <span style={{ padding: '0.25rem 0.5rem', background: 'var(--bg-tertiary)', borderRadius: '4px', fontSize: '0.875rem' }}>
                                                    {mf.type}
                                                </span>
                                            </td>
                                            <td style={{ padding: '1rem' }}>{mf.units.toLocaleString('en-IN')}</td>
                                            <td style={{ padding: '1rem' }}>₹{mf.navAvg.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                            <td style={{ padding: '1rem' }}>₹{mf.ltp.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                                            <td style={{ padding: '1rem' }}>₹{mf.invested.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                            <td style={{ padding: '1rem', fontWeight: 500 }}>₹{currentValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>
                                            <td style={{ padding: '1rem' }}>
                                                <div className={isPositive ? 'positive' : 'negative'} style={{ fontWeight: 500 }}>
                                                    {isPositive ? '+' : ''}₹{pl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                                                </div>
                                                <div className={isPositive ? 'positive' : 'negative'} style={{ fontSize: '0.875rem' }}>
                                                    {isPositive ? '+' : ''}{plPercent.toFixed(2)}%
                                                </div>
                                            </td>
                                        </tr>
                                    )
                                })}
                                {zerodhaMFs.length === 0 && (
                                    <tr>
                                        <td colSpan="8" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                                            No mutual funds found for this portfolio.
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
            <style>{`
         @keyframes spin { 100% { transform: rotate(360deg); } }
         .spinning { animation: spin 1s linear infinite; }
      `}</style>
        </div >
    );
};

export default Zerodha;
