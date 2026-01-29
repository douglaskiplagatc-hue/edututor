from app import create_app, db
from app.models import User, Tutor, Booking, Review, Message, Payment, Schedule, Notification
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Tutor": Tutor,
        "Booking": Booking,
        "Review": Review,
        "Message": Message,
        "Payment": Payment,
        "Schedule": Schedule,
        "Notification": Notification,
    }

if __name__ == "__main__":
    app.run(debug=True)