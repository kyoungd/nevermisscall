const request = require('supertest');

describe('Integration Tests', () => {
    let app;

    beforeAll(() => {
        process.env.NODE_ENV = 'test';
        app = require('../index');
    });

    describe('Health Check', () => {
        it('should return health status', async () => {
            const response = await request(app)
                .get('/health');

            expect(response.status).toBe(200);
            expect(response.body).toHaveProperty('success', true);
            expect(response.body).toHaveProperty('data');
            expect(response.body.data).toHaveProperty('status', 'healthy');
            expect(response.body.data).toHaveProperty('service', 'twilio-server');
            expect(response.body.data).toHaveProperty('timestamp');
        });
    });

    describe('Complete Call Flow', () => {
        it('should handle incoming call and process missed call status', async () => {
            const callSid = 'CA' + Math.random().toString(36).substr(2, 9);
            const callerNumber = '+15551111111';

            const callResponse = await request(app)
                .post('/webhooks/twilio/call')
                .send({
                    CallStatus: 'ringing',
                    From: callerNumber,
                    To: process.env.TWILIO_PHONE_NUMBER,
                    CallSid: callSid
                });

            expect(callResponse.status).toBe(200);
            expect(callResponse.headers['content-type']).toContain('text/xml');

            const statusResponse = await request(app)
                .post(`/webhooks/twilio/call/status/${callSid}`)
                .send({
                    DialCallStatus: 'no-answer',
                    From: callerNumber,
                    CallSid: callSid
                });

            expect(statusResponse.status).toBe(200);
            expect(statusResponse.headers['content-type']).toContain('text/xml');
        });
    });
});