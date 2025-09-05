#!/usr/bin/env node

/**
 * Puppeteer UI test for MailAI Console Gmail accounts functionality
 * Tests the accounts page and message viewing functionality
 */

const puppeteer = require('puppeteer');

// Simple Puppeteer config (headless for CI, can be changed for debugging)
const getPuppeteerConfig = () => ({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security'],
    defaultViewport: { width: 1280, height: 800 }
});

const BASE_URL = 'http://127.0.0.1:5171';
const API_URL = 'http://127.0.0.1:5170';

async function testUI() {
    console.log('🔵 Starting MailAI Console UI test with Puppeteer...\n');
    
    const browser = await puppeteer.launch(getPuppeteerConfig());
    
    try {
        const page = await browser.newPage();
        
        // Enable console logging from the page
        page.on('console', (msg) => {
            const type = msg.type();
            if (type === 'error' || type === 'warn') {
                console.log(`🖥️ Browser ${type}: ${msg.text()}`);
            }
        });
        
        // Enable request/response logging for API calls
        await page.setRequestInterception(true);
        page.on('request', (req) => {
            if (req.url().includes('5170') || req.url().includes('/accounts') || req.url().includes('/auth')) {
                console.log(`🔵 API Request: ${req.method()} ${req.url()}`);
            }
            req.continue();
        });
        
        page.on('response', async (res) => {
            if (res.url().includes('5170')) {
                const status = res.status();
                const statusIcon = status === 200 ? '✅' : '❌';
                console.log(`${statusIcon} API Response: ${status} ${res.url()}`);
                
                if (status !== 200 && status !== 404) {
                    try {
                        const text = await res.text();
                        if (text && text.length < 500) {
                            console.log(`   Error details: ${text}`);
                        }
                    } catch (e) {
                        // Ignore response reading errors
                    }
                }
            }
        });
        
        // Test 1: Navigate to accounts page
        console.log('🖥️ Step 1: Navigating to accounts page...');
        await page.goto(`${BASE_URL}/accounts`, { waitUntil: 'networkidle0' });
        
        // Wait for page to load
        await page.waitForSelector('h1', { timeout: 10000 });
        
        // Take initial screenshot
        await page.screenshot({ 
            path: 'accounts-page-initial.png',
            fullPage: true 
        });
        
        // Check page title
        const pageTitle = await page.$eval('h1', el => el.textContent);
        console.log(`✅ Page loaded: "${pageTitle}"`);
        
        // Test 2: Check for account entries
        console.log('\\n📊 Step 2: Checking account entries in UI...');
        
        try {
            await page.waitForSelector('table', { timeout: 5000 });
            
            const accountsData = await page.evaluate(() => {
                const rows = document.querySelectorAll('tbody tr');
                return Array.from(rows).map(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 4) {
                        return {
                            email: cells[0]?.textContent?.trim() || '',
                            status: cells[1]?.textContent?.trim() || '',
                            messages: cells[2]?.textContent?.trim() || '',
                            lastSync: cells[3]?.textContent?.trim() || ''
                        };
                    }
                    return null;
                }).filter(Boolean);
            });
            
            console.log(`Found ${accountsData.length} accounts in UI:`);
            accountsData.forEach((acc, i) => {
                console.log(`  ${i+1}. ${acc.email}: ${acc.status} | ${acc.messages} messages | Last sync: ${acc.lastSync}`);
            });
            
        } catch (error) {
            console.log(`⚠️ Could not parse account table: ${error.message}`);
        }
        
        // Test 3: Try to click "View Messages" button
        console.log('\\n📧 Step 3: Testing View Messages functionality...');
        
        try {
            // Look for the View Messages button
            const viewMessagesButton = await page.$('button[class*="btn"]');
            
            if (viewMessagesButton) {
                const buttonText = await page.evaluate(btn => btn.textContent, viewMessagesButton);
                
                if (buttonText.includes('View Messages')) {
                    console.log('🔵 Clicking View Messages button...');
                    await viewMessagesButton.click();
                    
                    // Wait for modal to appear
                    await page.waitForSelector('.fixed.inset-0', { timeout: 5000 });
                    console.log('✅ Messages modal opened');
                    
                    // Take screenshot of modal
                    await page.screenshot({ 
                        path: 'messages-modal-opened.png',
                        fullPage: true 
                    });
                    
                    // Look for Load Recent Messages button
                    const loadButton = await page.$('button[class*="btn-primary"]');
                    if (loadButton) {
                        const loadButtonText = await page.evaluate(btn => btn.textContent, loadButton);
                        
                        if (loadButtonText.includes('Load')) {
                            console.log('🔵 Clicking Load Recent Messages button...');
                            await loadButton.click();
                            
                            // Wait a bit for the loading state
                            await page.waitForTimeout(2000);
                            
                            // Take screenshot after clicking load
                            await page.screenshot({ 
                                path: 'messages-loading-state.png',
                                fullPage: true 
                            });
                            
                            // Wait for either success or error
                            await page.waitForTimeout(5000);
                            
                            // Take final screenshot
                            await page.screenshot({ 
                                path: 'messages-final-state.png',
                                fullPage: true 
                            });
                            
                            // Check for error or success states
                            const hasError = await page.$('.bg-red-50') !== null;
                            const hasMessages = await page.$('.space-y-4 > div') !== null;
                            const isLoading = await page.$('.animate-spin') !== null;
                            
                            if (hasError) {
                                const errorText = await page.$eval('.bg-red-50', el => el.textContent);
                                console.log(`❌ Error in UI: ${errorText.slice(0, 200)}`);
                            } else if (hasMessages) {
                                console.log('✅ Messages loaded successfully in UI!');
                            } else if (isLoading) {
                                console.log('⏳ Still loading messages...');
                            } else {
                                console.log('⚠️ Unknown state - no clear success/error indication');
                            }
                        }
                    }
                }
            } else {
                console.log('⚠️ View Messages button not found');
            }
            
        } catch (error) {
            console.log(`⚠️ Error testing View Messages: ${error.message}`);
        }
        
        // Test 4: Check Connect Account functionality
        console.log('\\n🔗 Step 4: Testing Connect Account modal...');
        
        try {
            // Look for Connect Account button
            const connectButtons = await page.$$('button');
            let connectButton = null;
            
            for (const btn of connectButtons) {
                const text = await page.evaluate(el => el.textContent, btn);
                if (text.includes('Connect Account') || text.includes('Connect First Account')) {
                    connectButton = btn;
                    break;
                }
            }
            
            if (connectButton) {
                console.log('🔵 Clicking Connect Account button...');
                await connectButton.click();
                
                // Wait for IMAP modal to appear
                await page.waitForSelector('.fixed.inset-0', { timeout: 5000 });
                console.log('✅ Connect IMAP modal opened');
                
                // Take screenshot of connect modal
                await page.screenshot({ 
                    path: 'connect-imap-modal.png',
                    fullPage: true 
                });
                
                // Check if the modal has the expected content
                const hasEmailInput = await page.$('input[type="email"]') !== null;
                const hasPasswordInput = await page.$('input[type="password"]') !== null;
                const hasInstructions = await page.$eval('div', el => 
                    el.textContent.includes('app password')
                );
                
                console.log(`   Email input: ${hasEmailInput ? '✅' : '❌'}`);
                console.log(`   Password input: ${hasPasswordInput ? '✅' : '❌'}`);
                console.log(`   Instructions visible: ${hasInstructions ? '✅' : '❌'}`);
                
                // Close modal by clicking X or outside
                const closeButton = await page.$('button[class*="text-gray-400"]');
                if (closeButton) {
                    await closeButton.click();
                    console.log('✅ Closed connect modal');
                }
                
            } else {
                console.log('⚠️ Connect Account button not found');
            }
            
        } catch (error) {
            console.log(`⚠️ Error testing Connect Account: ${error.message}`);
        }
        
        // Test 5: Check debug API status
        console.log('\\n🔍 Step 5: Final API status check...');
        
        const apiTests = [
            { name: 'Account Tokens', url: '/debug/account-tokens' },
            { name: 'Accounts List', url: '/accounts' },
        ];
        
        for (const test of apiTests) {
            try {
                const response = await fetch(`${API_URL}${test.url}`);
                const status = response.status;
                const statusIcon = status === 200 ? '✅' : '❌';
                console.log(`${statusIcon} ${test.name}: ${status}`);
                
                if (status === 200 && test.url === '/debug/account-tokens') {
                    const data = await response.json();
                    console.log(`   Found ${data.total} accounts with token formats:`);
                    data.accounts.forEach(acc => {
                        console.log(`     - ${acc.email}: ${acc.token_format}`);
                    });
                }
            } catch (error) {
                console.log(`❌ ${test.name}: Error - ${error.message}`);
            }
        }
        
    } catch (error) {
        console.error('❌ UI test failed:', error);
        
        // Take error screenshot
        try {
            const page = browser.pages()[0] || await browser.newPage();
            await page.screenshot({ 
                path: 'test-error-state.png',
                fullPage: true 
            });
        } catch (screenshotError) {
            console.log('Could not take error screenshot');
        }
        
        throw error;
    } finally {
        await browser.close();
    }
    
    console.log('\\n✅ Puppeteer UI test completed!');
    console.log('Screenshots saved:');
    console.log('  - accounts-page-initial.png');
    console.log('  - messages-modal-opened.png');
    console.log('  - messages-loading-state.png');
    console.log('  - messages-final-state.png');
    console.log('  - connect-imap-modal.png');
}

if (require.main === module) {
    testUI().catch(console.error);
}

module.exports = { testUI };