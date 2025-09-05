#!/usr/bin/env node

/**
 * Test UI message loading with comprehensive logging
 * This will help us see exactly where the process fails
 */

const puppeteer = require('puppeteer');

async function testUILogging() {
    console.log('🔵 Testing UI message loading with comprehensive logging...\n');
    
    const browser = await puppeteer.launch({
        headless: false, // Show browser to see what's happening
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        defaultViewport: { width: 1280, height: 800 }
    });
    
    try {
        const page = await browser.newPage();
        
        // Enable detailed console logging
        page.on('console', (msg) => {
            const text = msg.text();
            // Log all our custom messages but filter out noise
            if (text.includes('🚀') || text.includes('🔵') || text.includes('📊') || 
                text.includes('✅') || text.includes('❌') || text.includes('⚠️') ||
                text.includes('📞') || text.includes('🔄') || text.includes('📋') ||
                text.includes('🎬') || text.includes('🏁') || text.includes('💥')) {
                console.log(`🖥️ ${text}`);
            }
        });
        
        page.on('pageerror', (error) => {
            console.log(`💥 Page error: ${error.message}`);
        });
        
        page.on('requestfailed', (request) => {
            console.log(`📡 Request failed: ${request.url()} - ${request.failure()?.errorText}`);
        });
        
        console.log('📄 Navigating to accounts page...');
        await page.goto('http://127.0.0.1:5171/accounts', { 
            waitUntil: 'networkidle0',
            timeout: 15000 
        });
        
        // Wait for page to load
        await page.waitForSelector('h1', { timeout: 10000 });
        console.log('✅ Page loaded');
        
        // Find and click View Messages button
        console.log('🔍 Looking for View Messages button...');
        const viewButton = await page.evaluateHandle(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.find(btn => btn.textContent.includes('View Messages'));
        });
        
        if (!viewButton || !(await viewButton.asElement())) {
            throw new Error('View Messages button not found');
        }
        
        console.log('👆 Clicking View Messages button...');
        await viewButton.click();
        
        // Wait for modal
        console.log('⏳ Waiting for modal to open...');
        await page.waitForSelector('.fixed.inset-0', { timeout: 10000 });
        console.log('✅ Modal opened');
        
        // Take screenshot before loading
        await page.screenshot({ path: 'before-loading.png' });
        
        // Look for auto-load or find load button
        console.log('🔍 Checking if messages auto-load or if we need to click Load button...');
        
        // Wait a moment to see if auto-loading starts
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Check if already loading or if we need to click load
        const hasLoadButton = await page.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            return buttons.some(btn => btn.textContent.includes('Load Recent Messages'));
        });
        
        if (hasLoadButton) {
            console.log('👆 Clicking Load Recent Messages button...');
            const loadButton = await page.evaluateHandle(() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                return buttons.find(btn => btn.textContent.includes('Load Recent Messages'));
            });
            await loadButton.click();
        } else {
            console.log('🔄 Messages appear to be auto-loading...');
        }
        
        // Now wait for results or timeout (max 45 seconds)
        console.log('⏳ Waiting for messages to load with comprehensive logging (max 45 seconds)...');
        
        try {
            await page.waitForFunction(() => {
                // Check for completion states
                const hasMessages = document.querySelectorAll('.space-y-4 > div').length > 0;
                const hasError = document.querySelector('.bg-red-50') !== null;
                const hasPartialResults = document.querySelector('.bg-yellow-50, .bg-green-50') !== null;
                const isStillLoading = document.querySelector('.animate-spin') !== null;
                
                // Return true when we have any completion state
                return hasMessages || hasError || hasPartialResults || !isStillLoading;
            }, { timeout: 45000 });
            
            // Take final screenshot
            await page.screenshot({ path: 'after-loading.png' });
            
            // Analyze results
            const results = await page.evaluate(() => {
                const messageElements = document.querySelectorAll('.space-y-4 > div');
                const hasError = document.querySelector('.bg-red-50') !== null;
                const hasSuccess = document.querySelector('.bg-green-50') !== null;
                const hasPartial = document.querySelector('.bg-yellow-50') !== null;
                
                let errorText = '';
                if (hasError) {
                    const errorEl = document.querySelector('.bg-red-50');
                    errorText = errorEl ? errorEl.textContent : '';
                }
                
                let statusText = '';
                if (hasSuccess || hasPartial) {
                    const statusEl = document.querySelector('.bg-green-50, .bg-yellow-50');
                    statusText = statusEl ? statusEl.textContent : '';
                }
                
                return {
                    messageCount: messageElements.length,
                    hasError,
                    hasSuccess,
                    hasPartial,
                    errorText,
                    statusText
                };
            });
            
            console.log('\n📊 Final Results:');
            console.log(`   Messages displayed: ${results.messageCount}`);
            console.log(`   Has error: ${results.hasError}`);
            console.log(`   Has success: ${results.hasSuccess}`);
            console.log(`   Has partial: ${results.hasPartial}`);
            
            if (results.statusText) {
                console.log(`   Status: ${results.statusText.substring(0, 100)}...`);
            }
            
            if (results.hasError) {
                console.log(`   Error: ${results.errorText.substring(0, 200)}...`);
            }
            
            if (results.messageCount > 0) {
                // Get first few message details
                const messageDetails = await page.evaluate(() => {
                    const messageElements = document.querySelectorAll('.space-y-4 > div');
                    const messages = [];
                    
                    for (let i = 0; i < Math.min(3, messageElements.length); i++) {
                        const element = messageElements[i];
                        const subject = element.querySelector('h4')?.textContent || '';
                        const fromText = element.querySelector('p')?.textContent || '';
                        const account = element.querySelector('[class*="px-2 py-0.5"]')?.textContent || '';
                        
                        messages.push({ subject, fromText, account });
                    }
                    
                    return messages;
                });
                
                console.log(`📧 First messages:`);
                messageDetails.forEach((msg, i) => {
                    console.log(`   ${i + 1}. "${msg.subject}" (${msg.account})`);
                    console.log(`      ${msg.fromText}`);
                });
                
                return true;
            } else if (results.hasSuccess || results.hasPartial) {
                console.log('📧 Loading completed but no messages displayed');
                return false;
            } else {
                console.log('❌ Unknown completion state');
                return false;
            }
            
        } catch (timeoutError) {
            console.log('\n⏱️ Timeout after 45 seconds');
            await page.screenshot({ path: 'timeout-state.png' });
            
            // Check what state we're in
            const finalState = await page.evaluate(() => {
                const isLoading = document.querySelector('.animate-spin') !== null;
                const hasError = document.querySelector('.bg-red-50') !== null;
                const loadingText = document.querySelector('.animate-spin')?.closest('.text-center')?.textContent || '';
                
                return { isLoading, hasError, loadingText };
            });
            
            console.log(`📊 Timeout state:`);
            console.log(`   Still loading: ${finalState.isLoading}`);
            console.log(`   Has error: ${finalState.hasError}`);
            if (finalState.loadingText) {
                console.log(`   Loading text: ${finalState.loadingText}`);
            }
            
            return false;
        }
        
    } catch (error) {
        console.error('\n💥 Test failed:', error.message);
        
        try {
            await page.screenshot({ path: 'test-error.png' });
            console.log('📸 Error screenshot saved as test-error.png');
        } catch (screenshotError) {
            console.log('Could not take error screenshot');
        }
        
        return false;
    } finally {
        await browser.close();
    }
}

// Run the test
if (require.main === module) {
    testUILogging()
        .then(success => {
            console.log('\n' + '='.repeat(50));
            if (success) {
                console.log('🎉 UI Message Loading Test PASSED!');
                console.log('📸 Screenshots saved:');
                console.log('   - before-loading.png');
                console.log('   - after-loading.png');
            } else {
                console.log('💥 UI Message Loading Test FAILED!');
                console.log('📸 Check screenshots for visual debugging:');
                console.log('   - before-loading.png');
                console.log('   - after-loading.png (if available)');
                console.log('   - timeout-state.png (if timeout occurred)');
            }
            
            console.log('\n📋 Check browser console logs above for detailed debugging info');
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('\n💥 Test crashed:', error);
            process.exit(1);
        });
}

module.exports = { testUILogging };