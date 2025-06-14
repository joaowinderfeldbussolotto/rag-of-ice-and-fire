# GraphRAG Query Interface

A Streamlit web app for querying GraphRAG and traditional RAG (Retrieval-Augmented Generation) methods. The app allows users to submit questions and compare results from multiple retrieval methods side-by-side.

## Features

- Query multiple RAG methods in parallel
- Compare results in a single view (side-by-side or tabs)
- Async API polling for responsive UX

## Setup

1. **Clone the repository**  
   ```bash
   git clone <repo-url>
   cd rag-of-ice-and-fire/app
   ```

2. **Install dependencies**  
   It's recommended to use a virtual environment.
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**  
   Create a `.env` file in the project root (one level above `app/`) with:
   ```
   API_URL=http://localhost:8000
   ```

4. **Run the app**  
   ```bash
   streamlit run main.py
   ```

   The app will be available at [http://localhost:8501](http://localhost:8501).

## Docker

To run the app in Docker:

```bash
docker build -t grag-app .
docker run -p 8501:8501 --env API_URL=http://host.docker.internal:8000 grag-app
```

## Usage

- Enter your question in the text area.
- Select one or more retrieval methods.
- Click "Search" to run queries and view results.

## Project Structure

- `main.py` - Streamlit app entry point
- `ui_components.py` - UI and API logic
- `requirements.txt` - Python dependencies
- `Dockerfile` - Containerization support

## License

MIT License
