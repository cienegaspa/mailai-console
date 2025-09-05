/**
 * Real OAuth Flow Test with Google
 * This will actually go through the Google OAuth flow
 */

const puppeteer = require('puppeteer');

async function testRealOAuthFlow() {
    console.log('🔵 Starting REAL OAuth flow test with Google...');
    console.log('⚠️ This will open Google OAuth and require manual interaction');
    
    const browser = await puppeteer.launch({
        headless: false,  // Show browser for OAuth interaction
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        defaultViewport: { width: 1280, height: 720 }
    });
    
    const page = await browser.newPage();
    
    try {
        // Step 1: Navigate to accounts page
        console.log('📄 Navigating to accounts page...');
        await page.goto('http://127.0.0.1:5171/accounts', { waitUntil: 'networkidle2' });
        await page.screenshot({ path: 'real-oauth-1-accounts.png' });
        
        // Step 2: Check current account status
        console.log('🔍 Checking current account status...');
        const currentAccounts = await page.evaluate(async () => {
            try {
                const response = await fetch('http://127.0.0.1:5170/accounts');
                return await response.json();
            } catch (e) {
                return [];
            }
        });
        console.log(`📊 Current accounts: ${currentAccounts.length}`);
        if (currentAccounts.length > 0) {
            console.log(`   First account: ${currentAccounts[0].email} (${currentAccounts[0].status})`);
        }
        
        // Step 3: Get OAuth URL
        console.log('🔗 Getting OAuth connect URL...');
        const oauthData = await page.evaluate(async () => {
            const response = await fetch('http://127.0.0.1:5170/auth/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            return await response.json();
        });
        
        console.log('✅ OAuth URL generated:', !!oauthData.auth_url);
        console.log('🔗 Auth URL:', oauthData.auth_url);
        
        // Step 4: Navigate to OAuth URL
        console.log('🚀 Navigating to Google OAuth...');
        console.log('👆 Please complete the OAuth flow manually in the browser window');
        console.log('🔄 Waiting for OAuth callback...');
        
        await page.goto(oauthData.auth_url, { waitUntil: 'networkidle2' });
        await page.screenshot({ path: 'real-oauth-2-google-consent.png' });
        
        // Step 5: Wait for redirect back to our app
        console.log('⏳ Waiting for OAuth callback (up to 2 minutes)...');
        
        // Wait for either success or error redirect
        await page.waitForFunction(() => {
            return window.location.href.includes('127.0.0.1:5171') && 
                   (window.location.href.includes('connected=') || 
                    window.location.href.includes('error='));
        }, { timeout: 120000 }); // 2 minute timeout
        
        await page.screenshot({ path: 'real-oauth-2-local-response.png' });
        
        // Step 6: Check the result
        const finalUrl = await page.url();
        console.log('🏁 Final URL:', finalUrl);
        
        if (finalUrl.includes('connected=')) {
            const email = new URL(finalUrl).searchParams.get('connected');
            console.log('✅ OAuth SUCCESS! Connected email:', email);
        } else if (finalUrl.includes('error=')) {
            const error = new URL(finalUrl).searchParams.get('error');
            console.log('❌ OAuth ERROR:', error);
        }
        
        // Step 7: Check final account status
        console.log('🔍 Checking final account status...');
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait a bit for DB update
        
        const finalAccounts = await page.evaluate(async () => {
            const response = await fetch('http://127.0.0.1:5170/accounts');
            return await response.json();
        });
        
        console.log('📊 Final accounts status:');
        finalAccounts.forEach((account, index) => {
            console.log(`   ${index + 1}. ${account.email} - Status: ${account.status}`);
            console.log(`      Connected at: ${account.connected_at || 'Never'}`);
            console.log(`      Tokens: Access=${!!account.access_token}, Refresh=${!!account.refresh_token}`);
        });
        
        // Keep browser open for inspection
        console.log('🔍 Browser will stay open for 30 seconds for inspection...');
        await new Promise(resolve => setTimeout(resolve, 30000));
        
        return {
            success: finalUrl.includes('connected='),
            accounts: finalAccounts
        };
        
    } catch (error) {
        console.error('❌ Real OAuth test failed:', error);
        await page.screenshot({ path: 'real-oauth-error.png' });
        throw error;
    } finally {
        await browser.close();
    }
}

// Monitor backend logs during the test
async function monitorBackendLogs() {
    console.log('👂 Monitoring backend logs for OAuth activity...');
    
    // This function would monitor the backend logs
    // For now, just remind user to watch the terminal
    console.log('📝 Watch the backend terminal for detailed OAuth logs with 🔵, ✅, and ❌ emojis');
}

// Run the test
if (require.main === module) {
    console.log('🚨 IMPORTANT: This test will open a browser window and require you to:');
    console.log('   1. Sign in to Google (if not already signed in)');
    console.log('   2. Select or confirm the account (tom@cienegaspa.com)');
    console.log('   3. Grant permissions to MailAI Console');
    console.log('');
    console.log('Press Ctrl+C to cancel or wait 5 seconds to continue...');
    
    setTimeout(async () => {
        try {
            monitorBackendLogs();
            const result = await testRealOAuthFlow();
            console.log('');
            console.log('🎉 Real OAuth flow test completed!');
            console.log('📋 Result:', result.success ? 'SUCCESS' : 'FAILED');
            console.log(`📊 Connected accounts: ${result.accounts.filter(a => a.status === 'connected').length}`);
            process.exit(0);
        } catch (error) {
            console.error('💥 Real OAuth flow test failed:', error);
            process.exit(1);
        }
    }, 5000);
}

module.exports = { testRealOAuthFlow };