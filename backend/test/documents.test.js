const request = require('supertest');
const app = require('../src/app');

describe('Documents API (smoke)', () => {
  test('list documents', async () => {
    const res = await request(app).get('/api/documents');
    expect(res.status).toBe(401); // requires auth
  });
});