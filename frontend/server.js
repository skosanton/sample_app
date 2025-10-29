const express = require("express");
const path = require("path");
const { createProxyMiddleware } = require("http-proxy-middleware");
const app = express();

const BACKEND_URL = process.env.BACKEND_URL || "https://app.skosyrev.com/";
const BASE_PATH = "/fe/"

// Proxy /fe/api/* (or whatever BASE_PATH is) to backend
app.use(`${BASE_PATH}api`, createProxyMiddleware({
  target: BACKEND_URL,
  changeOrigin: true,
  pathRewrite: (p) => p.replace(`${BASE_PATH}api`, "/api"),
}));

// Serve static files under /fe
app.use(BASE_PATH, express.static(path.join(__dirname, "public")));

// (optional) SPA-style fallback for deep links under /fe
app.get(`${BASE_PATH}*`, (req, res) =>
  res.sendFile(path.join(__dirname, "public", "index.html"))
);

const port = process.env.PORT || 3000;
app.listen(port, () => console.log(`Frontend on ${port}, BASE_PATH=${BASE_PATH}, proxy -> ${BACKEND_URL}`));
