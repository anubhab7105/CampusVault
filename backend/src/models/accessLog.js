const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/db');

const AccessLog = sequelize.define('AccessLog', {
  id: { type: DataTypes.INTEGER.UNSIGNED, autoIncrement: true, primaryKey: true },
  userId: { type: DataTypes.INTEGER.UNSIGNED, allowNull: true },
  documentId: { type: DataTypes.INTEGER.UNSIGNED, allowNull: true },
  action: { type: DataTypes.STRING(100), allowNull: false },
  ip: { type: DataTypes.STRING(100) }
});

module.exports = AccessLog;