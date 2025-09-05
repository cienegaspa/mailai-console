#!/usr/bin/env node

/**
 * Simple script to update Gmail account credentials to the new format
 * This fixes the "old token format - needs reconnection" issue
 * 
 * Usage: node fix-account-credentials.js
 * Then follow the prompts to enter your app passwords
 */

const readline = require('readline');

const API_URL = 'http://127.0.0.1:5170';

// The accounts that need updating (from our debug test)
const ACCOUNTS = [
    'tom@cienegaspa.com',
    'tbwerz@gmail.com', 
    'rose@cienegaspa.com'
];

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

function askQuestion(question) {
    return new Promise((resolve) => {
        rl.question(question, resolve);
    });
}

function askPassword(question) {
    return new Promise((resolve) => {
        const stdin = process.stdin;
        const stdout = process.stdout;
        
        stdout.write(question);
        
        stdin.resume();
        stdin.setEncoding('utf8');
        stdin.setRawMode(true);
        
        let password = '';
        
        const onData = (char) => {
            switch (char) {
                case '\n':
                case '\r':
                case '\u0004': // Ctrl+D
                    stdin.setRawMode(false);
                    stdin.removeListener('data', onData);
                    stdout.write('\n');
                    resolve(password);
                    break;
                case '\u0003': // Ctrl+C
                    process.exit();
                    break;
                case '\u007f': // Backspace
                    if (password.length > 0) {
                        password = password.slice(0, -1);
                        stdout.write('\b \b');
                    }
                    break;
                default:
                    password += char;
                    stdout.write('*');
            }
        };
        
        stdin.on('data', onData);
    });
}

async function updateAccountCredentials(email, appPassword) {
    try {
        const response = await fetch(`${API_URL}/debug/update-account-credentials?email=${encodeURIComponent(email)}&app_password=${encodeURIComponent(appPassword)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

async function testMessagesAfterUpdate() {
    try {
        console.log('\n🧪 Testing message fetching after credential update...');
        const response = await fetch(`${API_URL}/accounts/recent-messages?days=1&limit_per_account=3`);
        
        if (response.ok) {
            const data = await response.json();
            console.log(`✅ Success! Fetched ${data.total_messages} messages from ${data.total_accounts} accounts`);
            
            if (data.messages && data.messages.length > 0) {
                console.log('\n📧 Sample messages:');
                data.messages.slice(0, 3).forEach((msg, i) => {
                    console.log(`  ${i+1}. From: ${msg.from_email}`);
                    console.log(`     Subject: ${msg.subject || '(No subject)'}`);
                    console.log(`     Account: ${msg.account_email}`);
                    console.log(`     Date: ${new Date(msg.date).toLocaleString()}`);
                    console.log('');
                });
                return true;
            }
        } else {
            const errorText = await response.text();
            console.log(`❌ Still failing: ${response.status} - ${errorText.slice(0, 200)}`);
            return false;
        }
    } catch (error) {
        console.log(`❌ Test error: ${error.message}`);
        return false;
    }
}

async function main() {
    console.log('🔧 MailAI Console - Fix Account Credentials');
    console.log('==========================================\n');
    
    console.log('This script will update your Gmail account credentials to the new format.');
    console.log('You will need your Gmail app passwords for each account.\n');
    
    console.log('📋 Accounts that need updating:');
    ACCOUNTS.forEach((email, i) => {
        console.log(`  ${i+1}. ${email}`);
    });
    console.log('');
    
    const proceed = await askQuestion('Do you want to proceed? (y/N): ');
    if (proceed.toLowerCase() !== 'y' && proceed.toLowerCase() !== 'yes') {
        console.log('Operation cancelled.');
        rl.close();
        return;
    }
    
    console.log('\n🔑 Please enter your Gmail app passwords for each account.');
    console.log('(App passwords are 16 characters, all lowercase, no spaces)\n');
    
    const credentials = {};
    
    for (const email of ACCOUNTS) {
        console.log(`\\n📧 Account: ${email}`);
        console.log('To get an app password:');
        console.log('1. Go to myaccount.google.com');
        console.log('2. Security → 2-Step Verification');
        console.log('3. App passwords → Mail');
        console.log('4. Copy the 16-character password (no spaces)\\n');
        
        const appPassword = await askPassword(`Enter app password for ${email}: `);
        
        if (appPassword.length < 10) {
            console.log('⚠️  App password seems too short. App passwords are usually 16 characters.');
            const confirm = await askQuestion('Continue anyway? (y/N): ');
            if (confirm.toLowerCase() !== 'y') {
                console.log('Skipping this account.');
                continue;
            }
        }
        
        credentials[email] = appPassword;
    }
    
    console.log(`\\n🔄 Updating ${Object.keys(credentials).length} account(s)...\\n`);
    
    let successCount = 0;
    
    for (const [email, appPassword] of Object.entries(credentials)) {
        console.log(`🔵 Updating ${email}...`);
        
        const result = await updateAccountCredentials(email, appPassword);
        
        if (result.success) {
            console.log(`✅ ${result.message}`);
            console.log(`   Updated: ${result.old_format} → ${result.new_format}`);
            successCount++;
        } else {
            console.log(`❌ Failed to update ${email}: ${result.error}`);
            
            if (result.error.includes('authentication')) {
                console.log('   💡 Check that your app password is correct and that 2FA is enabled');
            }
        }
        console.log('');
    }
    
    console.log(`\\n📊 Update Summary: ${successCount}/${Object.keys(credentials).length} accounts updated successfully\\n`);
    
    if (successCount > 0) {
        const testResult = await testMessagesAfterUpdate();
        
        if (testResult) {
            console.log('🎉 Success! Your accounts are now ready to load emails.');
            console.log('\\nNext steps:');
            console.log('1. Go to http://127.0.0.1:5171/accounts');
            console.log('2. Click "View Messages"');
            console.log('3. Click "Load Recent Messages"');
            console.log('4. Your messages should now load successfully!');
        } else {
            console.log('⚠️  Accounts updated but message testing failed.');
            console.log('Try refreshing the UI and testing manually.');
        }
    }
    
    rl.close();
}

main().catch(console.error);