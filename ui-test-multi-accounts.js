const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function testMultiAccountUI() {
    // Create screenshots directory
    const screenshotsDir = './screenshots/multi-accounts';
    if (!fs.existsSync(screenshotsDir)) {
        fs.mkdirSync(screenshotsDir, { recursive: true });
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
        console.log('🧪 Testing Multi-Account MailAI Console UI...');

        // Set viewport for consistent screenshots
        await page.setViewport({ width: 1400, height: 900 });

        // Test 1: Homepage with new navigation
        console.log('📸 Testing updated homepage with accounts navigation...');
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        await page.screenshot({ path: `${screenshotsDir}/01-homepage-with-accounts-nav.png`, fullPage: true });

        // Check for accounts navigation link
        const accountsNav = await page.$('a[href="/accounts"]');
        const hasAccountsNav = accountsNav !== null;
        console.log(`   ✓ Accounts navigation found: ${hasAccountsNav}`);

        // Test 2: Accounts Management Page
        console.log('📸 Testing accounts management page...');
        if (hasAccountsNav) {
            await page.click('a[href="/accounts"]');
            await page.waitForNavigation({ waitUntil: 'networkidle0' });
            await page.screenshot({ path: `${screenshotsDir}/02-accounts-page.png`, fullPage: true });

            // Check for account elements
            const accountRows = await page.$$('tbody tr');
            console.log(`   ✓ Account rows found: ${accountRows.length}`);

            // Check for development notice
            const devNotice = await page.$('.border-orange-200');
            console.log(`   ✓ Development notice displayed: ${devNotice !== null}`);

            // Test Connect Account button
            const connectBtn = await page.$('button:has-text("Connect Account")');
            if (connectBtn) {
                console.log('📸 Testing connect account interaction...');
                await page.evaluate(() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const connectBtn = buttons.find(btn => btn.textContent.includes('Connect Account'));
                    if (connectBtn) connectBtn.click();
                });
                await new Promise(resolve => setTimeout(resolve, 1000));
                await page.screenshot({ path: `${screenshotsDir}/03-connect-account-clicked.png`, fullPage: true });
            }
        }

        // Test 3: Updated New Question Modal
        console.log('📸 Testing updated new question modal with account selection...');
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        
        await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const newQuestionBtn = buttons.find(btn => btn.textContent.includes('New Question'));
            if (newQuestionBtn) newQuestionBtn.click();
        });
        
        await page.waitForSelector('.fixed.inset-0.z-50', { timeout: 5000 });
        await page.screenshot({ path: `${screenshotsDir}/04-new-question-modal-with-accounts.png` });

        // Check for account selection section
        const accountSelection = await page.$('label:has-text("Gmail Accounts")');
        const hasAccountSelection = accountSelection !== null;
        console.log(`   ✓ Account selection section found: ${hasAccountSelection}`);

        // Count account checkboxes
        const accountCheckboxes = await page.$$('input[type="checkbox"]');
        console.log(`   ✓ Account checkboxes found: ${accountCheckboxes.length}`);

        // Test selecting accounts
        console.log('📸 Testing account selection...');
        if (accountCheckboxes.length > 0) {
            // Select first two accounts
            await accountCheckboxes[0].click();
            await accountCheckboxes[1].click();
            await page.screenshot({ path: `${screenshotsDir}/05-accounts-selected.png` });
        }

        // Fill in question
        const questionTextarea = await page.$('textarea[placeholder*="attorney question"]');
        if (questionTextarea) {
            await questionTextarea.type('Show me CoolSculpting Elite return responses across all connected accounts');
            await page.screenshot({ path: `${screenshotsDir}/06-question-with-accounts-filled.png` });
        }

        // Test form validation (should be enabled now)
        const submitBtn = await page.$('button[type="submit"]');
        if (submitBtn) {
            const isEnabled = await page.evaluate(btn => !btn.disabled, submitBtn);
            console.log(`   ✓ Submit button enabled after account selection: ${isEnabled}`);
        }

        // Test 4: Mobile responsiveness of new UI
        console.log('📸 Testing mobile responsiveness of multi-account UI...');
        await page.setViewport({ width: 375, height: 812 }); // iPhone X
        await page.goto('http://127.0.0.1:5171/accounts', { waitUntil: 'networkidle0' });
        await page.screenshot({ path: `${screenshotsDir}/07-accounts-mobile.png`, fullPage: true });

        // Test 5: Tablet view
        await page.setViewport({ width: 768, height: 1024 }); // iPad
        await page.screenshot({ path: `${screenshotsDir}/08-accounts-tablet.png`, fullPage: true });

        // Test 6: Desktop view with modal
        await page.setViewport({ width: 1400, height: 900 });
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        
        await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const newQuestionBtn = buttons.find(btn => btn.textContent.includes('New Question'));
            if (newQuestionBtn) newQuestionBtn.click();
        });
        
        await page.waitForSelector('.fixed.inset-0.z-50', { timeout: 5000 });
        await page.screenshot({ path: `${screenshotsDir}/09-final-modal-desktop.png` });

        console.log('✅ Multi-account UI testing completed successfully!');
        console.log(`📁 Screenshots saved to: ${path.resolve(screenshotsDir)}`);

        // Generate an HTML report for multi-account features
        const reportHtml = `
<!DOCTYPE html>
<html>
<head>
    <title>MailAI Console Multi-Account UI Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .screenshot { margin: 20px 0; text-align: center; }
        .screenshot img { max-width: 100%; border: 1px solid #ddd; }
        .screenshot h3 { margin: 10px 0; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .implemented { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .in-progress { background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; }
    </style>
</head>
<body>
    <h1>MailAI Console Multi-Account UI Test Report</h1>
    <p>Generated: ${new Date().toISOString()}</p>
    
    <div class="status implemented">
        <h3>✅ Implemented Features</h3>
        <ul>
            <li>Gmail Accounts management page with mock data</li>
            <li>Account navigation in header</li>
            <li>Account selection in New Question modal</li>
            <li>Form validation requiring account selection</li>
            <li>Professional UI design with development notices</li>
            <li>Responsive design (mobile/tablet/desktop)</li>
        </ul>
    </div>

    <div class="status in-progress">
        <h3>🚧 In Development (Highlighted in UI)</h3>
        <ul>
            <li>Google OAuth integration (mock buttons shown)</li>
            <li>Real account connection/disconnection</li>
            <li>Backend multi-account data models</li>
            <li>Message deduplication system</li>
            <li>Cross-account thread linking</li>
        </ul>
    </div>
    
    <div class="screenshot">
        <h3>1. Updated Homepage with Accounts Navigation</h3>
        <img src="01-homepage-with-accounts-nav.png" alt="Homepage with Accounts Nav">
    </div>
    
    <div class="screenshot">
        <h3>2. Gmail Accounts Management Page</h3>
        <img src="02-accounts-page.png" alt="Accounts Management">
    </div>
    
    <div class="screenshot">
        <h3>4. New Question Modal with Account Selection</h3>
        <img src="04-new-question-modal-with-accounts.png" alt="Modal with Account Selection">
    </div>
    
    <div class="screenshot">
        <h3>5. Accounts Selected State</h3>
        <img src="05-accounts-selected.png" alt="Accounts Selected">
    </div>
    
    <div class="screenshot">
        <h3>6. Complete Form with Question and Accounts</h3>
        <img src="06-question-with-accounts-filled.png" alt="Complete Form">
    </div>
    
    <div class="screenshot">
        <h3>7. Mobile View - Accounts Page</h3>
        <img src="07-accounts-mobile.png" alt="Mobile Accounts">
    </div>
    
    <div class="screenshot">
        <h3>8. Tablet View - Accounts Page</h3>
        <img src="08-accounts-tablet.png" alt="Tablet Accounts">
    </div>
</body>
</html>`;

        fs.writeFileSync(`${screenshotsDir}/multi-account-test-report.html`, reportHtml);
        console.log(`📄 HTML report saved: ${path.resolve(screenshotsDir)}/multi-account-test-report.html`);

    } catch (error) {
        console.error('❌ Error during testing:', error.message);
        await page.screenshot({ path: `${screenshotsDir}/error-screenshot.png` });
    } finally {
        await browser.close();
    }
}

// Run the test
testMultiAccountUI().catch(console.error);