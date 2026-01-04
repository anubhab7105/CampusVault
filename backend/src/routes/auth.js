const express = require('express');
const { body, validationResult } = require('express-validator');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const router = express.Router();
const User = require('../models/user');
const OTP = require('../models/otp');

// Request OTP for signup (phone)
router.post('/request-otp', [body('phone').isMobilePhone()], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { phone } = req.body;
    // generate OTP & store with expiry (5 min)
    const code = Math.floor(100000 + Math.random() * 900000).toString();
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000);
    await OTP.create({ phone, code, expiresAt });
    // Send SMS via Twilio if configured
    try {
      if (process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN) {
        const client = require('twilio')(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);
        await client.messages.create({ body: `Your CampusVault OTP: ${code}`, from: process.env.TWILIO_PHONE_NUMBER, to: phone });
      }
    } catch (e) { console.warn('Failed to send SMS', e); }
    const resp = { ok: true, msg: 'OTP sent' };
    if (process.env.NODE_ENV === 'development') resp.code = code;
    return res.json(resp);
  } catch (err) { next(err); }
});

// Verify OTP and create user (step two in single-page flow)
router.post('/verify-otp', [body('phone').isMobilePhone(), body('code').isLength({ min: 6, max: 6 })], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { phone, code, fullName, collegeId, email, password } = req.body;
    const otp = await OTP.findOne({ where: { phone, code, used: false, expiresAt: { [require('sequelize').Op.gt]: new Date() } } });
    if (!otp) return res.status(400).json({ error: 'Invalid or expired OTP' });
    // create user
    let generatedPassword = null;
    let passwordHash;
    if (!password) {
      generatedPassword = Math.random().toString(36).slice(-10) + 'A1!';
      passwordHash = await bcrypt.hash(generatedPassword, 12);
    } else {
      passwordHash = await bcrypt.hash(password, 12);
    }
    const user = await User.create({ fullName, collegeId, email, phone, passwordHash, verified: true });
    otp.used = true; await otp.save();
    if (generatedPassword && process.env.SMTP_HOST) {
      const { sendMail } = require('../utils/email');
      try {
        await sendMail(email, 'Your CampusVault credentials', `<p>Your account has been created. Email: ${email}<br/>Password: <strong>${generatedPassword}</strong></p>`);
      } catch (e) { console.warn('Failed to send email', e); }
    }
    res.json({ ok: true, userId: user.id });
  } catch (err) { next(err); }
});

// Login
router.post('/login', [body('email').isEmail(), body('password').isLength({ min: 6 })], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { email, password } = req.body;
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(401).json({ error: 'Invalid credentials' });
    const ok = await bcrypt.compare(password, user.passwordHash);
    if (!ok) return res.status(401).json({ error: 'Invalid credentials' });
    const token = jwt.sign({ userId: user.id, role: user.role }, process.env.JWT_SECRET, { expiresIn: process.env.JWT_EXPIRES_IN || '7d' });
    res.json({ token });
  } catch (err) { next(err); }
});

// Request password reset
router.post('/request-password-reset', [body('email').isEmail()], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { email } = req.body;
    const user = await User.findOne({ where: { email } });
    if (!user) return res.status(200).json({ ok: true }); // don't reveal existence
    const ResetToken = require('../models/resetToken');
    const token = require('crypto').randomBytes(32).toString('hex');
    const expiresAt = new Date(Date.now() + 60 * 60 * 1000); // 1 hour
    await ResetToken.create({ userId: user.id, token, expiresAt });
    const { sendMail } = require('../utils/email');
    const resetUrl = `${process.env.BASE_URL}/reset-password?token=${token}`;
    await sendMail(user.email, 'CampusVault Password Reset', `<p>Reset your password: <a href="${resetUrl}">${resetUrl}</a></p>`);
    res.json({ ok: true });
  } catch (err) { next(err); }
});

// Reset password
router.post('/reset-password', [body('token').notEmpty(), body('newPassword').isLength({ min: 6 })], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { token, newPassword } = req.body;
    const ResetToken = require('../models/resetToken');
    const rt = await ResetToken.findOne({ where: { token, used: false, expiresAt: { [require('sequelize').Op.gt]: new Date() } } });
    if (!rt) return res.status(400).json({ error: 'Invalid or expired token' });
    const user = await User.findByPk(rt.userId);
    user.passwordHash = await bcrypt.hash(newPassword, 10);
    await user.save();
    rt.used = true; await rt.save();
    res.json({ ok: true });
  } catch (err) { next(err); }
});

module.exports = router;