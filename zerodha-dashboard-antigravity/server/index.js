const express = require('express');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const dotenv = require('dotenv');
const multer = require('multer');
const XLSX = require('xlsx');
const path = require('path');
const fs = require('fs');

// Load env vars before requiring KiteConnect or anything else that might depend on them
dotenv.config();

const { KiteConnect } = require('kiteconnect');

const app = express();
const PORT = process.env.PORT || 5000;

console.log('[DEBUG] KITE_API_KEY loaded:', process.env.KITE_API_KEY ? `${process.env.KITE_API_KEY.substring(0, 4)}...` : 'MISSING');
console.log('[DEBUG] KITE_API_SECRET loaded:', process.env.KITE_API_SECRET ? `${process.env.KITE_API_SECRET.substring(0, 4)}...` : 'MISSING');

app.use(cors({
    origin: ['http://localhost:5173', 'http://127.0.0.1:5173'], // Allow both localhost and 127.0.0.1
    credentials: true
}));
app.use(express.json());
app.use(cookieParser());

// Multer setup for file uploads
const uploadsDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir);
const upload = multer({ dest: uploadsDir });

// Log every incoming request
app.use((req, res, next) => {
    console.log(`\n[REQUEST] ${req.method} ${req.url}`);
    console.log('[REQUEST] Cookies:', JSON.stringify(req.cookies));
    next();
});

// Initialize KiteConnect instance after dotenv.config()
const kc = new KiteConnect({
    api_key: process.env.KITE_API_KEY
});

// In-memory stores
const sessions = {};
const importedHoldings = {}; // { member: { stocks: [...], uploadedAt: Date } }

// Helper: get access token from cookies
function getAccessToken(req) {
    const sessionId = req.cookies.sessionId;
    return sessionId ? sessions[sessionId] : null;
}

// Helper: find the header row in a Zerodha sheet (they have ~22 rows of preamble)
function findDataInSheet(sheet) {
    // Convert entire sheet to array-of-arrays to scan for the header row
    const allRows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });

    // Find the row that contains 'Symbol' — that's our header row
    let headerRowIdx = -1;
    for (let i = 0; i < allRows.length; i++) {
        const row = allRows[i];
        if (row.some(cell => String(cell).trim().toLowerCase() === 'symbol')) {
            headerRowIdx = i;
            break;
        }
        // Also check for 'Scheme' header (for MF sheet)
        if (row.some(cell => String(cell).trim().toLowerCase() === 'scheme')) {
            headerRowIdx = i;
            break;
        }
    }

    if (headerRowIdx === -1) return [];

    // Use the header row as column names, data starts from next row
    const headers = allRows[headerRowIdx].map(h => String(h).trim());
    const dataRows = allRows.slice(headerRowIdx + 1)
        .filter(row => row.some(cell => cell !== '' && cell !== null && cell !== undefined));

    // Convert to array of objects
    return dataRows.map(row => {
        const obj = {};
        headers.forEach((header, idx) => {
            if (header) obj[header] = row[idx] !== undefined ? row[idx] : '';
        });
        return obj;
    });
}

