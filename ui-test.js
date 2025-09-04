const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function testMailAIConsole() {
    // Create screenshots directory
    const screenshotsDir = './screenshots';
    if (!fs.existsSync(screenshotsDir)) {
        fs.mkdirSync(screenshotsDir);
    }

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--quiet'],
        dumpio: false
    });

    const page = await browser.newPage();
    
    // Suppress console logs for silent mode
    page.on('console', () => {});
    page.on('pageerror', () => {});

    try {
        console.log('🧪 Testing MailAI Console UI...');

        // Set viewport for consistent screenshots
        await page.setViewport({ width: 1400, height: 900 });

        // Test 1: Homepage/Runs List
        console.log('📸 Testing homepage/runs list...');
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        await page.screenshot({ path: `${screenshotsDir}/01-homepage.png`, fullPage: true });

        // Test if page loads properly
        const title = await page.title();
        console.log(`   ✓ Page title: ${title}`);

        // Check for main navigation elements
        const navElements = await page.$$eval('nav button, nav a', els => els.length);
        console.log(`   ✓ Navigation elements found: ${navElements}`);

        // Test 2: New Run Modal
        console.log('📸 Testing new run modal...');
        // Look for button with "New Question" text
        await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const newQuestionBtn = buttons.find(btn => btn.textContent.includes('New Question'));
            if (newQuestionBtn) newQuestionBtn.click();
        });
        await page.waitForSelector('.fixed.inset-0.z-50', { timeout: 5000 });
        await page.screenshot({ path: `${screenshotsDir}/02-new-run-modal.png` });

        // Test form elements in modal
        const formElements = await page.$$eval('input, textarea, select', els => els.length);
        console.log(`   ✓ Form elements in modal: ${formElements}`);

        // Fill out the form with test question
        const questionTextarea = await page.$('textarea[placeholder*="attorney question"]');
        if (questionTextarea) {
            await questionTextarea.type('Show me CoolSculpting Elite return responses');
        }
        await page.screenshot({ path: `${screenshotsDir}/03-new-run-form-filled.png` });

        // Test 3: Submit and Create Run
        console.log('📸 Testing run creation...');
        await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const submitBtn = buttons.find(btn => btn.textContent.includes('Create Run'));
            if (submitBtn) submitBtn.click();
        });
        
        // Wait for navigation to run detail page or progress
        try {
            await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 5000 });
        } catch (e) {
            // Navigation might not happen immediately, wait for URL change or modal to close
            await page.waitForFunction(() => !document.querySelector('.fixed.inset-0.z-50'), { timeout: 5000 });
            await new Promise(resolve => setTimeout(resolve, 2000)); // Give time for any redirect
        }
        await page.screenshot({ path: `${screenshotsDir}/04-run-detail-initial.png`, fullPage: true });

        // Test 4: Monitor Run Progress (if SSE is working)
        console.log('📸 Monitoring run progress...');
        
        // Wait a bit to see if progress updates
        await new Promise(resolve => setTimeout(resolve, 3000));
        await page.screenshot({ path: `${screenshotsDir}/05-run-progress.png`, fullPage: true });

        // Check for progress indicators
        const progressElements = await page.$$eval('.progress, [class*="progress"], [role="progressbar"]', els => els.length);
        console.log(`   ✓ Progress indicators found: ${progressElements}`);

        // Wait longer to see if run completes
        console.log('⏳ Waiting for run to complete (up to 30 seconds)...');
        let attempts = 0;
        const maxAttempts = 15;
        
        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Check if run is complete by looking for results or "DONE" status
            const isComplete = await page.evaluate(() => {
                return document.body.innerText.includes('DONE') || 
                       document.body.innerText.includes('Summary') ||
                       document.querySelector('.summary, [class*="summary"], [data-testid*="summary"]');
            });
            
            if (isComplete) {
                console.log('   ✓ Run completed!');
                break;
            }
            attempts++;
        }

        // Test 5: Results View
        console.log('📸 Testing results view...');
        await page.screenshot({ path: `${screenshotsDir}/06-run-results.png`, fullPage: true });

        // Check for result elements
        const resultElements = await page.$$eval('.summary, .thread, .citation, [class*="result"]', els => els.length);
        console.log(`   ✓ Result elements found: ${resultElements}`);

        // Test 6: Evidence Viewer (if available)
        const evidenceLinks = await page.$$('a[href*="evidence"]');
        if (evidenceLinks.length > 0) {
            console.log('📸 Testing evidence viewer...');
            await evidenceLinks[0].click();
            await new Promise(resolve => setTimeout(resolve, 1000));
            await page.screenshot({ path: `${screenshotsDir}/07-evidence-viewer.png`, fullPage: true });
        }

        // Test 7: Q&A Interface (if available)
        await page.goBack();
        const qaElements = await page.$$('input[placeholder*="question"], textarea[placeholder*="question"], [data-testid*="qa"]');
        if (qaElements.length > 0) {
            console.log('📸 Testing Q&A interface...');
            await qaElements[0].click();
            await page.type(qaElements[0], 'What was the root cause of the issue?');
            await page.screenshot({ path: `${screenshotsDir}/08-qa-interface.png`, fullPage: true });
        }

        // Test 8: Mobile Responsiveness
        console.log('📸 Testing mobile responsiveness...');
        await page.setViewport({ width: 375, height: 812 }); // iPhone X
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        await page.screenshot({ path: `${screenshotsDir}/09-mobile-homepage.png`, fullPage: true });

        // Test 9: Tablet View
        console.log('📸 Testing tablet view...');
        await page.setViewport({ width: 768, height: 1024 }); // iPad
        await page.screenshot({ path: `${screenshotsDir}/10-tablet-homepage.png`, fullPage: true });

        console.log('✅ UI testing completed successfully!');
        console.log(`📁 Screenshots saved to: ${path.resolve(screenshotsDir)}`);

        // Generate a simple HTML report
        const reportHtml = `
<!DOCTYPE html>
<html>
<head>
    <title>MailAI Console UI Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .screenshot { margin: 20px 0; text-align: center; }
        .screenshot img { max-width: 100%; border: 1px solid #ddd; }
        .screenshot h3 { margin: 10px 0; }
    </style>
</head>
<body>
    <h1>MailAI Console UI Test Report</h1>
    <p>Generated: ${new Date().toISOString()}</p>
    
    <div class="screenshot">
        <h3>1. Homepage/Runs List</h3>
        <img src="01-homepage.png" alt="Homepage">
    </div>
    
    <div class="screenshot">
        <h3>2. New Run Modal</h3>
        <img src="02-new-run-modal.png" alt="New Run Modal">
    </div>
    
    <div class="screenshot">
        <h3>3. Form Filled</h3>
        <img src="03-new-run-form-filled.png" alt="Form Filled">
    </div>
    
    <div class="screenshot">
        <h3>4. Run Detail Initial</h3>
        <img src="04-run-detail-initial.png" alt="Run Detail Initial">
    </div>
    
    <div class="screenshot">
        <h3>5. Run Progress</h3>
        <img src="05-run-progress.png" alt="Run Progress">
    </div>
    
    <div class="screenshot">
        <h3>6. Run Results</h3>
        <img src="06-run-results.png" alt="Run Results">
    </div>
    
    <div class="screenshot">
        <h3>9. Mobile View</h3>
        <img src="09-mobile-homepage.png" alt="Mobile Homepage">
    </div>
    
    <div class="screenshot">
        <h3>10. Tablet View</h3>
        <img src="10-tablet-homepage.png" alt="Tablet Homepage">
    </div>
</body>
</html>`;

        fs.writeFileSync(`${screenshotsDir}/test-report.html`, reportHtml);
        console.log(`📄 HTML report saved: ${path.resolve(screenshotsDir)}/test-report.html`);

    } catch (error) {
        console.error('❌ Error during testing:', error.message);
        await page.screenshot({ path: `${screenshotsDir}/error-screenshot.png` });
    } finally {
        await browser.close();
    }
}

// Run the test
testMailAIConsole().catch(console.error);