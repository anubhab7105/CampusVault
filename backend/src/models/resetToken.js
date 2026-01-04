const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/db');

const ResetToken = sequelize.define('ResetToken', {
  id: { type: DataTypes.INTEGER.UNSIGNED, autoIncrement: true, primaryKey: true },
  userId: { type: DataTypes.INTEGER.UNSIGNED, allowNull: false },
  token: { type: DataTypes.STRING, allowNull: false },
  expiresAt: { type: DataTypes.DATE, allowNull: false },
  used: { type: DataTypes.BOOLEAN, defaultValue: false }
});

module.exports = ResetToken;