const { sequelize } = require('../config/db');
(async () => {
  try {
    await sequelize.authenticate();
    console.log('DB connected. Syncing...');
    await sequelize.sync({ alter: true });
    console.log('Synced.');
    process.exit(0);
  } catch (e) { console.error(e); process.exit(1); }
})();