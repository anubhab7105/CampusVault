-- MySQL schema for CampusVault

CREATE TABLE users (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  fullName VARCHAR(255) NOT NULL,
  collegeId VARCHAR(100) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  phone VARCHAR(50) NOT NULL,
  role ENUM('admin','faculty','student') NOT NULL DEFAULT 'student',
  passwordHash VARCHAR(255) NOT NULL,
  verified TINYINT(1) DEFAULT 0,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX (email),
  INDEX (collegeId)
);

CREATE TABLE otps (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  phone VARCHAR(50) NOT NULL,
  code VARCHAR(6) NOT NULL,
  expiresAt DATETIME NOT NULL,
  used TINYINT(1) DEFAULT 0,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX (phone),
  INDEX (expiresAt)
);

CREATE TABLE documents (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT,
  fileUrl VARCHAR(2000) NOT NULL,
  filePublicId VARCHAR(500),
  fileType VARCHAR(100),
  isPublic TINYINT(1) DEFAULT 1,
  uploadedById INT UNSIGNED,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (uploadedById) REFERENCES users(id) ON DELETE SET NULL,
  INDEX (isPublic),
  FULLTEXT INDEX title_desc (title, description)
);

CREATE TABLE comments (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  body TEXT NOT NULL,
  authorId INT UNSIGNED NOT NULL,
  documentId INT UNSIGNED NOT NULL,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (authorId) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (documentId) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE access_logs (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  userId INT UNSIGNED,
  documentId INT UNSIGNED,
  action VARCHAR(100),
  ip VARCHAR(100),
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (userId) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (documentId) REFERENCES documents(id) ON DELETE SET NULL
);

-- sample admin user insertion (password: change before production)
-- INSERT INTO users (fullName, collegeId, email, phone, role, passwordHash, verified) VALUES ('Admin One', 'ADM001', 'admin1@example.com', '+1000000000', 'admin', '$2a$10$...bcrypt...', 1);
