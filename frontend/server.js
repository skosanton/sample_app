const express = require("express");
const path = require("path");
const { createProxyMiddleware } = require("http-proxy-middleware");
const app = express();

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
app.use("/fe/api", createProxyMiddleware({ target: BACKEND_URL, changeOrigin: true }));

app.use(express.static(path.join(__dirname, "public")));

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Frontend listening on ${port}, proxy -> ${BACKEND_URL}`));
