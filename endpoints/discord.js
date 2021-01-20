const passport = require("passport");
const bodyParser = require("body-parser");
var DiscordStrategy = require("passport-discord").Strategy;
const router = require("express").Router();
const rethinkdb = require("../utils/database");
var scopes = ["identify", "email"];
require("dotenv").config();

router.use(bodyParser.urlencoded({ extended: false }));
router.use(bodyParser.json());
router.use(passport.initialize());
router.use(passport.session());

passport.serializeUser(function (user, done) {
  done(null, user);
});

passport.deserializeUser(function (user, done) {
  done(null, user);
});

passport.use(
  new DiscordStrategy(
    {
      clientID: process.env.DISCORD_CLIENT_ID,
      clientSecret: process.env.DISCORD_CLIENT_SECRET,
      callbackURL: "http://localhost:3000/api/v1/discord",
      scope: scopes,
      passReqToCallback: true,
    },
    async function (req, accessToken, refreshToken, profile, cb) {
      rethinkdb
        .table("api")
        .filter({ id: profile.id })
        .run((result) => {
          if (result)
            return cb(null, false, {
              opcode: 2,
              message: "account was already registered",
            });
        });
      rethinkdb
        .table("api")
        .insert({
          id: profile.id,
          access_token: accessToken,
          refresh_token: refreshToken,
          account: profile,
        })
        .run((result) => console.log);
      return cb(null, {
        id: profile.id,
        access_token: accessToken,
        refresh_token: refreshToken,
        account: profile,
      });
    }
  )
);

router.get("/", function (req, res) {
  passport.authenticate(
    "discord",
    {
      failureRedirect: "/failure",
    },
    function (err, user, info) {
      if (err) res.status(500).json({ code: 500, msg: err });
      else if (info && info.opcode === 2)
        res.status(409).json({ code: 409, msg: "you're already registered" });
      else res.redirect("../../../dashboard");
    }
  )(req, res);
});

router.get("/success", (req, res) => {
  console.log(req.body);
  console.log(req.header);
  res.json({ msg: "poggers, you're in!", code: 200 });
});

module.exports = router;
