<a name="readme-top"></a>

<div align="center">
<img src="https://microsoft.github.io/autogen/0.2/img/ag.svg" alt="AutoGen Logo" width="100">

[![Twitter](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40pyautogen)](https://twitter.com/pyautogen)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Company?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/company/105812540)
[![Discord](https://img.shields.io/badge/discord-chat-green?logo=discord)](https://aka.ms/autogen-discord)
[![Documentation](https://img.shields.io/badge/Documentation-AutoGen-blue?logo=read-the-docs)](https://microsoft.github.io/autogen/)
[![Blog](https://img.shields.io/badge/Blog-AutoGen-blue?logo=blogger)](https://devblogs.microsoft.com/autogen/)

</div>

<div align="center" style="background-color: rgba(255, 235, 59, 0.5); padding: 10px; border-radius: 5px; margin: 20px 0;">
  <strong>Important:</strong> This is the official project. We are not affiliated with any fork or startup. See our <a href="https://x.com/pyautogen/status/1857264760951296210">statement</a>.
</div>

# PharmaDB Research Agent - AutoGen Multi-Agent System

![AutoGen](https://img.shields.io/badge/AutoGen-v0.4-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Deployment](https://img.shields.io/badge/Deployment-Render-purple)

An intelligent pharmaceutical research microservice powered by Microsoft AutoGen multi-agent AI system with **real tool execution**. This service provides deep research capabilities for drug discovery, regulatory analysis, and pharmaceutical data processing using live web search, file analysis, and multi-agent reasoning.

**🔥 New Features:**
- ✅ **Live Tavily Web Search** - Real-time pharmaceutical research with actual URLs
- ✅ **CSV Data Analysis** - SQL queries on uploaded files using DuckDB  
- ✅ **PDF Document Processing** - Text extraction and analysis using pdfplumber
- ✅ **Real Tool Integration** - All tools actively execute and provide real data

## 🚀 **LIVE API & Integration Ready**

**Production URL**: `https://pharmadb-research-agent-autogent.onrender.com`

**Status**: ✅ **PRODUCTION READY** - Stateless, concurrent-safe, multiple users supported

## 📋 Quick Start for Main App Integration

### 1. **Test the API** (Main App Developer)

```bash
# Install test dependencies
pip install httpx

# Test the integration
python test_integration.py --url https://pharmadb-research-agent-autogent.onrender.com

# Check health
curl https://pharmadb-research-agent-autogent.onrender.com/health
```

### 2. **Basic Integration Example**

```python
import httpx

async def call_research_service(question: str, files: list = None):
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            "https://pharmadb-research-agent-autogent.onrender.com/api/v1/research",
            json={"question": question, "file_ids": files}
        )
        return response.json()

# Example usage
result = await call_research_service("What are the side effects of metformin?")
print(result["final_answer"])  # Markdown-formatted research answer
```

### 3. **API Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check service health and configuration |
| `/api/v1/research` | POST | Submit research questions with optional files |
| `/docs` | GET | Interactive API documentation |

## 📚 Complete Integration Documentation

### For Main App Developers:

1. **[API Integration Guide](API_INTEGRATION_GUIDE.md)** - Complete integration instructions with code examples
2. **[OpenAPI Specification](openapi.yaml)** - Formal API documentation 
3. **[Scaling Recommendations](SCALING_RECOMMENDATIONS.md)** - Production optimization guidance
4. **[Integration Test Script](test_integration.py)** - Test your integration

### Key Features for Integration:

✅ **Stateless Design** - Multiple users can call API concurrently  
✅ **Comprehensive Error Handling** - Graceful failure modes  
✅ **Markdown Responses** - Rich formatted research answers  
✅ **File Analysis Support** - CSV, PDF processing via Supabase  
✅ **Web Search Integration** - Real-time information gathering  
✅ **Agent Transparency** - Step-by-step reasoning included  

## 🏗️ Architecture Overview

```
Main App → HTTP Request → PharmaDB Research Microservice
                           ├── Analyst Agent (Question Analysis)
                           ├── DataRunner Agent (Tool Execution)
                           └── Writer Agent (Response Synthesis)
                           
Tools Available:
├── Web Search (Tavily API)
├── CSV Query (DuckDB + Pandas)
├── PDF Reading (pdfplumber)
└── Database Query (Supabase)
```

## 🛠️ Local Development

### Prerequisites
- Python 3.11+
- Virtual environment
- Required API keys (OpenAI, Tavily, Supabase)

### Setup
```bash
# Clone and setup
git clone <repository>
cd PharmaDB-research-agent-autogent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp sample.env .env.local
# Edit .env.local with your API keys

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables Required
```bash
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_BUCKET_NAME=pharma_research_files
```

## 🧪 Testing

```bash
# Run all tests
python run_tests.py

# Run specific test categories
pytest tests/test_api.py -v          # API endpoint tests
pytest tests/test_tools.py -v        # Tool functionality tests  
pytest tests/test_integration.py -v  # Integration tests

# Test live API integration
python test_integration.py --url https://pharmadb-research-agent-autogent.onrender.com
```

## 🎯 Example Use Cases

### Pharmaceutical Research
```python
# Drug information queries
await research("What are the contraindications for warfarin?")

# Regulatory research  
await research("What are FDA requirements for clinical trial Phase II?")

# Drug discovery
await research("Latest developments in CRISPR for genetic disorders 2024")
```

### Data Analysis
```python
# CSV data analysis
await research(
    "Find all antidiabetic drugs with price under $100", 
    file_ids=["drug_database.csv"]
)

# PDF document analysis
await research(
    "Summarize the key findings from this clinical trial",
    file_ids=["clinical_study.pdf"] 
)
```

## 📊 Performance & Scaling

- **Response Time**: 3-8 seconds (typical with real tools) | Up to 2 minutes (complex multi-source)
- **Web Search**: 3.94-4.68 seconds with live Tavily API calls
- **File Analysis**: 4.5-8.32 seconds for CSV/PDF processing  
- **Real Data Sources**: 3-7 URLs and file results per query
- **Concurrent Users**: 10-20 per instance | 200+ with load balancing
- **Memory Usage**: ~50-100MB per request
- **Stateless Design**: Horizontally scalable

## 🔒 Security & Production

- **API Keys**: Secured via environment variables
- **Input Validation**: Request sanitization and limits
- **Error Handling**: No sensitive data in error responses  
- **Rate Limiting**: Recommended for production use
- **CORS**: Configurable for frontend integration

## 🚀 Deployment

### Render (Current Production)
Deployed at: `https://pharmadb-research-agent-autogent.onrender.com`

Auto-deploys from main branch with environment variables configured.

### Docker Deployment
```bash
# Build image
docker build -t pharma-research-api .

# Run container
docker run -p 8000:8000 --env-file .env pharma-research-api
```

## 📞 Support & Contributing

### For Main App Integration Issues:
1. Test with `test_integration.py` first
2. Check the `/health` endpoint
3. Review `API_INTEGRATION_GUIDE.md`
4. Verify timeout settings (recommend 300s)

### For Development:
- Follow coding preferences in `.cursor/rules/`
- Always add tests for new features  
- Use proper git commit messages with author details
- Keep functions under 200-300 lines

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

**Ready to integrate!** This microservice is production-ready and designed for seamless integration with your main pharmaceutical application. The stateless architecture ensures multiple users can research concurrently without conflicts.

## Where to go next?

<div align="center">

|               | [![Python](https://img.shields.io/badge/AutoGen-Python-blue?logo=python&logoColor=white)](./python)                                                                                                                                                                                                                                                                                                                | [![.NET](https://img.shields.io/badge/AutoGen-.NET-green?logo=.net&logoColor=white)](./dotnet) | [![Studio](https://img.shields.io/badge/AutoGen-Studio-purple?logo=visual-studio&logoColor=white)](./python/packages/autogen-studio)                     |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Installation  | [![Installation](https://img.shields.io/badge/Install-blue)](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/installation.html)                                                                                                                                                                                                                                                            | [![Install](https://img.shields.io/badge/Install-green)](https://microsoft.github.io/autogen/dotnet/dev/core/installation.html) | [![Install](https://img.shields.io/badge/Install-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/installation.html) |
| Quickstart    | [![Quickstart](https://img.shields.io/badge/Quickstart-blue)](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/quickstart.html#)                                                                                                                                                                                                                                                            | [![Quickstart](https://img.shields.io/badge/Quickstart-green)](https://microsoft.github.io/autogen/dotnet/dev/core/index.html) | [![Usage](https://img.shields.io/badge/Quickstart-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html#)        |
| Tutorial      | [![Tutorial](https://img.shields.io/badge/Tutorial-blue)](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/index.html)                                                                                                                                                                                                                                                            | [![Tutorial](https://img.shields.io/badge/Tutorial-green)](https://microsoft.github.io/autogen/dotnet/dev/core/tutorial.html) | [![Usage](https://img.shields.io/badge/Tutorial-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html#)        |
| API Reference | [![API](https://img.shields.io/badge/Docs-blue)](https://microsoft.github.io/autogen/stable/reference/index.html#)                                                                                                                                                                                                                                                                                                    | [![API](https://img.shields.io/badge/Docs-green)](https://microsoft.github.io/autogen/dotnet/dev/api/Microsoft.AutoGen.Contracts.html) | [![API](https://img.shields.io/badge/Docs-purple)](https://microsoft.github.io/autogen/stable/user-guide/autogenstudio-user-guide/usage.html)               |
| Packages      | [![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/) <br> [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/) <br> [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/) | [![NuGet Contracts](https://img.shields.io/badge/NuGet-Contracts-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.Contracts/) <br> [![NuGet Core](https://img.shields.io/badge/NuGet-Core-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.Core/) <br> [![NuGet Core.Grpc](https://img.shields.io/badge/NuGet-Core.Grpc-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.Core.Grpc/) <br> [![NuGet RuntimeGateway.Grpc](https://img.shields.io/badge/NuGet-RuntimeGateway.Grpc-green?logo=nuget)](https://www.nuget.org/packages/Microsoft.AutoGen.RuntimeGateway.Grpc/) | [![PyPi autogenstudio](https://img.shields.io/badge/PyPi-autogenstudio-purple?logo=pypi)](https://pypi.org/project/autogenstudio/)                       |

</div>


Interested in contributing? See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines on how to get started. We welcome contributions of all kinds, including bug fixes, new features, and documentation improvements. Join our community and help us make AutoGen better!

Have questions? Check out our [Frequently Asked Questions (FAQ)](./FAQ.md) for answers to common queries. If you don't find what you're looking for, feel free to ask in our [GitHub Discussions](https://github.com/microsoft/autogen/discussions) or join our [Discord server](https://aka.ms/autogen-discord) for real-time support. You can also read our [blog](https://devblogs.microsoft.com/autogen/) for updates.

## Legal Notices

Microsoft and any contributors grant you a license to the Microsoft documentation and other content
in this repository under the [Creative Commons Attribution 4.0 International Public License](https://creativecommons.org/licenses/by/4.0/legalcode),
see the [LICENSE](LICENSE) file, and grant you a license to any code in the repository under the [MIT License](https://opensource.org/licenses/MIT), see the
[LICENSE-CODE](LICENSE-CODE) file.

Microsoft, Windows, Microsoft Azure, and/or other Microsoft products and services referenced in the documentation
may be either trademarks or registered trademarks of Microsoft in the United States and/or other countries.
The licenses for this project do not grant you rights to use any Microsoft names, logos, or trademarks.
Microsoft's general trademark guidelines can be found at <http://go.microsoft.com/fwlink/?LinkID=254653>.

Privacy information can be found at <https://go.microsoft.com/fwlink/?LinkId=521839>

Microsoft and any contributors reserve all other rights, whether under their respective copyrights, patents,
or trademarks, whether by implication, estoppel, or otherwise.

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
  <a href="#readme-top" style="text-decoration: none; color: blue; font-weight: bold;">
    ↑ Back to Top ↑
  </a>
</p>
