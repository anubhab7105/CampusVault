require('dotenv').config();
const app = require('./app');
const { sequelize } = require('./config/db');

const PORT = process.env.PORT || 4000;

(async () => {
  try {
    await sequelize.authenticate();
    console.log('Database connected');
    // Sync only in dev — for production use migrations
    // await sequelize.sync({ alter: true });

    app.listen(PORT, () => {
      console.log(`Server running on port ${PORT}`);
    });
  } catch (err) {
    console.error('Unable to connect to DB', err);
    process.exit(1);
  }
})();