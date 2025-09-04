const puppeteer = require('puppeteer');

async function testRealGmailOAuth() {
  const browser = await puppeteer.launch({ 
    headless: true,
    defaultViewport: { width: 1280, height: 800 }
  });
  
  try {
    const page = await browser.newPage();
    
    // Capture console logs
    page.on('console', msg => {
      console.log(`[BROWSER] ${msg.text()}`);
    });
    
    console.log('🔵 Step 1: Loading accounts page...');
    await page.goto('http://127.0.0.1:5171/accounts', { 
      waitUntil: 'networkidle0',
      timeout: 10000 
    });
    
    await page.screenshot({ path: 'real-oauth-1-accounts.png', fullPage: true });
    console.log('✓ Screenshot 1: Accounts page loaded');
    
    // Check current state
    const pageState = await page.evaluate(() => {
      return {
        hasConnectButton: Array.from(document.querySelectorAll('button')).some(btn => 
          btn.textContent.includes('Connect Account')
        ),
        hasAccountData: document.querySelector('table tbody tr') !== null,
        hasMockNotice: document.body.textContent.includes('Mock') || 
                      document.body.textContent.includes('Development Mode'),
        hasSetupNotice: document.body.textContent.includes('Setup Required') ||
                       document.body.textContent.includes('OAuth credentials')
      };
    });
    
    console.log('🔵 Page state:', pageState);
    
    if (pageState.hasConnectButton) {
      console.log('🔵 Step 2: Testing Connect Account button...');
      
      // Click Connect Account button
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const connectBtn = buttons.find(btn => btn.textContent.includes('Connect Account'));
        if (connectBtn) {
          console.log('🔵 Found Connect Account button, clicking...');
          connectBtn.click();
        }
      });
      
      // Wait for redirect or navigation
      try {
        await page.waitForNavigation({ timeout: 5000 });
        console.log('✓ Navigation occurred - likely redirected to Google OAuth!');
        
        const currentUrl = page.url();
        console.log('🔵 Current URL:', currentUrl);
        
        if (currentUrl.includes('accounts.google.com')) {
          console.log('🎉 SUCCESS: Redirected to real Google OAuth consent screen!');
          await page.screenshot({ path: 'real-oauth-2-google-consent.png', fullPage: true });
        } else if (currentUrl.includes('localhost') || currentUrl.includes('127.0.0.1')) {
          console.log('🔵 Stayed on local site, checking for error messages...');
          await page.screenshot({ path: 'real-oauth-2-local-response.png', fullPage: true });
        }
        
      } catch (timeoutError) {
        console.log('⚠️ No navigation detected, checking page response...');
        await page.screenshot({ path: 'real-oauth-2-no-navigation.png', fullPage: true });
      }
    }
    
    // Test API endpoint directly
    console.log('🔵 Step 3: Testing OAuth connect API directly...');
    const apiResult = await page.evaluate(async () => {
      try {
        const response = await fetch('http://127.0.0.1:5170/auth/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        
        const result = {
          status: response.status,
          statusText: response.statusText,
          headers: Object.fromEntries(response.headers.entries())
        };
        
        if (response.ok) {
          const data = await response.json();
          result.data = data;
        } else {
          const text = await response.text();
          result.error = text;
        }
        
        return result;
      } catch (error) {
        return { error: error.message, stack: error.stack };
      }
    });
    
    console.log('✅ API test result:', JSON.stringify(apiResult, null, 2));
    
    if (apiResult.data && apiResult.data.auth_url) {
      console.log('🎉 SUCCESS: Real OAuth URL generated!');
      console.log('🔗 OAuth URL:', apiResult.data.auth_url);
      
      if (apiResult.data.auth_url.includes('accounts.google.com')) {
        console.log('✅ CONFIRMED: Using real Google OAuth (not mock)');
      }
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error);
    await page.screenshot({ path: 'real-oauth-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
}

console.log('Testing real Gmail OAuth integration...');
testRealGmailOAuth().then(() => {
  console.log('Real OAuth test completed!');
}).catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});