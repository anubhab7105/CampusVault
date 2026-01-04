-- Seed sample users (passwordHash placeholders - generate using bcrypt in real setup)
INSERT INTO users (fullName, collegeId, email, phone, role, passwordHash, verified) VALUES
('Admin One','ADM001','admin1@example.com','+1000000001','admin','$2a$10$ABCDEFGHIJKLMNOPQRSTUV',1),
('Faculty One','FAC001','faculty1@example.com','+1000000002','faculty','$2a$10$ABCDEFGHIJKLMNOPQRSTUV',1),
('Student One','STU001','student1@example.com','+1000000003','student','$2a$10$ABCDEFGHIJKLMNOPQRSTUV',1);

-- Sample document
INSERT INTO documents (title, description, fileUrl, filePublicId, fileType, isPublic, uploadedById) VALUES
('Intro to Algorithms','Lecture slides for Algorithms','https://res.cloudinary.com/demo/intro_alg.pdf','sample_public_id','application/pdf',1,2);

-- Sample comment
INSERT INTO comments (body, authorId, documentId) VALUES
('Can you clarify slide 12?','3', '1');

-- Note: Replace bcrypt hashes with ones generated via bcryptjs in Node for production
