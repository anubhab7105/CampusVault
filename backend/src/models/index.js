const User = require('./user');
const OTP = require('./otp');
const Document = require('./document');
const Comment = require('./comment');
const ResetToken = require('./resetToken');
const AccessLog = require('./accessLog');
// Associations are defined in each model file for clarity

module.exports = { User, OTP, Document, Comment, ResetToken, AccessLog };