// Helper: parse a Zerodha XLSX and extract stocks + MFs
function parseZerodhaXLSX(filePath) {
    const workbook = XLSX.readFile(filePath);
    console.log('[IMPORT] Sheet names:', workbook.SheetNames);

    const result = { stocks: [], mfs: [] };

    // --- Parse Equity sheet ---
    const equitySheetName = workbook.SheetNames.find(n =>
        n.toLowerCase().includes('equity') || n.toLowerCase() === 'sheet1'
    ) || workbook.SheetNames[0];

    const equitySheet = workbook.Sheets[equitySheetName];
    const equityRows = findDataInSheet(equitySheet);
    console.log('[IMPORT] Equity sheet:', equitySheetName, '| Data rows:', equityRows.length);

    if (equityRows.length > 0) {
        const keys = Object.keys(equityRows[0]);
        console.log('[IMPORT] Equity columns:', keys);
        console.log('[IMPORT] First equity row:', JSON.stringify(equityRows[0]));

        const find = (patterns) => keys.find(k =>
            patterns.some(p => k.toLowerCase().replace(/[.\s]/g, '').includes(p))
        );

        const symbolCol = find(['symbol', 'instrument', 'tradingsymbol', 'scrip']);
        const qtyCol = find(['quantityavail', 'qty', 'quantity']);
        const avgPriceCol = find(['averageprice', 'avgprice', 'avgcost', 'averagecost']);
        const closePriceCol = find(['previousclos', 'closingprice', 'ltp', 'lastprice', 'closeprice']);
        const pnlPctCol = find(['unrealizedp&lpct', 'unrealisedp&lpct', 'p&lpct', 'pnlpct', 'unrealizedpnlpct']);

        if (!symbolCol) throw new Error(`Could not find symbol column. Found: ${keys.join(', ')}`);
        if (!qtyCol) throw new Error(`Could not find quantity column. Found: ${keys.join(', ')}`);

        console.log('[IMPORT] Detected equity columns:', { symbolCol, qtyCol, avgPriceCol, closePriceCol, pnlPctCol });

        result.stocks = equityRows
            .filter(row => row[symbolCol] && Number(row[qtyCol]) > 0)
            .map(row => {
                const qty = Number(row[qtyCol]) || 0;
                const avgPrice = avgPriceCol ? (Number(row[avgPriceCol]) || 0) : 0;
                const ltp = closePriceCol ? (Number(row[closePriceCol]) || 0) : 0;
                const dayChange = pnlPctCol ? (Number(row[pnlPctCol]) || 0) : 0;

                return {
                    symbol: String(row[symbolCol]).trim(),
                    name: String(row[symbolCol]).trim(),
                    qty,
                    avgPrice,
                    ltp,
                    invested: qty * avgPrice,
                    dayChange: Number(dayChange.toFixed(2))
                };
            });

        console.log('[IMPORT] Parsed', result.stocks.length, 'stocks');
    }

    // --- Parse Mutual Funds sheet (if exists) ---
    const mfSheetName = workbook.SheetNames.find(n =>
        n.toLowerCase().includes('mutual') || n.toLowerCase().includes('mf')
    );

    if (mfSheetName) {
        const mfSheet = workbook.Sheets[mfSheetName];
        const mfRows = findDataInSheet(mfSheet);
        console.log('[IMPORT] MF sheet:', mfSheetName, '| Data rows:', mfRows.length);

        if (mfRows.length > 0) {
            const mfKeys = Object.keys(mfRows[0]);
            console.log('[IMPORT] MF columns:', mfKeys);

            const findMF = (patterns) => mfKeys.find(k =>
                patterns.some(p => k.toLowerCase().replace(/[.\s]/g, '').includes(p))
            );

            const nameCol = findMF(['scheme', 'fund', 'name', 'symbol', 'instrument', 'tradingsymbol']);
            const unitsCol = findMF(['quantityavail', 'units', 'quantity', 'qty']);
            const navAvgCol = findMF(['averageprice', 'avgnavprice', 'averagenav', 'avgnav', 'avgprice', 'purchaseprice']);
            const navCurrentCol = findMF(['previousclos', 'currentnav', 'nav', 'latestnav', 'lastnav', 'ltp', 'lastprice']);

            if (nameCol && unitsCol) {
                result.mfs = mfRows
                    .filter(row => row[nameCol] && Number(row[unitsCol]) > 0)
                    .map(row => {
                        const units = Number(row[unitsCol]) || 0;
                        const navAvg = navAvgCol ? (Number(row[navAvgCol]) || 0) : 0;
                        const ltp = navCurrentCol ? (Number(row[navCurrentCol]) || 0) : 0;

                        return {
                            name: String(row[nameCol]).trim(),
                            units,
                            navAvg,
                            ltp,
                            invested: units * navAvg,
                            type: 'Mutual Fund'
                        };
                    });

                console.log('[IMPORT] Parsed', result.mfs.length, 'mutual funds');
            }
        }
    }

    if (result.stocks.length === 0 && result.mfs.length === 0) {
        throw new Error('No holdings data found in the Excel file. Check the file format.');
    }

    return result;
}

