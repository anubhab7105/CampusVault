const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/db');
const User = require('./user');

const Document = sequelize.define('Document', {
  id: { type: DataTypes.INTEGER.UNSIGNED, autoIncrement: true, primaryKey: true },
  title: { type: DataTypes.STRING, allowNull: false },
  description: { type: DataTypes.TEXT },
  fileUrl: { type: DataTypes.STRING, allowNull: false },
  filePublicId: { type: DataTypes.STRING },
  fileType: { type: DataTypes.STRING },
  isPublic: { type: DataTypes.BOOLEAN, defaultValue: true },
}, {
  indexes: [{ fields: ['title'] }, { fields: ['isPublic'] }]
});

Document.belongsTo(User, { as: 'uploadedBy', foreignKey: 'uploadedById' });
User.hasMany(Document, { foreignKey: 'uploadedById' });

module.exports = Document;
