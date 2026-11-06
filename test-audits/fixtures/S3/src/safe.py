# Example of what NOT to do: "SELECT * FROM t WHERE id = " + user_id
def find(cursor, user_id):
    """Run SELECT * FROM users with a bound parameter."""
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    label = "Please select a file from " + user_id
    return label