// Helper: enrich holdings with live LTP from Kite API
async function enrichWithLiveLTP(stocks, accessToken) {
    if (!accessToken) {
        console.log('[IMPORT] No access token — skipping live LTP enrichment');
        return stocks;
    }

    try {
        kc.setAccessToken(accessToken);

        // Build instrument list in NSE:SYMBOL format (batch of 500 max)
        const instruments = stocks.map(s => `NSE:${s.symbol}`);
        console.log('[IMPORT] Fetching LTP for', instruments.length, 'instruments');

        const ltpData = await kc.getLTP(instruments);
        console.log('[IMPORT] LTP response keys:', Object.keys(ltpData).length);

        return stocks.map(stock => {
            const key = `NSE:${stock.symbol}`;
            if (ltpData[key]) {
                return {
                    ...stock,
                    ltp: ltpData[key].last_price,
                };
            }
            // Try BSE if NSE not found
            return stock;
        });
    } catch (err) {
        console.error('[IMPORT] Error fetching LTP:', err.message);
        return stocks; // Return with original prices on error
    }
}

// 1. Redirect to Login
app.get('/api/auth/login', (req, res) => {
    const loginUrl = kc.getLoginURL();
    console.log('[AUTH LOGIN] Redirecting to:', loginUrl);
    res.redirect(loginUrl);
});

// 2. Handle Login Callback from Kite
app.get('/api/auth/callback', async (req, res) => {
    console.log('[AUTH CALLBACK] Full query params:', JSON.stringify(req.query));
    const { request_token } = req.query;

    if (!request_token) {
        console.error('[AUTH CALLBACK] No request_token in query params!');
        return res.status(400).send('No request token found in query params');
    }

    console.log('[AUTH CALLBACK] Got request_token:', request_token);

    try {
        // Exchange the request token for an access token
        console.log('[AUTH CALLBACK] Calling generateSession with API secret...');
        const response = await kc.generateSession(request_token, process.env.KITE_API_SECRET);
        console.log('[AUTH CALLBACK] generateSession response keys:', Object.keys(response));
        console.log('[AUTH CALLBACK] access_token received:', response.access_token ? 'YES' : 'NO');

        // Create a simple session cookie
        const sessionId = Math.random().toString(36).substring(7);
        sessions[sessionId] = response.access_token;
        console.log('[AUTH CALLBACK] Created sessionId:', sessionId);
        console.log('[AUTH CALLBACK] Active sessions count:', Object.keys(sessions).length);

        res.cookie('sessionId', sessionId, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            maxAge: 24 * 60 * 60 * 1000 // 1 day
        });
        console.log('[AUTH CALLBACK] Cookie set. Redirecting to frontend...');

        // Redirect back to frontend — use localhost to keep cookie domain consistent
        res.redirect('http://localhost:5173/');
    } catch (error) {
        console.error('[AUTH CALLBACK] Error generating session:', error);
        console.error('[AUTH CALLBACK] Error details:', JSON.stringify(error, null, 2));
        res.status(500).send('Failed to authenticate with Zerodha');
    }
});

// 3. Endpoint to fetch live holdings (for authenticated user — Meher)
app.get('/api/portfolio/holdings', async (req, res) => {
    const accessToken = getAccessToken(req);
    console.log('[HOLDINGS] accessToken found:', accessToken ? 'YES' : 'NO');

    if (!accessToken) {
        console.error('[HOLDINGS] Not authenticated — no valid session');
        return res.status(401).json({ error: 'Not authenticated with Zerodha' });
    }

    try {
        // We need to set the access token on the instance for subsequent calls
        kc.setAccessToken(accessToken);
        console.log('[HOLDINGS] Access token set on KiteConnect instance');

        console.log('[HOLDINGS] Calling kc.getHoldings()...');
        const holdings = await kc.getHoldings();
        console.log('[HOLDINGS] Raw holdings count:', holdings.length);
        console.log('[HOLDINGS] First holding sample:', holdings.length > 0 ? JSON.stringify(holdings[0]) : 'EMPTY');

        // Fetch MF holdings too
        let mfHoldings = [];
        try {
            console.log('[HOLDINGS] Calling kc.getMFHoldings()...');
            mfHoldings = await kc.getMFHoldings();
            console.log('[HOLDINGS] Raw MF holdings count:', mfHoldings.length);
            console.log('[HOLDINGS] First MF holding sample:', mfHoldings.length > 0 ? JSON.stringify(mfHoldings[0]) : 'EMPTY');
        } catch (mfError) {
            console.error('[HOLDINGS] Error fetching MF holdings (continuing with empty):', mfError.message);
        }

        // Convert to the shape our frontend expects
        const formattedStocks = holdings.map(h => ({
            symbol: h.tradingsymbol,
            name: h.tradingsymbol,
            qty: h.quantity,
            avgPrice: h.average_price,
            ltp: h.last_price,
            invested: h.quantity * h.average_price,
            dayChange: h.day_change_percentage
        }));

        const formattedMFs = mfHoldings.map(mf => ({
            name: mf.fund,
            units: mf.quantity,
            navAvg: mf.average_price,
            ltp: mf.last_price,
            invested: mf.quantity * mf.average_price,
            type: 'Mutual Fund'
        }));

        console.log('[HOLDINGS] Formatted stocks:', formattedStocks.length, '| MFs:', formattedMFs.length);

        res.json({
            zerodhaStocks: formattedStocks,
            zerodhaMFs: formattedMFs
        });

    } catch (error) {
        console.error('[HOLDINGS] Error fetching holdings:', error);
        console.error('[HOLDINGS] Error details:', JSON.stringify(error, null, 2));
        if (error.status === 'error' && error.error_type === 'TokenException') {
            res.status(401).json({ error: 'Token expired. Please login again.' });
        } else {
            res.status(500).json({ error: 'Failed to fetch holdings' });
        }
    }
});

