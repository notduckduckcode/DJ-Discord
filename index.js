const express = require("express");
require("dotenv").config();
const rateLimiter = require("express-rate-limit");
const bodyParser = require("body-parser");
const router = express.Router();
const rethinkdb = require("rethinkdbdash")({
  db: "djdiscord",
  user: process.env.RETHINKDB_USER,
  password: process.env.RETHINKDB_PASS,
  servers: [
    { host: process.env.RETHINKDB_HOST, port: process.env.RETHINKDB_PORT },
  ],
});

const passport = require("passport");
var DiscordStrategy = require("passport-discord").Strategy;
const { query } = require("express");
const api = express();
var scopes = ["identify", "email"];

api.use(bodyParser.urlencoded({ extended: false }));
api.use(bodyParser.json());
api.use(passport.initialize());
api.use(passport.session());

passport.serializeUser(function(user, done) {
  done(null, user);
});

passport.deserializeUser(function(user, done) {
  done(null, user);
});

passport.use(
  new DiscordStrategy(
    {
      clientID: process.env.DISCORD_CLIENT_ID,
      clientSecret: process.env.DISCORD_CLIENT_SECRET,
      callbackURL: "http://localhost:3000/api/v1/playlist/callback",
      scope: scopes,
    },
    function (accessToken, refreshToken, profile, cb) {
      console.log(profile);
      if (rethinkdb.table("api").filter({id: profile.id}).run()) {
        return cb(null, false)
      }
      rethinkdb.table("api").insert(profile).run((result) => console.log);
      return cb(null, {msg: "done"})
    }
  )
);

const playlistLimiter = rateLimiter({
  windowMs: 60 * 60 * 1000, // 1 hour window
  max: 3, // start blocking after 5 requests
  message: {
    code: 429,
    msg: "too many playlists were created from this IP",
    ratelimit: 3600,
  },
});

api.get("/api/v1/playlist", passport.authenticate("discord"));

api.get(
  "/api/v1/playlist/callback",
  passport.authenticate("discord", {
    failureRedirect: "/",
  }),
  function (req, res) {
    res.redirect("/api/v1/success"); // Successful auth
  }
);

api.get("/api/v1/success", (req, res) => {
  console.log(req.body);
  console.log(req.header);
  res.json({msg: "poggers, you're in!", code: 200})
});

api.listen(3000, () => {
  console.log("API up and running!");
});

api.post("/api/v1/playlist/new", playlistLimiter, (req, res) => {
  const _query = {
    author: req.body.author,
    cover: req.body.cover,
    songs: req.body.songs
  }
  rethinkdb
    .table("accounts")
    .insert(
      _query
    )
    .run((result) => {
      res.json({ code: 200, msg: "done", result: result });
    });
});

api.get("/", (req, res) => {
  res.send("hi");
})
