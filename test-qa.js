const puppeteer = require('puppeteer');

async function testQAFunctionality() {
    console.log('🧪 Testing Q&A functionality...');
    
    const browser = await puppeteer.launch({ 
        headless: false,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    
    // Capture console messages
    page.on('console', msg => {
        console.log(`📝 Console ${msg.type().toUpperCase()}: ${msg.text()}`);
    });
    
    try {
        // Navigate to runs list
        console.log('📄 Loading runs list...');
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle2' });
        
        // Wait for the table to load and click "View" on the first run
        await page.waitForSelector('a[href*="/runs/"]', { timeout: 10000 });
        
        console.log('🔗 Clicking View on first run...');
        await page.click('a[href*="/runs/"]:last-child');
        
        // Wait for run detail page to load
        await page.waitForSelector('[placeholder*="follow-up"]', { timeout: 10000 });
        
        console.log('📸 Taking screenshot of run detail page...');
        await page.screenshot({ 
            path: '/Users/tom/Projects/mailai-console/run-detail-screenshot.png',
            fullPage: true 
        });
        
        // Test the Q&A functionality
        console.log('💬 Testing Q&A input...');
        const testQuestion = 'What was the root cause of these returns?';
        
        await page.type('[placeholder*="follow-up"]', testQuestion);
        
        // Click send button
        await page.click('button[type="submit"]');
        
        // Wait a moment for the API call to complete
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Take another screenshot to see the result
        console.log('📸 Taking screenshot after Q&A submission...');
        await page.screenshot({ 
            path: '/Users/tom/Projects/mailai-console/qa-test-result.png',
            fullPage: true 
        });
        
        console.log('✅ Q&A test complete! Check:');
        console.log('   - run-detail-screenshot.png for run detail view');
        console.log('   - qa-test-result.png for Q&A interaction result');
        
    } catch (error) {
        console.error('❌ Error during Q&A test:', error.message);
        
        // Take error screenshot
        await page.screenshot({ 
            path: '/Users/tom/Projects/mailai-console/qa-error-screenshot.png',
            fullPage: true 
        });
    } finally {
        await browser.close();
    }
}

testQAFunctionality().catch(console.error);