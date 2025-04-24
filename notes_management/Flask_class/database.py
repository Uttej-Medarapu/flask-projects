# pip install mysql-connector-python

import mysql.connector

db = mysql.connector.connect(
    host='localhost',
    user='root',
    password='uttej@345',
    database='personal_records'
)

cursor = db.cursor()
