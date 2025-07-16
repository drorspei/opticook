# OptiCook - Collaborative Cooking Made Optimal

OptiCook is an intelligent collaborative cooking app that transforms complex recipes into optimally scheduled tasks for multiple chefs. By solving the scheduling problem as a SAT problem, OptiCook ensures that your cooking team works in perfect harmony, minimizing total cooking time while maximizing efficiency.

## Features

- **Smart Recipe Import**: Enter recipes manually or provide a URL - our AI-powered parser extracts and structures the recipe automatically
- **Optimal Task Scheduling**: Automatically schedules cooking tasks across multiple chefs to minimize total cooking time
- **Real-time Coordination**: Interactive UI guides each chef through their assigned tasks with clear instructions
- **Task Types**: Distinguishes between attention-requiring tasks (cutting, mixing) and passive tasks (baking, boiling)
- **Progress Tracking**: Chefs mark tasks as complete in real-time, keeping everyone synchronized
- **Swipeable Task Cards**: Each chef gets their own carousel of tasks they can swipe through

## How It Works

1. **Recipe Input**: Add a recipe by entering details manually or providing a recipe URL
2. **Chef Assignment**: Specify how many chefs will be cooking
3. **Optimal Scheduling**: The app solves a SAT problem to find the optimal task distribution
4. **Cooking Session**: Each chef follows their personalized task list on a beautiful, intuitive interface
5. **Real-time Updates**: As tasks are completed, the UI updates to keep everyone in sync

## Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Python 3.12** - Core backend language
- **LiteLLM** - AI-powered recipe parsing
- **Selenium & BeautifulSoup** - Web scraping for recipe URLs
- **Pydantic** - Data validation

### Frontend
- **React 18** with TypeScript
- **Tailwind CSS** - Responsive, utility-first styling
- **Embla Carousel** - Smooth, swipeable task cards
- **Lucide React** - Beautiful icons

## Installation

### Prerequisites

- Python 3.12+
- Node.js 16+
- Chrome/Chromium browser (for recipe URL parsing)

### Option 1: Using Nix

```bash
nix-shell
cd frontend && npm install && npm build \
  && cd ../backend && uvicorn main:app --reload
```

### Option 2: Standard Installation

#### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm build
```

#### Run backend

```bash
# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --reload
```

The app will be available at http://localhost:8000

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Add your LLM API key for recipe parsing
OPENAI_API_KEY=your_api_key_here
```

### ChromeDriver

The recipe URL parsing feature requires ChromeDriver. The app will attempt to download it automatically, or you can install it manually:

- **Ubuntu/Debian**: `sudo apt-get install chromium-driver`
- **macOS**: `brew install chromedriver`
- **Windows**: Download from [ChromeDriver website](https://chromedriver.chromium.org/)

## Usage

1. **Start a Cooking Session**
   - Navigate to http://localhost:8000
   - Click "New Cooking Session"

2. **Add a Recipe**
   - **Manual Entry**: Fill in the recipe form with ingredients and steps
   - **From URL**: Paste a recipe URL and let the AI parse it for you

3. **Configure Chefs**
   - Enter the number of chefs participating
   - The app will optimize task distribution

4. **Start Cooking**
   - Each chef gets their own task carousel
   - Swipe through tasks or use navigation buttons
   - Mark tasks as complete when finished
   - The UI shows real-time progress for all chefs

## Project Structure

```
opticook/
├── backend/              # FastAPI backend
│   ├── main.py          # API endpoints
│   ├── data_models.py   # Domain models
│   ├── computations.py  # Scheduling algorithm
│   ├── parse.py         # Recipe parsing logic
│   └── retrive.py       # Web scraping
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── api.ts       # API client
│   │   └── types.ts     # TypeScript types
│   └── package.json
└── shell.nix           # Nix environment
```

## Development

### Running Tests

```bash
# Backend tests (if available)
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Design Principles

- **Optimal Scheduling**: Uses 30-second "quanta" as base time units for precise scheduling
- **On-Premise**: Designed for local use, no cloud dependencies
- **Single Session**: Handles one cooking session at a time (MVP approach)
- **Real-time Sync**: All chefs see updates immediately as tasks are completed

## Contributing

We welcome contributions! Please feel free to submit a Pull Request.

## Team

Omer Ben Neria, Dror Speiser
