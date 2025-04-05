# Golf Leaderboard Application

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A web application for tracking golf scores, birdies, eagles, and tournament results. Built with Flask and PostgreSQL, deployed on Render.

## Features

- **Player Management**
  - Add and manage player profiles
  - Track individual player statistics
  - View player history and achievements

- **Score Tracking**
  - Record birdies and eagles
  - Track scores by course
  - Historical score tracking

- **Tournament System**
  - Create and manage tournaments
  - Real-time tournament leaderboard
  - Tournament result history

- **Course Management**
  - Add and manage golf courses
  - Course-specific statistics

- **Team Features**
  - Team creation and management
  - Team member assignments
  - Team statistics

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL (hosted on Supabase)
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Migrations**: Flask-Migrate

### Frontend
- **Templates**: Jinja2
- **Styling**: Bootstrap 5
- **JavaScript**: Vanilla JS
- **Icons**: Font Awesome

### Deployment
- **Platform**: Render
- **Database**: Supabase
- **Version Control**: Git

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mawdis2/golf-leaderboard.git
   cd golf-leaderboard
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file with:
   ```
   DATABASE_URL=your_database_url
   SECRET_KEY=your_secret_key
   ```

5. Run the application:
   ```bash
   python wsgi.py
   ```

## Project Structure

```
golf-leaderboard/
├── app/                    # Application package
├── templates/              # HTML templates
│   ├── base.html          # Base template
│   ├── admin/             # Admin templates
│   ├── auth/              # Authentication templates
│   └── ...                # Other templates
├── static/                # Static files
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   └── img/              # Images
├── migrations/            # Database migrations
├── app.py                # Application factory
├── config.py             # Configuration settings
├── extensions.py         # Flask extensions
├── forms.py             # Form definitions
├── middleware.py        # Application middleware
├── models.py            # Database models
├── routes.py            # Route definitions
├── wsgi.py             # WSGI entry point
├── requirements.txt     # Python dependencies
└── README.md           # Project documentation
```

## Usage

1. **Adding Players**
   - Navigate to Admin Dashboard
   - Click "Add Player"
   - Fill in player details

2. **Recording Scores**
   - Select a player
   - Choose a course
   - Enter score details

3. **Managing Tournaments**
   - Create new tournament
   - Add players to tournament
   - Record tournament scores

4. **Viewing Statistics**
   - Access player profiles
   - View leaderboards
   - Check tournament history

## Development

1. **Database Migrations**
   ```bash
   flask db migrate -m "Description of changes"
   flask db upgrade
   ```

2. **Running Tests**
   ```bash
   python -m pytest
   ```

3. **Code Style**
   - Follow PEP 8 guidelines
   - Use meaningful variable names
   - Add docstrings to functions

## Contributing

We welcome contributions from the community! Here's how you can help:

1. **Reporting Issues**
   - Check if the issue already exists
   - Provide detailed information about the problem
   - Include steps to reproduce
   - Add screenshots if relevant

2. **Feature Requests**
   - Describe the feature you'd like to see
   - Explain why it would be useful
   - Provide examples if possible

3. **Pull Requests**
   - Fork the repository
   - Create a feature branch
   - Make your changes
   - Add tests if applicable
   - Update documentation
   - Submit a pull request

4. **Code Guidelines**
   - Follow PEP 8 style guide
   - Write clear, concise code
   - Add comments where necessary
   - Include docstrings for functions
   - Write tests for new features

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or support, please open an issue in the repository or contact the maintainer. 