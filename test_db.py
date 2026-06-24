import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="SStavana@1007"
)

cursor = conn.cursor()

cursor.execute("SELECT @@port")
print("Port:", cursor.fetchone())

cursor.execute("SHOW DATABASES")
for db in cursor:
    print(db)