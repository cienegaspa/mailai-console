/**
 * OAuth Configuration Diagnostic Tool
 * Helps identify Google Cloud Console configuration issues
 */

const https = require('https');
const http = require('http');

async function diagnoseOAuth() {
    console.log('🔍 MailAI OAuth Configuration Diagnostic');
    console.log('=====================================\n');
    
    // Step 1: Check environment variables
    console.log('1️⃣ Environment Configuration:');
    
    const clientId = process.env.GOOGLE_CLIENT_ID || 'NOT_SET';
    const clientSecret = process.env.GOOGLE_CLIENT_SECRET || 'NOT_SET';
    const redirectUri = process.env.GOOGLE_REDIRECT_URI || 'http://127.0.0.1:5170/auth/callback';
    
    console.log(`   Client ID: ${clientId.substring(0, 20)}...${clientId.substring(clientId.length - 10)}`);
    console.log(`   Client Secret: ${clientSecret !== 'NOT_SET' ? 'SET' : 'NOT_SET'}`);
    console.log(`   Redirect URI: ${redirectUri}`);
    console.log('');
    
    // Step 2: Test MailAI API endpoints
    console.log('2️⃣ MailAI API Status:');
    
    try {
        const statusResponse = await makeRequest('http://127.0.0.1:5170/auth/status');
        console.log(`   OAuth Status API: ${statusResponse.status === 200 ? '✅ Working' : '❌ Failed'}`);
        
        if (statusResponse.status === 200 && statusResponse.data) {
            console.log(`   OAuth Configured: ${statusResponse.data.oauth_configured ? '✅' : '❌'}`);
            console.log(`   Client ID Set: ${statusResponse.data.client_id_set ? '✅' : '❌'}`);  
            console.log(`   Client Secret Set: ${statusResponse.data.client_secret_set ? '✅' : '❌'}`);
            console.log(`   Redirect URI: ${statusResponse.data.redirect_uri}`);
        }
    } catch (e) {
        console.log(`   OAuth Status API: ❌ Error - ${e.message}`);
    }
    console.log('');
    
    // Step 3: Google OAuth Discovery
    console.log('3️⃣ Google OAuth Discovery:');
    
    try {
        const discoveryResponse = await makeHttpsRequest('https://accounts.google.com/.well-known/openid_configuration');
        console.log(`   Google Discovery: ${discoveryResponse.status === 200 ? '✅ Accessible' : '❌ Failed'}`);
        
        if (discoveryResponse.status === 200) {
            const config = discoveryResponse.data;
            console.log(`   Auth Endpoint: ${config.authorization_endpoint}`);
            console.log(`   Token Endpoint: ${config.token_endpoint}`);
        }
    } catch (e) {
        console.log(`   Google Discovery: ❌ Error - ${e.message}`);
    }
    console.log('');
    
    // Step 4: Generate test OAuth URL
    console.log('4️⃣ OAuth URL Generation:');
    
    try {
        const connectResponse = await makeRequest('http://127.0.0.1:5170/auth/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        console.log(`   Connect API: ${connectResponse.status === 200 ? '✅ Working' : '❌ Failed'}`);
        
        if (connectResponse.status === 200 && connectResponse.data.auth_url) {
            const authUrl = new URL(connectResponse.data.auth_url);
            console.log(`   Generated URL: ✅ Valid`);
            console.log(`   Host: ${authUrl.hostname}`);
            console.log(`   Client ID param: ${authUrl.searchParams.get('client_id')?.substring(0, 20)}...`);
            console.log(`   Redirect URI param: ${decodeURIComponent(authUrl.searchParams.get('redirect_uri') || '')}`);
            console.log(`   Scopes: ${decodeURIComponent(authUrl.searchParams.get('scope') || '')}`);
        }
    } catch (e) {
        console.log(`   Connect API: ❌ Error - ${e.message}`);
    }
    console.log('');
    
    // Step 5: Configuration recommendations
    console.log('5️⃣ Configuration Checklist:');
    console.log('');
    console.log('📋 **Google Cloud Console Setup Checklist:**');
    console.log('');
    console.log('   □ 1. Go to https://console.cloud.google.com/');
    console.log('   □ 2. Select your MailAI project');
    console.log('   □ 3. Navigate to APIs & Services > Credentials');
    console.log('   □ 4. Find your OAuth 2.0 Client ID');
    console.log('   □ 5. Click Edit (pencil icon)');
    console.log('   □ 6. Under "Authorized redirect URIs" verify:');
    console.log(`       ✓ Exactly: ${redirectUri}`);
    console.log('   □ 7. Click Save');
    console.log('   □ 8. Navigate to APIs & Services > OAuth consent screen');
    console.log('   □ 9. Under "Test users" add:');
    console.log('       ✓ tom@cienegaspa.com');
    console.log('       ✓ Any other emails you want to test with');
    console.log('   □ 10. Under "Scopes" verify:');
    console.log('        ✓ https://www.googleapis.com/auth/gmail.readonly');
    console.log('        ✓ https://www.googleapis.com/auth/userinfo.email');
    console.log('        ✓ https://www.googleapis.com/auth/userinfo.profile');
    console.log('        ✓ openid');
    console.log('');
    console.log('🔧 **Common Fixes:**');
    console.log('   • Redirect URI must be EXACTLY: http://127.0.0.1:5170/auth/callback');
    console.log('   • No trailing slashes');
    console.log('   • Must be http (not https) for localhost');
    console.log('   • Port 5170 must match your backend server');
    console.log('   • Email must be added as test user');
    console.log('');
    console.log('🧪 **Test Steps:**');
    console.log('   1. Make the above changes in Google Cloud Console');
    console.log('   2. Wait 5-10 minutes for changes to propagate');
    console.log('   3. Restart MailAI servers: Ctrl+C then `make dev`');
    console.log('   4. Try OAuth flow again at http://127.0.0.1:5171/accounts');
}

async function makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
        const req = http.request(url, options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    resolve({ status: res.statusCode, data: jsonData });
                } catch (e) {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });
        
        req.on('error', reject);
        if (options.method === 'POST' && options.body) req.write(options.body);
        req.end();
    });
}

async function makeHttpsRequest(url) {
    return new Promise((resolve, reject) => {
        https.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    resolve({ status: res.statusCode, data: jsonData });
                } catch (e) {
                    resolve({ status: res.statusCode, data: data });
                }
            });
        }).on('error', reject);
    });
}

// Load .env for testing
try {
    require('dotenv').config();
} catch (e) {
    console.log('Note: dotenv not available, using system environment variables');
}

// Run diagnostic
if (require.main === module) {
    diagnoseOAuth()
        .then(() => console.log('🎯 Diagnostic complete!'))
        .catch(err => console.error('❌ Diagnostic failed:', err));
}

module.exports = { diagnoseOAuth };