const AccessLog = require('../models/accessLog');

async function logAction(req, action, extras = {}) {
  try {
    await AccessLog.create({ userId: req.user ? req.user.userId : null, documentId: extras.documentId || null, action, ip: req.ip });
  } catch (e) { console.warn('AccessLog error', e); }
}

module.exports = { logAction };