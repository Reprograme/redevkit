export async function getUsers(req, res) {
  try {
    res.status(200).json([]);
  } catch (e) {
    res.status(500).end();
  }
}
