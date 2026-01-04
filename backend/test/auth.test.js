const request = require('supertest');
const app = require('../src/app');

describe('Auth routes (smoke)', () => {
  test('health check', async () => {
    const res = await request(app).get('/');
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
  });

  test('request-otp returns ok for valid phone', async () => {
    const res = await request(app).post('/api/auth/request-otp').send({ phone: '+1000000000' });
    expect(res.status).toBe(200);
    expect(res.body.ok).toBe(true);
  });
});