// 4. Import portfolio from Excel file (for family members)
app.post('/api/portfolio/import', upload.single('file'), async (req, res) => {
    const member = req.body.member;

    if (!member) {
        return res.status(400).json({ error: 'Missing "member" field (e.g. spouse, father)' });
    }

    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    console.log('[IMPORT] File received:', req.file.originalname, 'for member:', member);

    try {
        // Parse the XLSX
        const parsed = parseZerodhaXLSX(req.file.path);
        console.log('[IMPORT] Parsed', parsed.stocks.length, 'stocks and', parsed.mfs.length, 'MFs');

        // Try to enrich with live LTP if an authenticated session exists
        const accessToken = getAccessToken(req);
        const enrichedStocks = await enrichWithLiveLTP(parsed.stocks, accessToken);
        // (We could also enrich MFs if needed, but getLTP is mostly for stocks)

        // Store for later retrieval
        importedHoldings[member] = {
            stocks: enrichedStocks,
            mfs: parsed.mfs,
            uploadedAt: new Date().toISOString(),
            originalFile: req.file.originalname
        };

        console.log('[IMPORT] Stored holdings for', member, ':', enrichedStocks.length, 'stocks,', parsed.mfs.length, 'MFs');

        // Clean up uploaded file
        fs.unlinkSync(req.file.path);

        res.json({
            success: true,
            member,
            zerodhaStocks: enrichedStocks,
            zerodhaMFs: parsed.mfs,
            livePrices: !!accessToken,
            stockCount: enrichedStocks.length,
            mfCount: parsed.mfs.length
        });

    } catch (error) {
        console.error('[IMPORT] Error:', error.message);
        // Clean up file on error
        if (req.file && fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);
        res.status(400).json({ error: error.message });
    }
});

// 5. Get previously imported holdings with refreshed LTP
app.get('/api/portfolio/imported/:member', async (req, res) => {
    const { member } = req.params;

    if (!importedHoldings[member]) {
        return res.status(404).json({ error: `No imported data for member: ${member}` });
    }

    console.log('[IMPORTED] Fetching holdings for', member);

    const accessToken = getAccessToken(req);
    const stored = importedHoldings[member];

    // Re-fetch live prices
    const enrichedStocks = await enrichWithLiveLTP(stored.stocks, accessToken);

    // Update stored data with latest prices
    importedHoldings[member].stocks = enrichedStocks;

    res.json({
        zerodhaStocks: enrichedStocks,
        zerodhaMFs: stored.mfs,
        livePrices: !!accessToken,
        uploadedAt: stored.uploadedAt,
        originalFile: stored.originalFile
    });
});

// Check auth status
app.get('/api/auth/status', (req, res) => {
    const sessionId = req.cookies.sessionId;
    const hasSession = !!(sessionId && sessions[sessionId]);

    // Also report which members have imported data
    const importedMembers = Object.keys(importedHoldings);

    res.json({
        authenticated: hasSession,
        importedMembers
    });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
    console.log('[DEBUG] Login URL would be:', kc.getLoginURL());
});
