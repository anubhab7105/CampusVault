const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/db');

const User = sequelize.define('User', {
  id: { type: DataTypes.INTEGER.UNSIGNED, autoIncrement: true, primaryKey: true },
  fullName: { type: DataTypes.STRING, allowNull: false },
  collegeId: { type: DataTypes.STRING, allowNull: false, unique: true },
  email: { type: DataTypes.STRING, allowNull: false, unique: true },
  phone: { type: DataTypes.STRING, allowNull: false },
  role: { type: DataTypes.ENUM('admin','faculty','student'), defaultValue: 'student' },
  passwordHash: { type: DataTypes.STRING, allowNull: false },
  verified: { type: DataTypes.BOOLEAN, defaultValue: false }
}, {
  indexes: [
    { fields: ['email'] },
    { fields: ['collegeId'] },
  ]
});

module.exports = User;
