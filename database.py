import streamlit as st
import sqlite3 
from datetime import datetime

DB_NAME = ("Nutrition.db")

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute ('''CREATE TABLE IF NOT EXISTS food_logs 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      date TEXT, food TEXT, protein REAL, carbs REAL, fats REAL)''')
        conn.commit()


def save_meal(food, p, c, f):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("Insert into food_logs (date, food, protein, carbs, fats) values (?, ?, ?, ?, ?)",
                  now, food, p, c, f)
        conn.commit()

def today_intake():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("Select sum (protein), SUM(carbs), SUM(fats) FROM food_logs WHERE date LIKE ?", (f'{today}%',))
        total = c.fetchone()
        return [t if t else 0.0 for t in total]