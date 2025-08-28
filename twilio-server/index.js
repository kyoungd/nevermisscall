require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const twilio = require('twilio');
const { getCommonConfig, logger, successResponse, errorResponse } = require('../shared');

const app = express();
const config = getCommonConfig();
const port = process.env.PORT || 3701; // Use correct port from shared config

app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());

const twilioClient = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);

app.post('/webhooks/twilio/call', (req, res) => {
    const { CallStatus: callStatus, From: from, To: to, CallSid: callSid } = req.body;
    
    logger.info('Call webhook received', { callStatus, from, to, callSid });
    
    const twiml = new twilio.twiml.VoiceResponse();
    
    if (callStatus === 'ringing') {
        logger.info('Incoming call - forwarding to user phone', { callSid });
        
        twiml.dial({
            timeout: 20,
            action: `/webhooks/twilio/call/status/${callSid}`,
            method: 'POST'
        }, process.env.USER_PHONE_NUMBER);
    }
    
    res.type('text/xml');
    res.send(twiml.toString());
});

app.post('/webhooks/twilio/call/status/:callSid', async (req, res) => {
    const { callSid } = req.params;
    const { DialCallStatus: dialCallStatus, From: from } = req.body;
    
    logger.info('Dial status received', { callSid, dialCallStatus, from });
    
    if (dialCallStatus === 'no-answer' || dialCallStatus === 'busy' || dialCallStatus === 'failed') {
        logger.info('Call was missed - sending auto-response SMS', { callSid, dialCallStatus });
        
        try {
            const message = await twilioClient.messages.create({
                body: 'Thanks for calling! We missed your call but got your message. We\'ll get back to you shortly.',
                from: process.env.TWILIO_PHONE_NUMBER,
                to: from
            });
            
            logger.info('Auto-response SMS sent successfully', { 
                callSid, 
                messageSid: message.sid,
                to: from 
            });
        } catch (error) {
            logger.error('Error sending SMS', { callSid, error: error.message });
        }
    }
    
    const twiml = new twilio.twiml.VoiceResponse();
    res.type('text/xml');
    res.send(twiml.toString());
});

app.get('/health', (req, res) => {
    res.json(successResponse({ 
        status: 'healthy', 
        service: 'twilio-server',
        timestamp: new Date().toISOString() 
    }));
});

if (process.env.NODE_ENV !== 'test') {
    app.listen(port, () => {
        logger.info('NeverMissCall Twilio Server started', { 
            port, 
            webhookUrl: `http://localhost:${port}/webhooks/twilio/call` 
        });
    });
}

module.exports = app;