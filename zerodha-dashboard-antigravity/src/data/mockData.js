export const FAMILY_MEMBERS = [
    { id: 'meher', name: 'Meher (Self)', relation: 'Self' },
    { id: 'spouse', name: 'Priya (Spouse)', relation: 'Spouse' },
    { id: 'father', name: 'Ramesh (Father)', relation: 'Father' }
];

// Utility to generate random fluctuations
const fluctuation = (base, variance = 0.05) => {
    return base + (base * (Math.random() * variance * 2 - variance));
};

export const MOCK_DATA = {
    meher: {
        overview: {
            totalNetworth: 15420000,
            dailyChange: 24500,
            dailyChangePercent: 0.16,
            assetAllocation: [
                { name: 'Zerodha Stocks', value: 6500000, color: '#4f46e5' },
                { name: 'Zerodha MFs', value: 4200000, color: '#818cf8' },
                { name: 'US Stocks', value: 2800000, color: '#10b981' },
                { name: 'Fixed Deposits', value: 1920000, color: '#f59e0b' }
            ]
        },
        zerodhaStocks: [
            { symbol: 'RELIANCE', name: 'Reliance Industries', qty: 250, avgPrice: 2450.50, ltp: fluctuation(2980), invested: 612625, dayChange: 1.2 },
            { symbol: 'TCS', name: 'Tata Consultancy Services', qty: 150, avgPrice: 3100.00, ltp: fluctuation(4120), invested: 465000, dayChange: -0.5 },
            { symbol: 'INFY', name: 'Infosys Ltd', qty: 400, avgPrice: 1450.20, ltp: fluctuation(1680), invested: 580080, dayChange: 0.8 },
            { symbol: 'HDFCBANK', name: 'HDFC Bank', qty: 500, avgPrice: 1580.00, ltp: fluctuation(1440), invested: 790000, dayChange: -1.2 },
            { symbol: 'ICICIBANK', name: 'ICICI Bank', qty: 600, avgPrice: 850.50, ltp: fluctuation(1080), invested: 510300, dayChange: 2.1 }
        ],
        zerodhaMFs: [
            { name: 'Parag Parikh Flexi Cap Direct', units: 4500.5, navAvg: 45.20, ltp: fluctuation(68.5), invested: 203422, type: 'Equity' },
            { name: 'UTI Nifty 50 Index Fund', units: 12500.8, navAvg: 112.50, ltp: fluctuation(145.2), invested: 1406340, type: 'Index' },
            { name: 'Mirae Asset Large Cap', units: 8500.0, navAvg: 85.00, ltp: fluctuation(112.4), invested: 722500, type: 'Equity' }
        ],
        usStocks: [
            { symbol: 'AAPL', name: 'Apple Inc.', qty: 50, avgPrice: 150.20, ltp: fluctuation(185.5, 0.02), invested: 7510, currency: 'USD', dayChange: 0.5 },
            { symbol: 'MSFT', name: 'Microsoft Corp.', qty: 30, avgPrice: 280.50, ltp: fluctuation(405.2, 0.02), invested: 8415, currency: 'USD', dayChange: 1.1 },
            { symbol: 'GOOGL', name: 'Alphabet Inc.', qty: 40, avgPrice: 110.00, ltp: fluctuation(145.8, 0.02), invested: 4400, currency: 'USD', dayChange: -0.3 }
        ],
        fixedDeposits: [
            { bank: 'HDFC Bank', principal: 500000, interestRate: 7.1, maturityDate: '2025-08-15', currentVal: 535500 },
            { bank: 'SBI', principal: 1000000, interestRate: 6.8, maturityDate: '2026-02-20', currentVal: 1068000 },
            { bank: 'ICICI Bank', principal: 420000, interestRate: 7.25, maturityDate: '2024-11-10', currentVal: 450450 }
        ]
    },
    spouse: {
        overview: {
            totalNetworth: 8500000,
            dailyChange: 12400,
            dailyChangePercent: 0.15,
            assetAllocation: [
                { name: 'Zerodha Stocks', value: 3500000, color: '#4f46e5' },
                { name: 'Zerodha MFs', value: 2500000, color: '#818cf8' },
                { name: 'US Stocks', value: 0, color: '#10b981' },
                { name: 'Fixed Deposits', value: 2500000, color: '#f59e0b' }
            ]
        },
        zerodhaStocks: [
            { symbol: 'ITC', name: 'ITC Ltd', qty: 1500, avgPrice: 280.00, ltp: fluctuation(420.5), invested: 420000, dayChange: 0.4 },
            { symbol: 'LT', name: 'Larsen & Toubro', qty: 100, avgPrice: 2200.00, ltp: fluctuation(3540), invested: 220000, dayChange: 1.5 }
        ],
        zerodhaMFs: [
            { name: 'SBI Small Cap Fund', units: 3500.0, navAvg: 88.50, ltp: fluctuation(155.2), invested: 309750, type: 'Equity' },
            { name: 'HDFC Balanced Advantage', units: 5500.0, navAvg: 245.00, ltp: fluctuation(310.5), invested: 1347500, type: 'Hybrid' }
        ],
        usStocks: [],
        fixedDeposits: [
            { bank: 'Axis Bank', principal: 2500000, interestRate: 7.5, maturityDate: '2027-01-10', currentVal: 2687500 }
        ]
    },
    father: {
        overview: {
            totalNetworth: 22500000,
            dailyChange: 18000,
            dailyChangePercent: 0.08,
            assetAllocation: [
                { name: 'Zerodha Stocks', value: 4500000, color: '#4f46e5' },
                { name: 'Zerodha MFs', value: 3000000, color: '#818cf8' },
                { name: 'US Stocks', value: 0, color: '#10b981' },
                { name: 'Fixed Deposits', value: 15000000, color: '#f59e0b' }
            ]
        },
        zerodhaStocks: [
            { symbol: 'RELIANCE', name: 'Reliance Industries', qty: 500, avgPrice: 1200.00, ltp: fluctuation(2980), invested: 600000, dayChange: 1.2 },
            { symbol: 'HUL', name: 'Hindustan Unilever', qty: 300, avgPrice: 1800.00, ltp: fluctuation(2450), invested: 540000, dayChange: -0.2 }
        ],
        zerodhaMFs: [
            { name: 'Nippon India Liquid Fund', units: 45000.0, navAvg: 51.20, ltp: fluctuation(54.5, 0.001), invested: 2304000, type: 'Debt' }
        ],
        usStocks: [],
        fixedDeposits: [
            { bank: 'SBI', principal: 10000000, interestRate: 7.8, maturityDate: '2028-05-20', currentVal: 11500000 },
            { bank: 'Post Office MIS', principal: 5000000, interestRate: 7.4, maturityDate: '2025-12-15', currentVal: 5000000 }
        ]
    }
};

export const USD_TO_INR = 83.50;
