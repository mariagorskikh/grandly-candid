# Grantly - Smart Grant Finder

Grantly is an intelligent grant search platform that helps nonprofits find and match with relevant funding opportunities. It uses the Candid API to access grant data and provides a modern, user-friendly interface for searching and filtering grants.

## Features

- Modern, responsive web interface
- Real-time grant search
- Advanced filtering options
- Smart results display
- Integration with Candid Grants API

## Setup

1. Clone the repository:
```bash
git clone https://github.com/[your-username]/grantly.git
cd grantly
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a .env file with your Candid API key:
```bash
CANDID_API_KEY=your_api_key_here
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:8080`

## Environment Variables

- `CANDID_API_KEY`: Your Candid API subscription key (required)

## Tech Stack

- Backend: Python/Flask
- Frontend: HTML, JavaScript, Tailwind CSS
- API: Candid Grants API

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
