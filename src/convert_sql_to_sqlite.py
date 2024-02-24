"""Read files from data/ ending with .sql and convert them to sqlite"""
import os
import re

import sqlite3

# Create a connection to the database
conn = sqlite3.connect("data/spotify.db")
cursor = conn.cursor()

# Get all files from data/ ending with .sql
files = os.listdir("data/")
files = [f for f in files if f.endswith(".sql")]

# Create a table for each file
for file in files:
    # Get the name of the table
    table_name = file.split(".")[0]
    # The table name has some numbers, so we need to remove them
    table_name = re.sub(r"\d+", "", table_name)
    # Remove the last _ if it exists
    table_name = table_name[:-1] if table_name[-1] == "_" else table_name
    print(f"Table: {table_name}")
    # Read the file
    with open(f"data/{file}", "r") as f:
        sql = f.read()

    # Get the sql query until "VALUES"
    insert_subquery = sql.split("VALUES")[0]
    # Get the columns
    columns = insert_subquery.split("(")[1].split(")")[0]
    # Split the columns
    columns = columns.split(",")
    # Create the table
    cursor.execute(f"CREATE TABLE {table_name} ({', '.join(columns)});")
    print(f"CREATE TABLE {table_name} ({', '.join(columns)});")
    # Replace in sql query spotify. by nothing
    sql = sql.replace(f"spotify.{table_name}", table_name)
    # Execute the sql
    # cursor.execute(sql)

    cursor.executescript(sql)
    conn.commit()
    cursor.close()
    conn.close()
