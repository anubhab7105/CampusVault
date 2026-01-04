const { DataTypes } = require('sequelize');
const { sequelize } = require('../config/db');
const User = require('./user');
const Document = require('./document');

const Comment = sequelize.define('Comment', {
  id: { type: DataTypes.INTEGER.UNSIGNED, autoIncrement: true, primaryKey: true },
  body: { type: DataTypes.TEXT, allowNull: false }
});

Comment.belongsTo(User, { as: 'author', foreignKey: 'authorId' });
Comment.belongsTo(Document, { foreignKey: 'documentId' });
User.hasMany(Comment, { foreignKey: 'authorId' });
Document.hasMany(Comment, { foreignKey: 'documentId' });

module.exports = Comment;
