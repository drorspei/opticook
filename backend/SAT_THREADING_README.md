# SAT Solver Threading Implementation

## Overview

This implementation adds a background SAT solver thread to the OptiCook application that continuously optimizes the cooking schedule while the main FastAPI server handles chef interactions without blocking.

## Architecture

### Key Components

1. **SATSolverThread** (`sat_solver_thread.py`): A dedicated thread that runs the SAT solver continuously
2. **Interruption System**: Uses `threading.Event` to safely interrupt and restart the SAT solver
3. **Session Synchronization**: Thread-safe session state management between main thread and SAT solver thread
4. **Statistics Tracking**: Comprehensive monitoring of SAT solver performance

### How It Works

1. **Session Start**: When a cooking session starts, the SAT solver thread is initialized with the initial session state
2. **Continuous Optimization**: The SAT solver runs continuously in the background, updating the `SATSchedule` with improved solutions
3. **Real-time Interruption**: When a chef finishes a task, the SAT solver is interrupted and restarted with updated session state
4. **Non-blocking API**: All API endpoints remain responsive as they use the stored `SATSchedule` for assignments

## API Changes

### New Endpoint

- `GET /api/v1/session/current/sat-stats`: Returns statistics about the SAT solver thread

### Modified Endpoints

- `POST /api/v1/session/current/start`: Now starts the SAT solver thread
- `POST /api/v1/session/current/done`: Now interrupts and restarts the SAT solver
- `POST /api/v1/session/current/reset`: Now stops the SAT solver thread

## Thread Safety

- **Session Lock**: Uses `threading.Lock` to ensure thread-safe session updates
- **Deep Copying**: Session state is deep-copied to prevent race conditions
- **Interruption Events**: Uses `threading.Event` for safe interruption signaling

## Performance Monitoring

The SAT solver thread tracks the following statistics:

- `runs`: Total number of SAT solver runs
- `successful_updates`: Number of times the schedule was successfully updated
- `interruptions`: Number of times the solver was interrupted
- `errors`: Number of errors encountered
- `total_time`: Total time spent in SAT solving
- `last_run_time`: Time of the most recent SAT solver run

## Interruption Strategy

The implementation uses **cooperative interruption** with `threading.Event`:

### Pros:
- Clean and safe interruption
- No resource cleanup issues
- Can save partial results if needed
- Works well with long-running loops

### Implementation:
- The `sat_search` function now accepts an `interruption_check` callback
- The binary search loop checks for interruption at each iteration
- The SAT solver thread provides a lambda that checks the interruption event

## Usage Example

```python
# Start a session (automatically starts SAT solver thread)
response = requests.post("/api/v1/session/current/start", json={
    "recipe_id": "example_recipe",
    "chefs": ["Alice", "Bob"]
})

# Check SAT solver statistics
stats = requests.get("/api/v1/session/current/sat-stats")
print(stats.json())

# When a chef finishes a task (automatically interrupts and restarts SAT solver)
response = requests.post("/api/v1/session/current/done", json={
    "chef": "Alice",
    "instruction_index": 0,
    "timestamp_seconds": 120.0
})
```

## Testing

Run the test script to verify the implementation:

```bash
cd backend
python test_sat_threading.py
```

## Configuration

### Timeout Settings

- SAT solver timeout: 30 seconds per run (configurable in `sat_solver_thread.py`)
- Thread join timeout: 5 seconds (configurable in `stop()` method)

### Logging

The SAT solver thread uses Python's logging module with INFO level. Logs include:
- Thread start/stop events
- Interruption events
- Successful schedule updates
- Error conditions

## Future Improvements

1. **More Granular Interruption**: Add interruption checks within the SAT solver's clause generation
2. **Caching**: Cache partial results between runs
3. **Parallel SAT Solving**: Allow multiple SAT solver instances for complex recipes
4. **WebSocket Updates**: Real-time status updates to the frontend
5. **Configurable Parameters**: Make timeout and frequency configurable via API

## Troubleshooting

### Common Issues

1. **Thread Not Starting**: Check if dependencies are installed (`pycryptosat`)
2. **High CPU Usage**: The SAT solver runs continuously; this is expected behavior
3. **Memory Leaks**: Ensure proper cleanup by calling `stop()` when resetting sessions

### Debug Mode

Enable debug logging by modifying the logging level in `sat_solver_thread.py`:

```python
logging.basicConfig(level=logging.DEBUG)
``` 