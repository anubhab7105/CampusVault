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

module.exports = router;