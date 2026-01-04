const express = require('express');
const multer = require('multer');
const { body, validationResult } = require('express-validator');
const { v2: cloudinary } = require('cloudinary');
const streamifier = require('streamifier');

const Document = require('../models/document');
const { authenticateJWT, requireRole } = require('../middleware/auth');

const router = express.Router();

// simple memory upload
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 50 * 1024 * 1024 } });

// Cloudinary config
cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_KEY,
  api_secret: process.env.CLOUDINARY_SECRET
});

// Faculty uploads a document
const ALLOWED_MIMES = ['application/pdf', 'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
router.post('/', authenticateJWT, requireRole('faculty'), upload.single('file'), [body('title').notEmpty()], async (req, res, next) => {
  try {
    const errors = validationResult(req); if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });
    if (!req.file) return res.status(400).json({ error: 'File required' });
    if (!ALLOWED_MIMES.includes(req.file.mimetype)) return res.status(400).json({ error: 'Unsupported file type' });
    const { title, description, isPublic } = req.body;
    // stream to cloudinary
    const stream = cloudinary.uploader.upload_stream({ resource_type: 'auto', folder: 'campusvault' }, async (err, result) => {
      if (err) return next(err);
      const doc = await Document.create({ title, description, fileUrl: result.secure_url, filePublicId: result.public_id, fileType: req.file.mimetype, isPublic: isPublic !== 'false', uploadedById: req.user.userId });
      res.json({ ok: true, document: doc });
    });
    streamifier.createReadStream(req.file.buffer).pipe(stream);
  } catch (err) { next(err); }
});

// List documents (public only for students)
router.get('/', authenticateJWT, async (req, res, next) => {
  try {
    const docs = await Document.findAll({ include: ['uploadedBy'] });
    // If the user is a student, filter non-public
    if (req.user && req.user.role === 'student') {
      return res.json({ ok: true, docs: docs.filter(d => d.isPublic) });
    }
    res.json({ ok: true, docs });
  } catch (err) { next(err); }
});

// Return viewable link for a document (do NOT expose raw storage links unless necessary)
router.get('/:id/view', authenticateJWT, async (req, res, next) => {
  try {
    const doc = await Document.findByPk(req.params.id);
    if (!doc) return res.status(404).json({ error: 'Not found' });
    // Only public docs for students
    if (req.user.role === 'student' && !doc.isPublic) return res.status(403).json({ error: 'Forbidden' });
    // In production: generate signed short-lived URL or proxy stream through server
    return res.json({ ok: true, fileUrl: doc.fileUrl });
  } catch (err) { next(err); }
});

// Edit document (faculty can edit their own document)
router.put('/:id', authenticateJWT, requireRole('faculty'), [body('title').optional().notEmpty()], async (req, res, next) => {
  try {
    const { id } = req.params;
    const doc = await Document.findByPk(id);
    if (!doc) return res.status(404).json({ error: 'Not found' });
    if (doc.uploadedById !== req.user.userId && req.user.role !== 'admin') return res.status(403).json({ error: 'Forbidden' });
    const { title, description, isPublic } = req.body;
    if (title) doc.title = title;
    if (description) doc.description = description;
    if (typeof isPublic !== 'undefined') doc.isPublic = isPublic;
    await doc.save();
    res.json({ ok: true, doc });
  } catch (err) { next(err); }
});

// Delete document (faculty can delete own, admin can delete any)
router.delete('/:id', authenticateJWT, requireRole('faculty'), async (req, res, next) => {
  try {
    const { id } = req.params;
    const doc = await Document.findByPk(id);
    if (!doc) return res.status(404).json({ error: 'Not found' });
    if (doc.uploadedById !== req.user.userId && req.user.role !== 'admin') return res.status(403).json({ error: 'Forbidden' });
    // remove from cloudinary
    if (doc.filePublicId) await cloudinary.uploader.destroy(doc.filePublicId, { resource_type: 'auto' });
    await doc.destroy();
    res.json({ ok: true });
  } catch (err) { next(err); }
});

module.exports = router;