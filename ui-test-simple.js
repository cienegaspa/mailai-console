const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function simpleUITest() {
    const screenshotsDir = './screenshots/simple-test';
    if (!fs.existsSync(screenshotsDir)) {
        fs.mkdirSync(screenshotsDir, { recursive: true });
    }

    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--quiet'],
        dumpio: false
    });

    const page = await browser.newPage();
    page.on('console', () => {});
    page.on('pageerror', () => {});

    try {
        console.log('🧪 Simple UI Test...');
        await page.setViewport({ width: 1400, height: 900 });

        // Test 1: Homepage
        console.log('📸 Homepage...');
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        await page.screenshot({ path: `${screenshotsDir}/homepage.png`, fullPage: true });

        // Check navigation
        const accountsNavExists = await page.$('a[href="/accounts"]') !== null;
        console.log(`   ✓ Accounts nav exists: ${accountsNavExists}`);

        // Test 2: Try clicking accounts
        if (accountsNavExists) {
            console.log('📸 Attempting to navigate to accounts...');
            await page.click('a[href="/accounts"]');
            await new Promise(resolve => setTimeout(resolve, 3000)); // Wait 3 seconds
            await page.screenshot({ path: `${screenshotsDir}/accounts-attempt.png`, fullPage: true });
            
            // Check URL
            const currentUrl = page.url();
            console.log(`   Current URL: ${currentUrl}`);
        }

        // Test 3: New Question Modal
        console.log('📸 Testing modal...');
        await page.goto('http://127.0.0.1:5171', { waitUntil: 'networkidle0' });
        
        const newQuestionBtn = await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const btn = buttons.find(btn => btn.textContent.includes('New Question'));
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        });
        
        console.log(`   ✓ New Question button clicked: ${newQuestionBtn}`);
        
        if (newQuestionBtn) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            await page.screenshot({ path: `${screenshotsDir}/modal.png` });
        }

        console.log('✅ Simple test completed!');
        console.log(`📁 Screenshots saved to: ${path.resolve(screenshotsDir)}`);

    } catch (error) {
        console.error('❌ Error during testing:', error.message);
        await page.screenshot({ path: `${screenshotsDir}/error-screenshot.png` });
    } finally {
        await browser.close();
    }
}

simpleUITest().catch(console.error);