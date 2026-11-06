export function findUser(db, userId) {
  const q = "SELECT ... " + userId;
  return db.query(q);
}
export function findOrder(db, orderId) {
  return db.query('SELECT * FROM orders WHERE id = ' + orderId);
}
