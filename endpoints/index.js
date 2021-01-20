const router = require("express").Router();

router.use("/api/v1/discord", require("./discord"));
router.use("/api/v1/playlist", require("./playlist"));

module.exports = router;