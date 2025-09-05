#!/usr/bin/env node

/**
 * Automated IMAP query testing for Gmail date operators
 * Tests different date formats and operators to find what actually works
 */

const API_URL = 'http://127.0.0.1:5170';

async function testIMAPQueries() {
    console.log('🔍 Automated IMAP Query Testing - 3 Day Range');
    console.log('==============================================\n');
    
    // Test different date formats and operators
    const today = new Date();
    const threeDaysAgo = new Date(today);
    threeDaysAgo.setDate(today.getDate() - 3);
    
    // Format dates for different operators
    const todaySlash = today.toISOString().slice(0, 10).replace(/-/g, '/');
    const todayDash = today.toISOString().slice(0, 10);
    const threeDaysAgoSlash = threeDaysAgo.toISOString().slice(0, 10).replace(/-/g, '/');
    const threeDaysAgoDash = threeDaysAgo.toISOString().slice(0, 10);
    
    console.log(`📅 Date Range: ${threeDaysAgoSlash} to ${todaySlash}`);
    console.log(`Today: ${todaySlash} (slash format) / ${todayDash} (dash format)`);
    console.log(`3 days ago: ${threeDaysAgoSlash} (slash format) / ${threeDaysAgoDash} (dash format)\n`);
    
    // Test queries to try
    const testQueries = [
        // Gmail documentation recommended formats (with slashes)
        { name: 'after: with slashes', query: `after:${threeDaysAgoSlash}` },
        { name: 'after: before: with slashes', query: `after:${threeDaysAgoSlash} before:${todaySlash}` },
        
        // Common IMAP formats (with dashes) 
        { name: 'since: with dashes', query: `since:${threeDaysAgoDash}` },
        { name: 'after: with dashes', query: `after:${threeDaysAgoDash}` },
        
        // Relative date operators
        { name: 'newer_than: 3 days', query: 'newer_than:3d' },
        { name: 'newer_than: 72 hours', query: 'newer_than:72h' },
        
        // No date filter (get all recent messages)
        { name: 'ALL (no date filter)', query: 'ALL' },
        { name: 'Empty query', query: '' }
    ];
    
    console.log('🧪 Testing each query format against all 3 accounts...\n');
    
    for (const testCase of testQueries) {
        console.log(`\n🔵 Testing: "${testCase.name}" - Query: "${testCase.query}"`);
        console.log('─'.repeat(60));
        
        let totalFound = 0;
        
        // Test each account individually
        const accounts = ['tom@cienegaspa.com', 'tbwerz@gmail.com', 'rose@cienegaspa.com'];
        
        for (const email of accounts) {
            try {
                const response = await fetch(`${API_URL}/debug/test-imap`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: email,
                        app_password: 'from_database', // Special token to use stored credentials
                        query: testCase.query,
                        limit: 5
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        console.log(`  ✅ ${email}: ${data.messages_found} messages`);
                        totalFound += data.messages_found;
                        
                        // Show sample message details if found
                        if (data.messages && data.messages.length > 0) {
                            const msg = data.messages[0];
                            console.log(`     📧 Sample: "${msg.subject}" from ${msg.from_email} (${new Date(msg.date).toLocaleDateString()})`);
                        }
                    } else {
                        console.log(`  ❌ ${email}: ${data.error}`);
                    }
                } else {
                    const errorText = await response.text();
                    console.log(`  ❌ ${email}: HTTP ${response.status} - ${errorText.slice(0, 100)}`);
                }
            } catch (error) {
                console.log(`  ❌ ${email}: Network error - ${error.message}`);
            }
        }
        
        console.log(`📊 Total messages found with "${testCase.name}": ${totalFound}`);
        
        // If this query found messages, test it with the main endpoint
        if (totalFound > 0) {
            console.log(`\n🎯 This query worked! Testing with main /accounts/recent-messages endpoint...`);
            
            try {
                const response = await fetch(`${API_URL}/debug/test-all-accounts-query`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: testCase.query,
                        limit_per_account: 3
                    })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        console.log(`  ✅ Main endpoint: ${data.total_messages} messages from ${data.total_accounts} accounts`);
                        
                        // Show sample messages
                        if (data.messages && data.messages.length > 0) {
                            console.log('  📧 Sample messages:');
                            data.messages.slice(0, 2).forEach((msg, i) => {
                                console.log(`     ${i+1}. "${msg.subject}" from ${msg.from_email} (${msg.account_email}) - ${new Date(msg.date).toLocaleDateString()}`);
                            });
                        }
                    } else {
                        console.log(`  ❌ Main endpoint failed: ${data.error}`);
                    }
                } else {
                    console.log(`  ❌ Main endpoint HTTP error: ${response.status}`);
                }
            } catch (error) {
                console.log(`  ❌ Main endpoint network error: ${error.message}`);
            }
        }
    }
    
    console.log('\n🎉 Automated IMAP query testing completed!');
    console.log('\n📋 Summary:');
    console.log('- Tested multiple date formats: slashes (Gmail standard) vs dashes (IMAP)');
    console.log('- Tested different operators: after:, since:, newer_than:, ALL');
    console.log('- Tested both individual accounts and main endpoint');
    console.log('- The working format(s) will be used to fix the production endpoint');
}

testIMAPQueries().catch(console.error);