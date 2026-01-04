const express = require('express');
const User = require('../models/user');
const { authenticateJWT, requireRole } = require('../middleware/auth');

const router = express.Router();

// admin: list users
router.get('/', authenticateJWT, requireRole('admin'), async (req, res, next) => {
  try {
    const users = await User.findAll({ attributes: ['id','fullName','email','role','collegeId','verified'] });
    res.json({ ok: true, users });
  } catch (err) { next(err); }
});

// admin: delete user
router.delete('/:id', authenticateJWT, requireRole('admin'), async (req, res, next) => {
  try {
    const user = await User.findByPk(req.params.id);
    if (!user) return res.status(404).json({ error: 'Not found' });
    await user.destroy();
    res.json({ ok: true });
  } catch (err) { next(err); }
});

// admin: access logs
router.get('/access-logs/all', authenticateJWT, requireRole('admin'), async (req, res, next) => {
  try {
    const AccessLog = require('../models/accessLog');
    const logs = await AccessLog.findAll({ order: [['createdAt','DESC']], limit: 200 });
    res.json({ ok: true, logs });
  } catch (err) { next(err); }
});

module.exports = router;