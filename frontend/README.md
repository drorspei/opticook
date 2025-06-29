# Opticook Frontend

A modern React-based frontend for the Opticook cooking session scheduling system.

## Features

- **Session Setup**: Select recipes and configure chefs
- **Real-time Monitoring**: Live updates of cooking progress
- **Chef Status**: Individual chef status and task assignments
- **Task Management**: Visual task cards with progress tracking
- **Auto-refresh**: Automatic session state updates
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

- Node.js 16+ 
- npm or yarn
- Backend server running on `http://localhost:8000`

## Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## Development

The frontend is built with:
- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Lucide React** for icons
- **Proxy configuration** to connect to backend

## Project Structure

```
src/
├── components/          # React components
│   ├── TaskCard.tsx    # Individual task display
│   ├── ChefStatus.tsx  # Chef status and info
│   └── SessionSetup.tsx # Session initialization
├── api.ts              # Backend API client
├── types.ts            # TypeScript type definitions
├── utils.ts            # Utility functions
├── App.tsx             # Main application component
└── index.tsx           # Application entry point
```

## API Integration

The frontend communicates with the backend using the REST API defined in `opticook_spec_v1.md`:

- `GET /api/v1/session/current/recipes` - List available recipes
- `POST /api/v1/session/current/start` - Start new session
- `POST /api/v1/session/current/refresh` - Refresh session state
- `POST /api/v1/session/current/done` - Mark task complete
- `GET /api/v1/session/current/state` - Get current session
- `POST /api/v1/session/current/reset` - Reset session

## Usage

1. **Start Session**: Select a recipe and add chefs
2. **Monitor Progress**: Watch real-time updates of cooking tasks
3. **Mark Tasks Complete**: Click "Mark Step Complete" for manual tasks
4. **Reset**: Use the reset button to start over

## Building for Production

```bash
npm run build
```

This creates an optimized build in the `build/` directory. 