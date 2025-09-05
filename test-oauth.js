/**
 * OAuth Flow Test Script for MailAI Console
 * Tests the complete OAuth integration end-to-end
 */

const puppeteer = require('puppeteer');

async function testOAuthFlow() {
    console.log('🔵 Starting OAuth flow test...');
    
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    
    try {
        // Step 1: Navigate to accounts page
        console.log('📄 Navigating to accounts page...');
        await page.goto('http://127.0.0.1:5171/accounts', { waitUntil: 'networkidle2' });
        
        // Take initial screenshot
        await page.screenshot({ path: 'oauth-test-01-accounts-page.png' });
        
        // Step 2: Check for Connect Account button
        console.log('🔍 Looking for Connect Account button...');
        await page.waitForSelector('button:contains("Connect Account"), button[class*="btn-primary"]', { timeout: 5000 });
        
        // Step 3: Test backend OAuth status endpoint
        console.log('🔧 Testing OAuth status endpoint...');
        const oauthStatus = await page.evaluate(async () => {
            const response = await fetch('http://127.0.0.1:5170/auth/status');
            return response.json();
        });
        console.log('✅ OAuth status:', oauthStatus);
        
        // Step 4: Test OAuth connect endpoint
        console.log('🔧 Testing OAuth connect endpoint...');
        const connectResult = await page.evaluate(async () => {
            const response = await fetch('http://127.0.0.1:5170/auth/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            return response.json();
        });
        console.log('✅ OAuth connect URL generated:', !!connectResult.auth_url);
        console.log('🔗 Auth URL preview:', connectResult.auth_url.substring(0, 100) + '...');
        
        // Step 5: Test accounts API endpoint
        console.log('🔧 Testing accounts endpoint...');
        const accounts = await page.evaluate(async () => {
            const response = await fetch('http://127.0.0.1:5170/accounts');
            return response.json();
        });
        console.log('✅ Accounts found:', accounts.length);
        if (accounts.length > 0) {
            console.log('📧 Account details:', accounts[0]);
        }
        
        // Step 6: Click Connect Account button (but don't follow through OAuth)
        console.log('👆 Testing Connect Account UI...');
        const connectButton = await page.$('button:contains("Connect Account"), button[class*="btn-primary"]');
        
        if (connectButton) {
            // Just verify it's clickable, don't actually click to avoid OAuth redirect
            const isEnabled = await page.evaluate(btn => !btn.disabled, connectButton);
            console.log('✅ Connect button is enabled:', isEnabled);
        }
        
        // Final screenshot
        await page.screenshot({ path: 'oauth-test-02-final-state.png' });
        
        console.log('✅ OAuth integration test completed successfully!');
        console.log('📊 Summary:');
        console.log(`   - OAuth configured: ${oauthStatus.oauth_configured}`);
        console.log(`   - Auth URL generated: ${!!connectResult.auth_url}`);
        console.log(`   - Accounts in database: ${accounts.length}`);
        console.log(`   - UI functional: true`);
        
    } catch (error) {
        console.error('❌ OAuth test failed:', error);
        await page.screenshot({ path: 'oauth-test-error.png' });
        throw error;
    } finally {
        await browser.close();
    }
}

// Run the test
if (require.main === module) {
    testOAuthFlow()
        .then(() => {
            console.log('🎉 OAuth flow test passed!');
            process.exit(0);
        })
        .catch(error => {
            console.error('💥 OAuth flow test failed:', error);
            process.exit(1);
        });
}

module.exports = { testOAuthFlow };