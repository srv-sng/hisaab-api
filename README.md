## Hisaab API

### Overview

The **Hisaab API** is a backend service for the Hisaab web application, built using Flask and MongoDB. This API allows users to manage entries related to shared expenses, authenticate users, and perform various CRUD operations on the data stored in a MongoDB database. It is designed to support a frontend React application that tracks expenses and calculates amounts owed among flatmates.

### Table of Contents

- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Authentication](#authentication)
- [License](#license)

### Installation

1. **Clone the repository:**

    ```bash
    git clone https://github.com/srv-sng/hisaab-api.git
    cd hisaab-api
    ```

2. **Create and activate a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate   # On Windows use `venv\Scripts\activate`
    ```

3. **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run the Flask application:**

    ```bash
    python app.py
    ```

### Environment Setup

Create a `.env` file in the root directory of your project to store the environment variables required for the application. Below is an example of the required environment variables:

```
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
BLOG_DB=hisaab_db
JWT_SECRET=your_jwt_secret_key
```

Make sure to replace `<username>`, `<password>`, and `your_jwt_secret_key` with actual values.

### Usage

1. **Start the server** by running:

    ```bash
    flask run
    ```

2. **Base URL** for the API (local development):

    ```
    http://127.0.0.1:5000/
    ```

### API Endpoints

The following is a list of available endpoints for the **Hisaab API**:

- **Home Endpoint**
  - `GET /`
  - Returns a welcome message and a link to the full documentation.

- **User Authentication**
  - `POST /register`
    - Registers a new user.
    - Request Body: `{ "username": "<username>", "password": "<password>", "register_code": "<register_code>" }`
  - `POST /login`
    - Authenticates a user and returns a JWT token.
    - Request Body: `{ "username": "<username>", "password": "<password>" }`

- **Code Management**
  - `POST /generate_code`
    - Generates a new registration code.
    - **Protected**: Requires valid JWT token in the `Authorization` header.

- **Entries Management**
  - `GET /entries`
    - Retrieves all entries.
    - **Protected**: Requires valid JWT token in the `Authorization` header.
  - `POST /entries`
    - Creates a new entry.
    - **Protected**: Requires valid JWT token in the `Authorization` header.
    - Request Body: `{ "items": "<item_name>", "price": <price>, "owed_all": <bool>, "owed_by": [<list_of_users>], "notes": "<notes>" }`
  - `GET /entries/<id>`
    - Retrieves a specific entry by ID.
    - **Protected**: Requires valid JWT token in the `Authorization` header.
  - `PUT /entries/<id>`
    - Updates an existing entry.
    - **Protected**: Requires valid JWT token in the `Authorization` header.
    - Request Body: Same as POST `/entries`.
  - `DELETE /entries/<id>`
    - Deletes an entry.
    - **Protected**: Requires valid JWT token in the `Authorization` header.

- **Activity Management**
  - `GET /activities/<month>`
    - Retrieves all activities for a specific month.
    - **Protected**: Requires valid JWT token in the `Authorization` header.

- **Statistics**
  - `GET /stats/daily_person/<month>`
    - Retrieves daily statistics by person for a given month.
    - **Protected**: Requires valid JWT token in the `Authorization` header.
  - `GET /stats/daily/<month>`
    - Retrieves daily statistics for all entries in a given month.
    - **Protected**: Requires valid JWT token in the `Authorization` header.

- **User Management**
  - `GET /users`
    - Retrieves a list of all registered users.
    - **Protected**: Requires valid JWT token in the `Authorization` header.

### Authentication

This API uses JWT (JSON Web Token) for authentication. After a successful login, a token is returned to the user, which should be included in the `Authorization` header for subsequent requests that require authentication. Example:

```
Authorization: Bearer <your_token_here>
```

### License

This project is licensed under... well, no specific license. Feel free to use it however you like. Consider it public domain—use it, modify it, share it, or just ignore it.
