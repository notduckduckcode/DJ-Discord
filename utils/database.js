const rethinkdb = require("rethinkdbdash")({
  db: "djdiscord",
  user: process.env.RETHINKDB_USER,
  password: process.env.RETHINKDB_PASS,
  servers: [
    { host: process.env.RETHINKDB_HOST, port: process.env.RETHINKDB_PORT },
  ],
})();

module.exports = rethinkdb;
