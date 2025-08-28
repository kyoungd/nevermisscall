process.env.TWILIO_ACCOUNT_SID = 'test_account_sid';
process.env.TWILIO_AUTH_TOKEN = 'test_auth_token';
process.env.TWILIO_PHONE_NUMBER = '+15551234567';
process.env.USER_PHONE_NUMBER = '+15559876543';
process.env.PORT = '3001';

const mockDial = jest.fn();
const mockToString = jest.fn(() => '<?xml version="1.0" encoding="UTF-8"?><Response></Response>');

jest.mock('twilio', () => {
  const mockMessages = {
    create: jest.fn(() => Promise.resolve({
      sid: 'mock_message_sid',
      status: 'queued'
    }))
  };

  const mockTwilio = jest.fn(() => ({
    messages: mockMessages
  }));

  mockTwilio.twiml = {
    VoiceResponse: jest.fn(() => ({
      dial: mockDial,
      toString: mockToString
    }))
  };

  return mockTwilio;
});

global.mockDial = mockDial;
global.mockToString = mockToString;

global.mockTwilio = require('twilio');