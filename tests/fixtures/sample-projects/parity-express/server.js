// Orders API used as a runnable parity fixture (validation, auth, workflow, lookup).
const express = require("express");

const API_KEY = process.env.API_KEY || "demo-key";
const categories = [
  { id: 1, name: "books" },
  { id: 2, name: "games" },
  { id: 3, name: "music" },
];
const orders = [];
let nextId = 1;

const app = express();
app.use(express.json());

function authed(req) {
  return req.get("X-API-Key") === API_KEY;
}

app.get("/api/health", (req, res) => {
  res.json({ status: "ok" });
});

app.get("/api/categories", (req, res) => {
  res.json(categories);
});

app.get("/api/orders", (req, res) => {
  res.json(orders);
});

app.post("/api/orders", (req, res) => {
  if (!authed(req)) return res.status(401).json({ error: "unauthorized" });
  const data = req.body;
  if (data === null || typeof data !== "object" || Array.isArray(data)) {
    return res.status(400).json({ error: "invalid json" });
  }
  const { customer, category_id } = data;
  if (typeof customer !== "string" || customer.trim().length < 2) {
    return res.status(400).json({ error: "customer must be at least 2 characters" });
  }
  if (!Number.isInteger(category_id) || !categories.some((c) => c.id === category_id)) {
    return res.status(400).json({ error: "unknown category" });
  }
  const order = { id: nextId++, customer: customer.trim(), category_id, status: "draft" };
  orders.push(order);
  res.status(201).json(order);
});

app.get("/api/orders/:id", (req, res) => {
  const order = orders.find((o) => o.id === Number(req.params.id));
  if (!order) return res.status(404).json({ error: "not found" });
  res.json(order);
});

function transition(allowed, target) {
  return (req, res) => {
    if (!authed(req)) return res.status(401).json({ error: "unauthorized" });
    const order = orders.find((o) => o.id === Number(req.params.id));
    if (!order) return res.status(404).json({ error: "not found" });
    if (!allowed.includes(order.status)) {
      return res.status(409).json({ error: "invalid transition" });
    }
    order.status = target;
    res.json(order);
  };
}

app.post("/api/orders/:id/submit", transition(["draft"], "submitted"));
app.post("/api/orders/:id/pay", transition(["submitted"], "paid"));
app.post("/api/orders/:id/cancel", transition(["draft", "submitted"], "cancelled"));

const port = Number(process.env.PORT || 3000);
app.listen(port, "127.0.0.1", () => {
  console.log(`listening on ${port}`);
});
