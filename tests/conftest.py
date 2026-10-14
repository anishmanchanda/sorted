import os

# Tests never touch the real DB file.
os.environ["BRAIN_DB_URL"] = "sqlite://"
