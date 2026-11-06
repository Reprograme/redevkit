def find(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)


def find_f(cursor, user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
