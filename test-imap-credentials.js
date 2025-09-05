#!/usr/bin/env node

/**
 * Puppeteer test to fix IMAP credentials for all 3 Gmail accounts
 * This test will disconnect and reconnect all accounts with proper app passwords
 */

const puppeteer = require('puppeteer');
const { getGlobalPuppeteerConfig } = require('../GLOBAL_PUPPETEER_CONFIG.js');

// Account credentials - replace with actual app passwords
const ACCOUNTS = [
    {
        email: 'tom@cienegaspa.com',
        appPassword: 'your_app_password_here'
    },
    {
        email: 'tbwerz@gmail.com', 
        appPassword: 'your_app_password_here'
    },
    {
        email: 'rose@cienegaspa.com',
        appPassword: 'your_app_password_here'
    }
];

const BASE_URL = 'http://127.0.0.1:5171';
const API_URL = 'http://127.0.0.1:5170';

async function main() {
    console.log('🔵 Starting IMAP credentials test...');
    
    const browser = await puppeteer.launch(getGlobalPuppeteerConfig());
    
    try {
        const page = await browser.newPage();
        
        // Enable request interception to log API calls
        await page.setRequestInterception(true);
        page.on('request', (req) => {
            if (req.url().includes('/auth/') || req.url().includes('/debug/')) {
                console.log(`🔵 API Request: ${req.method()} ${req.url()}`);
                if (req.postData()) {
                    console.log(`🔵 Request body: ${req.postData()}`);
                }
            }
            req.continue();
        });
        
        page.on('response', async (res) => {
            if (res.url().includes('/auth/') || res.url().includes('/debug/')) {
                const status = res.status();
                console.log(`🔵 API Response: ${status} ${res.url()}`);
                if (status !== 200) {
                    try {
                        const text = await res.text();
                        console.log(`❌ Error response: ${text}`);
                    } catch (e) {
                        console.log(`❌ Could not read error response: ${e.message}`);
                    }
                }
            }
        });
        
        // Test 1: Check current token formats
        console.log('\\n📊 Step 1: Checking current token formats...');
        const tokensResponse = await fetch(`${API_URL}/debug/account-tokens`);
        const tokensData = await tokensResponse.json();
        console.log('Current account tokens:');
        tokensData.accounts.forEach(acc => {
            console.log(`  - ${acc.email}: ${acc.token_format} (${acc.token_preview})`);
        });
        
        // Test 2: Try fetching messages with old tokens (should fail)
        console.log('\\n📥 Step 2: Testing message fetch with old credentials...');
        try {
            const messagesResponse = await fetch(`${API_URL}/accounts/recent-messages?days=1&limit_per_account=5`);
            if (messagesResponse.ok) {
                const messagesData = await messagesResponse.json();
                console.log(`✅ Unexpectedly succeeded: Found ${messagesData.total_messages} messages`);
            } else {
                const errorText = await messagesResponse.text();
                console.log(`❌ Expected failure: ${messagesResponse.status} - ${errorText.slice(0, 200)}`);
            }
        } catch (error) {
            console.log(`❌ Expected error: ${error.message}`);
        }
        
        // Test 3: Update credentials using migration endpoint
        console.log('\\n🔧 Step 3: Updating credentials via API...');
        for (const account of ACCOUNTS) {
            if (account.appPassword === 'your_app_password_here') {
                console.log(`⚠️ Skipping ${account.email} - no app password provided`);
                continue;
            }
            
            console.log(`🔵 Updating credentials for ${account.email}...`);
            try {
                const updateResponse = await fetch(`${API_URL}/debug/update-account-credentials?email=${encodeURIComponent(account.email)}&app_password=${encodeURIComponent(account.appPassword)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const updateData = await updateResponse.json();
                if (updateData.success) {
                    console.log(`✅ ${updateData.message}`);
                    console.log(`   Old: ${updateData.old_format}`);
                    console.log(`   New: ${updateData.new_format}`);
                } else {
                    console.log(`❌ Failed to update ${account.email}: ${updateData.error}`);
                }
            } catch (error) {
                console.log(`❌ Error updating ${account.email}: ${error.message}`);
            }
        }
        
        // Test 4: Verify token formats updated
        console.log('\\n📊 Step 4: Verifying updated token formats...');
        const updatedTokensResponse = await fetch(`${API_URL}/debug/account-tokens`);
        const updatedTokensData = await updatedTokensResponse.json();
        console.log('Updated account tokens:');
        updatedTokensData.accounts.forEach(acc => {
            console.log(`  - ${acc.email}: ${acc.token_format} (${acc.token_preview})`);
        });
        
        // Test 5: Try fetching messages with new tokens
        console.log('\\n📥 Step 5: Testing message fetch with updated credentials...');
        try {
            const newMessagesResponse = await fetch(`${API_URL}/accounts/recent-messages?days=1&limit_per_account=5`);
            if (newMessagesResponse.ok) {
                const newMessagesData = await newMessagesResponse.json();
                console.log(`✅ Success! Found ${newMessagesData.total_messages} messages from ${newMessagesData.total_accounts} accounts`);
                
                // Show sample messages
                if (newMessagesData.messages && newMessagesData.messages.length > 0) {
                    console.log('\\n📧 Sample messages:');
                    newMessagesData.messages.slice(0, 3).forEach((msg, i) => {
                        console.log(`  ${i+1}. From: ${msg.from_email}`);
                        console.log(`     Subject: ${msg.subject}`);
                        console.log(`     Account: ${msg.account_email}`);
                        console.log(`     Date: ${msg.date}`);
                        if (msg.snippet) {
                            console.log(`     Snippet: ${msg.snippet.slice(0, 100)}...`);
                        }
                        console.log('');
                    });
                }
            } else {
                const errorText = await newMessagesResponse.text();
                console.log(`❌ Still failing: ${newMessagesResponse.status} - ${errorText.slice(0, 200)}`);
            }
        } catch (error) {
            console.log(`❌ Error: ${error.message}`);
        }
        
        // Test 6: Navigate to UI and verify accounts page
        console.log('\\n🖥️ Step 6: Testing UI...');
        await page.goto(`${BASE_URL}/accounts`);
        await page.waitForSelector('.card', { timeout: 5000 });
        
        // Take screenshot
        await page.screenshot({ 
            path: 'imap-credentials-test.png',
            fullPage: true 
        });
        
        // Check for account entries in the table
        const accountRows = await page.$$eval('tbody tr', rows => {
            return rows.map(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length >= 2) {
                    const email = cells[0]?.textContent?.trim() || '';
                    const status = cells[1]?.textContent?.trim() || '';
                    return { email, status };
                }
                return null;
            }).filter(Boolean);
        });
        
        console.log('UI Account Status:');
        accountRows.forEach(acc => {
            console.log(`  - ${acc.email}: ${acc.status}`);
        });
        
        // Try clicking "View Messages" button
        console.log('\\n📧 Step 7: Testing View Messages functionality...');
        try {
            const viewMessagesBtn = await page.$('button:has-text("View Messages")') || 
                                  await page.$('button[class*="btn"]:has-text("View Messages")') ||
                                  await page.$$eval('button', btns => 
                                    btns.find(btn => btn.textContent.includes('View Messages'))
                                  );
            
            if (viewMessagesBtn) {
                await page.click('button:has-text("View Messages")');
                await page.waitForSelector('.fixed.inset-0', { timeout: 3000 }); // Modal should appear
                
                await page.screenshot({ 
                    path: 'messages-modal-test.png',
                    fullPage: true 
                });
                
                // Click Load Recent Messages
                const loadBtn = await page.$('button:has-text("Load Recent Messages")');
                if (loadBtn) {
                    console.log('🔵 Clicking Load Recent Messages...');
                    await page.click('button:has-text("Load Recent Messages")');
                    
                    // Wait for either loading state or results
                    await page.waitForTimeout(3000);
                    
                    await page.screenshot({ 
                        path: 'messages-loaded-test.png',
                        fullPage: true 
                    });
                    
                    // Check if messages loaded
                    const messagesExist = await page.$('.space-y-4 > div') !== null;
                    const errorExists = await page.$('.bg-red-50') !== null;
                    
                    if (messagesExist) {
                        console.log('✅ Messages loaded successfully in UI!');
                    } else if (errorExists) {
                        const errorText = await page.$eval('.bg-red-50', el => el.textContent);
                        console.log(`❌ UI Error: ${errorText}`);
                    } else {
                        console.log('⚠️ No messages found or still loading...');
                    }
                }
            } else {
                console.log('⚠️ View Messages button not found');
            }
        } catch (error) {
            console.log(`⚠️ UI testing error: ${error.message}`);
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
        throw error;
    } finally {
        await browser.close();
    }
    
    console.log('\\n✅ IMAP credentials test completed!');
    console.log('Screenshots saved: imap-credentials-test.png, messages-modal-test.png, messages-loaded-test.png');
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = { main };