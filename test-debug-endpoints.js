#!/usr/bin/env node

/**
 * Simple test to demonstrate the IMAP credential format issue and solution
 */

const API_URL = 'http://127.0.0.1:5170';

async function testDebugEndpoints() {
    console.log('🔵 Testing debug endpoints to demonstrate IMAP credential issue...\n');
    
    // Test 1: Check current token formats
    console.log('📊 Step 1: Checking current account token formats...');
    try {
        const tokensResponse = await fetch(`${API_URL}/debug/account-tokens`);
        const tokensData = await tokensResponse.json();
        
        console.log('Current account tokens:');
        tokensData.accounts.forEach(acc => {
            console.log(`  - ${acc.email}: ${acc.token_format} (${acc.token_preview})`);
        });
        console.log(`Total accounts: ${tokensData.total}\n`);
    } catch (error) {
        console.log(`❌ Error checking tokens: ${error.message}\n`);
    }
    
    // Test 2: Try fetching messages (should fail with old format)
    console.log('📥 Step 2: Testing message fetch with current credentials...');
    try {
        const messagesResponse = await fetch(`${API_URL}/accounts/recent-messages?days=1&limit_per_account=5`);
        
        if (messagesResponse.ok) {
            const messagesData = await messagesResponse.json();
            console.log(`✅ Unexpectedly succeeded: Found ${messagesData.total_messages} messages from ${messagesData.total_accounts} accounts`);
        } else {
            const errorText = await messagesResponse.text();
            console.log(`❌ Expected failure with old token format:`);
            console.log(`   Status: ${messagesResponse.status}`);
            console.log(`   Error: ${errorText.slice(0, 300)}...`);
        }
    } catch (error) {
        console.log(`❌ Network error: ${error.message}`);
    }
    console.log('');
    
    // Test 3: Try IMAP test endpoint with dummy credentials (should fail gracefully)
    console.log('🔧 Step 3: Testing direct IMAP endpoint with dummy credentials...');
    try {
        const imapTestResponse = await fetch(`${API_URL}/debug/test-imap`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: 'test@example.com',
                app_password: 'dummy_password',
                query: 'from:no-reply',
                limit: 3
            })
        });
        
        const imapTestData = await imapTestResponse.json();
        
        if (imapTestData.success) {
            console.log(`✅ IMAP test succeeded: Found ${imapTestData.messages_found} messages`);
        } else {
            console.log(`❌ IMAP test failed (expected with dummy credentials):`);
            console.log(`   Error: ${imapTestData.error}`);
        }
    } catch (error) {
        console.log(`❌ IMAP test error: ${error.message}`);
    }
    console.log('');
    
    // Test 4: Show fetch-and-store endpoint
    console.log('📦 Step 4: Testing fetch-and-store endpoint (should show old token format issue)...');
    try {
        const fetchStoreResponse = await fetch(`${API_URL}/debug/fetch-and-store?days=1&limit_per_account=5`, {
            method: 'POST'
        });
        
        const fetchStoreData = await fetchStoreResponse.json();
        
        if (fetchStoreData.success) {
            console.log(`✅ Fetch and store completed:`);
            console.log(`   Total accounts processed: ${fetchStoreData.total_accounts_processed}`);
            console.log(`   Total messages fetched: ${fetchStoreData.total_messages_fetched}`);
            console.log('   Results by account:');
            fetchStoreData.results.forEach(result => {
                console.log(`     - ${result.email}: ${result.status} (${result.messages_fetched || 0} messages)`);
                if (result.error) {
                    console.log(`       Error: ${result.error}`);
                }
            });
        } else {
            console.log(`❌ Fetch and store failed:`);
            console.log(`   Error: ${fetchStoreData.error}`);
        }
    } catch (error) {
        console.log(`❌ Fetch and store error: ${error.message}`);
    }
    console.log('');
    
    // Summary
    console.log('📋 Summary:');
    console.log('The issue is that all accounts have old "imap_authenticated" token format.');
    console.log('The new system expects "imap:{app_password}" format.');
    console.log('');
    console.log('To fix this, you can:');
    console.log('1. Use the /debug/update-account-credentials endpoint with real app passwords');
    console.log('2. Or disconnect and reconnect accounts through the UI');
    console.log('3. The new ConnectIMAPModal will store credentials in the correct format');
    console.log('');
    console.log('✅ Debug test completed!');
}

testDebugEndpoints().catch(console.error);