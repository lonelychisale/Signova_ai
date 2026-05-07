# Signova AI

Signova AI is a Django-based project designed to provide an API application and a super admin interface for managing and interacting with the system. This README provides an overview of the project, setup instructions, and steps to run the application.

## Features
- API application for external integrations.
- Super admin interface for managing the system.
- User authentication and admin login functionality.

## Prerequisites
Ensure you have the following installed on your system:
- Python 3.8+
- pip (Python package manager)
- Django (installed via `requirements.txt`)

## Getting Started
Follow these steps to set up and run the project locally.

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Signova
```

### 2. Install Dependencies
Navigate to the project directory and install the required dependencies:
```bash
pip install -r requirements.txt
```

### 3. Apply Migrations
Run the following command to apply database migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create a Superuser (Optional)
If you need to create a new superuser, run:
```bash
python manage.py createsuperuser
```

## Running the Applications

### Running the API App
To start the API application, use the following command:
```bash
python manage.py runserver
```
The application will be accessible at `http://127.0.0.1:8000/`.

### Running the Signova Super Admin App
The super admin interface is part of the Django admin panel. To access it:
1. Start the server using the `runserver` command.
2. Navigate to `http://127.0.0.1:8000/admin` in your browser.

### Admin Login Instructions
Use the following credentials to log in to the admin panel:
- **Username:** signova
- **Password:** admin

## Migration Instructions
To ensure the database schema is up-to-date, follow these steps:
1. Generate migration files for any model changes:
   ```bash
   python manage.py makemigrations
   ```
2. Apply the migrations to the database:
   ```bash
   python manage.py migrate
   ```

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.