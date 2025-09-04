const puppeteer = require('puppeteer');
const fs = require('fs');

async function diagnoseFrontend() {
    console.log('🔍 Starting frontend diagnosis with Puppeteer...');
    
    const browser = await puppeteer.launch({ 
        headless: false,  // Show browser for debugging
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    
    const page = await browser.newPage();
    
    // Set viewport
    await page.setViewport({ width: 1920, height: 1080 });
    
    // Capture console messages
    const consoleMessages = [];
    page.on('console', msg => {
        const type = msg.type();
        const text = msg.text();
        consoleMessages.push({ type, text, timestamp: new Date().toISOString() });
        console.log(`📝 Console ${type.toUpperCase()}: ${text}`);
    });
    
    // Capture network failures
    const networkErrors = [];
    page.on('requestfailed', request => {
        const error = {
            url: request.url(),
            failure: request.failure().errorText,
            timestamp: new Date().toISOString()
        };
        networkErrors.push(error);
        console.log(`🚫 Network Error: ${error.url} - ${error.failure}`);
    });
    
    // Capture JavaScript errors
    const jsErrors = [];
    page.on('pageerror', error => {
        const errorInfo = {
            message: error.message,
            stack: error.stack,
            timestamp: new Date().toISOString()
        };
        jsErrors.push(errorInfo);
        console.log(`💥 JS Error: ${error.message}`);
    });
    
    try {
        console.log('🌐 Navigating to http://127.0.0.1:5171...');
        await page.goto('http://127.0.0.1:5171', { 
            waitUntil: 'networkidle2',
            timeout: 30000 
        });
        
        // Wait a bit more for React to render
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        // Take screenshot
        console.log('📸 Taking screenshot...');
        await page.screenshot({ 
            path: '/Users/tom/Projects/mailai-console/frontend-screenshot.png',
            fullPage: true 
        });
        
        // Get page title and content
        const title = await page.title();
        const bodyText = await page.evaluate(() => document.body.innerText);
        const html = await page.content();
        
        console.log(`📋 Page Title: ${title}`);
        console.log(`📄 Body Text Length: ${bodyText.length} characters`);
        console.log(`🏷️ HTML Length: ${html.length} characters`);
        
        // Check if React app mounted
        const reactRoot = await page.$('#root');
        const reactRootContent = reactRoot ? await page.evaluate(el => el.innerHTML, reactRoot) : 'No #root element found';
        
        // Save diagnostic report
        const report = {
            timestamp: new Date().toISOString(),
            pageInfo: {
                title,
                bodyTextLength: bodyText.length,
                htmlLength: html.length,
                reactRootExists: !!reactRoot,
                reactRootContentLength: reactRootContent.length
            },
            consoleMessages,
            networkErrors,
            jsErrors,
            bodyText: bodyText.substring(0, 1000), // First 1000 chars
            reactRootContent: reactRootContent.substring(0, 2000) // First 2000 chars
        };
        
        fs.writeFileSync('/Users/tom/Projects/mailai-console/diagnostic-report.json', 
                        JSON.stringify(report, null, 2));
        
        console.log('✅ Diagnosis complete! Check:');
        console.log('   - frontend-screenshot.png for visual');
        console.log('   - diagnostic-report.json for details');
        
    } catch (error) {
        console.error('❌ Error during diagnosis:', error.message);
        
        // Take screenshot even on error
        try {
            await page.screenshot({ 
                path: '/Users/tom/Projects/mailai-console/error-screenshot.png',
                fullPage: true 
            });
        } catch (screenshotError) {
            console.error('Failed to take error screenshot:', screenshotError.message);
        }
        
        // Save error report
        const errorReport = {
            timestamp: new Date().toISOString(),
            error: {
                message: error.message,
                stack: error.stack
            },
            consoleMessages,
            networkErrors,
            jsErrors
        };
        
        fs.writeFileSync('/Users/tom/Projects/mailai-console/error-report.json', 
                        JSON.stringify(errorReport, null, 2));
    } finally {
        await browser.close();
    }
}

diagnoseFrontend().catch(console.error);