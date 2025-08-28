import { config } from 'dotenv';

// Load test environment variables
config({ path: '.env.test' });

// Global test setup
beforeAll(async () => {
  // Setup test database connection
  // Setup test Redis connection
  // Setup test external service mocks
});

afterAll(async () => {
  // Cleanup test resources
  // Close database connections
  // Close Redis connections
});

// Global test utilities
declare global {
  var testUtils: {
    // Add shared test utilities here
  };
}

globalThis.testUtils = {
  // Add shared test utilities here
};