import React, { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { ArrowUpRight, ArrowDownRight, Wallet, Activity, TrendingUp, BadgePercent, RefreshCw } from 'lucide-react';
import { MOCK_DATA, USD_TO_INR } from '../data/mockData';

const StatCard = ({ title, value, change, isPercent, icon: Icon }) => {
    const isPositive = change >= 0;

    return (
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="flex-between">
                <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{title}</span>
                <div style={{ padding: '0.5rem', background: 'var(--bg-tertiary)', borderRadius: '12px' }}>
                    <Icon size={20} style={{ color: 'var(--accent-primary)' }} />
                </div>
            </div>
            <div>
                <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
                    {typeof value === 'number' && !isPercent ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : value}
                </h2>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.875rem' }}>
                    {isPositive ? (
                        <span className="positive" style={{ display: 'flex', alignItems: 'center', background: 'var(--status-success-bg)', padding: '0.125rem 0.375rem', borderRadius: '4px' }}>
                            <ArrowUpRight size={16} /> {Math.abs(change).toFixed(2)}{isPercent ? '%' : ''}
                        </span>
                    ) : (
                        <span className="negative" style={{ display: 'flex', alignItems: 'center', background: 'var(--status-danger-bg)', padding: '0.125rem 0.375rem', borderRadius: '4px' }}>
                            <ArrowDownRight size={16} /> {Math.abs(change).toFixed(2)}{isPercent ? '%' : ''}
                        </span>
                    )}
                    <span style={{ color: 'var(--text-muted)' }}>vs yesterday</span>
                </div>
            </div>
        </div>
    );
};

const Dashboard = ({ currentMember }) => {
    const [loading, setLoading] = useState(true);
    const [portfolioData, setPortfolioData] = useState({
        zerodhaStocks: MOCK_DATA[currentMember].zerodhaStocks,
        zerodhaMFs: MOCK_DATA[currentMember].zerodhaMFs,
        usStocks: MOCK_DATA[currentMember].usStocks,
        fixedDeposits: MOCK_DATA[currentMember].fixedDeposits
    });

    // Fetch dynamic data based on member
    useEffect(() => {
        let isMounted = true;

        const fetchDynamicData = async () => {
            setLoading(true);
            try {
                let fetchedStocks = MOCK_DATA[currentMember].zerodhaStocks;
                let fetchedMFs = MOCK_DATA[currentMember].zerodhaMFs;

                if (currentMember === 'meher') {
                    // Try to fetch live Kite data
                    const res = await fetch('/api/portfolio/holdings', { credentials: 'include' });
                    if (res.ok) {
                        const data = await res.json();
                        fetchedStocks = data.zerodhaStocks;
                        fetchedMFs = data.zerodhaMFs.length > 0 ? data.zerodhaMFs : fetchedMFs;
                    }
                } else {
                    // Try to fetch imported Excel data
                    const res = await fetch(`/api/portfolio/imported/${currentMember}`, { credentials: 'include' });
                    if (res.ok) {
                        const data = await res.json();
                        fetchedStocks = data.zerodhaStocks;
                        fetchedMFs = data.zerodhaMFs;
                    }
                }

                if (isMounted) {
                    setPortfolioData({
                        zerodhaStocks: fetchedStocks,
                        zerodhaMFs: fetchedMFs,
                        usStocks: MOCK_DATA[currentMember].usStocks,
                        fixedDeposits: MOCK_DATA[currentMember].fixedDeposits
                    });
                }
            } catch (err) {
                console.error("Error fetching dynamic data for dashboard:", err);
            } finally {
                if (isMounted) setLoading(false);
            }
        };

        fetchDynamicData();

        return () => { isMounted = false; };
    }, [currentMember]);

    // Calculate dynamic totals
    const calcTotal = (arr, qtyKey, priceKey) => arr.reduce((acc, curr) => acc + (curr[qtyKey] * curr[priceKey]), 0);

    const stocksCurrent = calcTotal(portfolioData.zerodhaStocks, 'qty', 'ltp');
    const mfCurrent = calcTotal(portfolioData.zerodhaMFs, 'units', 'ltp');
    const usCurrent = portfolioData.usStocks.reduce((acc, curr) => acc + (curr.qty * curr.ltp * USD_TO_INR), 0);
    const fdCurrent = portfolioData.fixedDeposits.reduce((acc, curr) => acc + curr.currentVal, 0);

    // Calculate dynamic day changes
    const stocksDayChange = portfolioData.zerodhaStocks.reduce((acc, curr) => {
        const invested = curr.qty * curr.avgPrice;
        // Approximation: assume dayChange is percentage of current invested
        return acc + (invested * (curr.dayChange / 100));
    }, 0) || MOCK_DATA[currentMember].overview.dailyChange * 0.5;

    const totalNetworth = stocksCurrent + mfCurrent + usCurrent + fdCurrent;
    const dailyChange = stocksDayChange + (MOCK_DATA[currentMember].overview.dailyChange * 0.5); // Fallback estimate for others
    const dailyChangePercent = totalNetworth > 0 ? (dailyChange / totalNetworth) * 100 : 0;

    const assetAllocation = [
        { name: 'Zerodha Stocks', value: stocksCurrent, color: '#4f46e5' },
        { name: 'Zerodha MFs', value: mfCurrent, color: '#818cf8' },
        { name: 'US Stocks', value: usCurrent, color: '#10b981' },
        { name: 'Fixed Deposits', value: fdCurrent, color: '#f59e0b' }
    ].filter(a => a.value > 0);

    const topAsset = assetAllocation.length > 0
        ? assetAllocation.reduce((max, current) => max.value > current.value ? max : current).name
        : 'None';

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            return (
                <div className="glass-panel" style={{ padding: '1rem', border: '1px solid var(--border-light)' }}>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>{payload[0].name}</p>
                    <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>₹{payload[0].value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</p>
                </div>
            );
        }
        return null;
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="flex-between">
                <div>
                    <h1 style={{ marginBottom: '0.5rem', fontSize: '2.5rem' }}>Networth Overview</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Track and manage your diverse investment portfolio.</p>
                </div>
                {loading && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
                        <RefreshCw size={16} className="spinning" />
                        <span style={{ fontSize: '0.875rem' }}>Syncing data...</span>
                    </div>
                )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
                <StatCard
                    title="Total Networth"
                    value={totalNetworth}
                    change={dailyChangePercent}
                    isPercent={true}
                    icon={Wallet}
                />
                <StatCard
                    title="Day's Change (Est)"
                    value={dailyChange}
                    change={dailyChange}
                    isPercent={false}
                    icon={Activity}
                />
                <StatCard
                    title="Top Asset Class"
                    value={topAsset}
                    change={0.8}
                    isPercent={true}
                    icon={TrendingUp}
                />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1rem' }}>
                <div className="glass-panel" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ marginBottom: '1.5rem' }}>Asset Allocation</h3>
                    <div style={{ flex: 1, position: 'relative' }}>
                        {assetAllocation.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={assetAllocation}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={80}
                                        outerRadius={120}
                                        paddingAngle={5}
                                        dataKey="value"
                                        stroke="none"
                                    >
                                        {assetAllocation.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip content={<CustomTooltip />} />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex-center" style={{ height: '100%', color: 'var(--text-muted)' }}>No allocation data</div>
                        )}
                        {/* Center Total Text */}
                        {assetAllocation.length > 0 && (
                            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Total</p>
                                <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>₹{(totalNetworth / 10000000).toFixed(2)}Cr</p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="glass-panel">
                    <h3 style={{ marginBottom: '1.5rem' }}>Allocation Details</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {assetAllocation.sort((a, b) => b.value - a.value).map((asset, index) => (
                            <div key={index} className="flex-between" style={{ padding: '1rem', background: 'var(--bg-tertiary)', borderRadius: '12px' }}>
                                <div className="flex-center" style={{ gap: '1rem' }}>
                                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: asset.color }}></div>
                                    <span style={{ fontWeight: 500 }}>{asset.name}</span>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontWeight: 600 }}>₹{asset.value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
                                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                        {((asset.value / totalNetworth) * 100).toFixed(1)}%
                                    </div>
                                </div>
                            </div>
                        ))}
                        {assetAllocation.length === 0 && (
                            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                                No assets found for this profile.
                            </div>
                        )}
                    </div>
                </div>
            </div>
            <style>{`
                @keyframes spin { 100% { transform: rotate(360deg); } }
                .spinning { animation: spin 1s linear infinite; }
            `}</style>
        </div>
    );
};

export default Dashboard;
