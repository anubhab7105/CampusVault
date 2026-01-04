const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const authRoutes = require('./routes/auth');
const docsRoutes = require('./routes/documents');
const commentsRoutes = require('./routes/comments');
const usersRoutes = require('./routes/users');

const app = express();

app.use(helmet());
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'", "'unsafe-inline'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
    imgSrc: ["'self'", 'data:', 'https:'],
    connectSrc: ["'self'", 'https:']
  }
}));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(cors({ origin: process.env.CORS_ORIGIN || true }));
app.use(morgan('dev'));

const limiter = rateLimit({ windowMs: 60 * 1000, max: 120 });
app.use(limiter);

app.use('/api/auth', authRoutes);
app.use('/api/users', usersRoutes);
app.use('/api/documents', docsRoutes);
app.use('/api/comments', commentsRoutes);

// Serve OpenAPI json
const path = require('path');
app.get('/api/docs/openapi.json', (req, res) => res.sendFile(path.join(__dirname, '../../docs/openapi.json')));

app.get('/', (req, res) => res.json({ ok: true, msg: 'CampusVault API' }));

// 404 handler
app.use((req, res, next) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status || 500).json({ error: err.message || 'Internal Server Error' });
});

module.exports = app;