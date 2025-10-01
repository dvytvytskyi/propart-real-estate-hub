from app import app

# Gunicorn очікує змінну 'application'
application = app

if __name__ == "__main__":
    app.run()
