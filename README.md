# 🌐 AI Web Search Gateway (FastAPI)

A lightweight, modular FastAPI server that connects AI language models to the internet — enabling dynamic web-augmented reasoning, search, and real-time knowledge retrieval.

Whether you're using a **local LLM with Ollama** or cloud models like **OpenAI**, this server bridges the gap between your model and the web.

---

## 🚀 Features

- ⚡ **FastAPI-powered API**: High-performance, asynchronous backend for AI inference and web interaction.
- 🌍 **Internet-enabled AI**: Integrates live web search and scraping for real-time knowledge.
- 🧠 **Model-agnostic**: Works with both **local LLMs via Ollama** and **cloud models like OpenAI**.
- 🔎 **Asynchronous scraping**: Fast, concurrent web retrieval with modern Python tools.
- 🔗 **Pluggable architecture**: Easily swap in different LLMs, retrieval, and search engines.

---

## 📦 Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — Modern, high-performance web framework
- **[Ollama](https://ollama.com/)** — For running local LLMs (e.g., LLaMA, Mistral)
- **[OpenAI API](https://platform.openai.com/)** — For hosted GPT-3.5/4 models
- **Playwright / aiohttp** — For async web scraping and browsing
- **FAISS / LangChain (optional)** — For embedding-based search and information extraction

---

## 🛠 Setup

### 1. Clone the repo

```bash
git clone https://github.com/iambatmanscape/ai-web-search-fastapi.git
cd ai-web-search-fastapi
