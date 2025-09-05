#!/usr/bin/env node

/**
 * Test the debug endpoint directly to see what's happening
 */

const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

async function testDirectEndpoint() {
    console.log('🔵 Testing debug endpoint directly...');
    
    try {
        console.log('🔍 Fetching from tom@cienegaspa.com...');
        
        const response = await fetch('http://127.0.0.1:5170/debug/show-messages/tom%40cienegaspa.com', {
            timeout: 15000
        });
        
        console.log(`📊 Response status: ${response.status}`);
        console.log(`📊 Response headers:`, Object.fromEntries(response.headers));
        
        if (response.ok) {
            const text = await response.text();
            console.log(`📊 Response length: ${text.length} characters`);
            console.log(`📊 Response preview:`, text.substring(0, 200) + '...');
            
            try {
                const data = JSON.parse(text);
                console.log(`✅ JSON parsed successfully`);
                console.log(`📧 Success: ${data.success}`);
                console.log(`📧 Total found: ${data.total_found}`);
                console.log(`📧 Messages array length: ${data.messages?.length || 0}`);
                if (data.messages && data.messages[0]) {
                    console.log(`📧 First message subject:`, data.messages[0].subject);
                }
            } catch (jsonError) {
                console.error('❌ JSON parse error:', jsonError.message);
            }
        } else {
            console.error(`❌ HTTP error: ${response.status}`);
        }
        
    } catch (error) {
        console.error('❌ Request failed:', error.message);
    }
}

testDirectEndpoint();