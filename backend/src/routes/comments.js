const express = require('express');
const { body, validationResult } = require('express-validator');
const Comment = require('../models/comment');
const Document = require('../models/document');
const { authenticateJWT, requireRole } = require('../middleware/auth');

const router = express.Router();

// post comment (students & faculty)
router.post('/:documentId', authenticateJWT, [body('body').notEmpty()], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    const { documentId } = req.params;
    const doc = await Document.findByPk(documentId);
    if (!doc) return res.status(404).json({ error: 'Document not found' });
    const comment = await Comment.create({ body: req.body.body, authorId: req.user.userId, documentId });
    res.json({ ok: true, comment });
  } catch (err) { next(err); }
});

// get comments for a document
router.get('/:documentId', async (req, res, next) => {
  try {
    const { documentId } = req.params;
    const comments = await Comment.findAll({ where: { documentId }, include: ['author'] });
    res.json({ ok: true, comments });
  } catch (err) { next(err); }
});

// delete comment (admin or author)
router.delete('/:id', authenticateJWT, async (req, res, next) => {
  try {
    const { id } = req.params;
    const comment = await Comment.findByPk(id);
    if (!comment) return res.status(404).json({ error: 'Not found' });
    if (req.user.role !== 'admin' && comment.authorId !== req.user.userId) return res.status(403).json({ error: 'Forbidden' });
    await comment.destroy();
    res.json({ ok: true });
  } catch (err) { next(err); }
});

module.exports = router;