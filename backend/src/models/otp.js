const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/db');

const OTP = sequelize.define('OTP', {
  id: { type: DataTypes.INTEGER.UNSIGNED, autoIncrement: true, primaryKey: true },
  phone: { type: DataTypes.STRING, allowNull: false },
  code: { type: DataTypes.STRING(6), allowNull: false },
  expiresAt: { type: DataTypes.DATE, allowNull: false },
  used: { type: DataTypes.BOOLEAN, defaultValue: false }
}, {
  indexes: [{ fields: ['phone'] }, { fields: ['expiresAt'] }]
});

module.exports = OTP;
