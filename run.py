import os
from flaskblog import app


if __name__ == "__main__":
    # If running on Heroku, DYNO is set; otherwise, assume local
    debug_mode = not bool(os.environ.get("DYNO"))
    app.run(debug=debug_mode)