const router = require("express").Router();
const rateLimiter = require("express-rate-limit");
const rethinkdb = require("../utils/database")

const playlistLimiter = rateLimiter({
  windowMs: 60 * 60 * 1000,
  max: 3,
  message: {
    code: 429,
    msg: "too many playlists were created from this IP",
    ratelimit: 3600,
  },
});

router.post("/new", playlistLimiter, (req, res) => {
  const _query = {
    author: req.body.author,
    cover: req.body.cover,
    songs: req.body.songs,
  };
  rethinkdb
    .table("accounts")
    .insert(_query)
    .run((result) => {
      res.json({ code: 200, msg: "done", result: result });
    });
});

module.exports = router;
