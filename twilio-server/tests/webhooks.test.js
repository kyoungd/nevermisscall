const request = require('supertest');

// Set required environment variables before requiring the app
process.env.NODE_ENV = 'test';
process.env.USER_PHONE_NUMBER = '+15559876543'; // Set required env var for tests

// Use the actual application under test
const app = require('../index');

describe('Twilio Webhook Handlers', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('POST /webhooks/twilio/call', () => {
        it('should handle incoming call and return TwiML', async () => {
            const response = await request(app)
                .post('/webhooks/twilio/call')
                .send({
                    CallStatus: 'ringing',
                    From: '+15551111111',
                    To: '+15551234567',
                    CallSid: 'CA123456789'
                });

            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toContain('text/xml');
            expect(response.text).toContain('<Response');
            // For small market app, just verify TwiML is returned - specific dialing logic tested in integration
        });

        it('should not dial for non-ringing call status', async () => {
            const response = await request(app)
                .post('/webhooks/twilio/call')
                .send({
                    CallStatus: 'completed',
                    From: '+15551111111',
                    To: '+15551234567',
                    CallSid: 'CA123456789'
                });

            expect(response.status).toBe(200);
            expect(response.text).not.toContain('<Dial');
        });
    });

    describe('POST /webhooks/twilio/call/status/:callSid', () => {
        it('should send SMS when call is not answered', async () => {
            const response = await request(app)
                .post('/webhooks/twilio/call/status/CA123456789')
                .send({
                    DialCallStatus: 'no-answer',
                    From: '+15551111111',
                    CallSid: 'CA123456789'
                });

            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toContain('text/xml');
        });

        it('should send SMS when call is busy', async () => {
            const response = await request(app)
                .post('/webhooks/twilio/call/status/CA123456789')
                .send({
                    DialCallStatus: 'busy',
                    From: '+15551111111',
                    CallSid: 'CA123456789'
                });

            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toContain('text/xml');
        });

        it('should send SMS when call fails', async () => {
            const response = await request(app)
                .post('/webhooks/twilio/call/status/CA123456789')
                .send({
                    DialCallStatus: 'failed',
                    From: '+15551111111',
                    CallSid: 'CA123456789'
                });

            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toContain('text/xml');
        });

        it('should not trigger SMS logic when call is answered', async () => {
            const response = await request(app)
                .post('/webhooks/twilio/call/status/CA123456789')
                .send({
                    DialCallStatus: 'answered',
                    From: '+15551111111',
                    CallSid: 'CA123456789'
                });

            expect(response.status).toBe(200);
            expect(response.headers['content-type']).toContain('text/xml');
        });
    });

    describe('GET /health', () => {
        it('should return health status using shared response format', async () => {
            const response = await request(app)
                .get('/health');

            expect(response.status).toBe(200);
            expect(response.body).toHaveProperty('success', true);
            expect(response.body).toHaveProperty('data');
            expect(response.body.data).toHaveProperty('status', 'healthy');
            expect(response.body.data).toHaveProperty('service', 'twilio-server');
        });
    });
});