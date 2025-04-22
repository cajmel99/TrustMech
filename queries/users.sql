-- create_user.sql
INSERT INTO users (name, surname, email, phone, password_hash, role, created_at)
VALUES (%(name)s, %(surname)s, %(email)s, %(phone)s, %(password_hash)s, %(role)s, NOW())
RETURNING id, email;

-- get_user_by_email.sql
SELECT * FROM users WHERE email = %(email)s;
