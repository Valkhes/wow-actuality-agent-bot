# WoW Actuality Discord Bot

A multi-container Discord bot system that provides World of Warcraft news updates through AI-powered responses, featuring web crawling, RAG database storage, and security monitoring.

## Architecture

- **Discord Bot Container**: Handles Discord interactions and `/ask` commands
- **API Container**: LangChain agent with Gemini 2.0 for intelligent responses  
- **ChromaDB Container**: Vector database for RAG storage
- **LiteLLM Gateway**: Prompt injection protection
- **Langfuse Container**: Token usage monitoring
- **Web Crawler**: Blizzspirit.com article extraction service

## Quick Start

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd wow-actuality-agent-bot
   ```

2. **Configure Environment**
   ```bash
   cp .env.template .env
   # Edit .env with your API keys and configuration
   ```

3. **Build and Run**
   ```bash
   docker-compose up --build
   ```

4. **Access Services**
   - Langfuse Dashboard: http://localhost:3000
   - ChromaDB API: http://localhost:8000
   - LiteLLM Gateway: http://localhost:4000
   - API Service: http://localhost:8000

## Environment Configuration

Copy `.env.template` to `.env` and configure:

- `DISCORD_BOT_TOKEN`: Your Discord bot token
- `GOOGLE_API_KEY`: Your Gemini API key
- `LANGFUSE_SECRET_KEY`: Langfuse secret key
- `LANGFUSE_PUBLIC_KEY`: Langfuse public key
- Other service configurations as needed

## Development

Follow the implementation tasks in `tasks.md` for detailed development steps.

## Services

- **discord-bot**: Discord bot service
- **api-service**: FastAPI service with LangChain
- **crawler-service**: Web crawler for articles
- **litellm-gateway**: Security gateway
- **chromadb**: Vector database
- **langfuse**: Monitoring dashboard
- **postgres**: Database for Langfuse

## License

MIT License
