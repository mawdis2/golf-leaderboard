Full Stack Web Development Starter Stack Setup
Backend:
1. Language: Python
2. Framework: Flask (simple and lightweight) 
3. Database: SQLLite

Frontend: 
1. HTML: Structure the web pages
2. CSS: Style the web pages
3. JavaScript: Adds in interactivity and dynamic elements 



Folder Structure:
/my_web_project
    /templates
        index.html
        leaderboard.html
        contact.html
    /static
        leaderboard.js
        styles.css
    /models.py            # Contains the Player and Birdie models, and db instance
    /routes.py            # Contains the route definitions and imports db
    /app.py               # Entry point to start the app and handle home/contact routes
    /init_db.py           # For creating the database tables
