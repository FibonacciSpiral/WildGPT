# 🐾 WildGPT

WildGPT is a desktop chat interface for talking to open large language models — the kind you can find on [Hugging Face](https://huggingface.co/).  
It’s written in **Python** with **PyQt5**, built to feel fast, responsive, and a little more *real* than most polished corporate AI apps.

Unlike ChatGPT, WildGPT doesn't have strict guardrails. It does depend on which model you select, but the guardrails are far less than on OpenAI, allowing adults a more free experience.

---

## ✨ What Makes It Cool
- 🧠 **Pick your own brain:** connect to different Hugging Face LLMs straight from the app.  
- 💬 **Custom personalities:** define how your AI should behave — poetic, sarcastic, stoic, flirty, teacherly, whatever you like.  
- 🎨 **Clean PyQt5 UI:** scrollable, fluid chat bubbles that resize to the text.  
- ⚙️ **Thread-safe and responsive:** no frozen windows, no weird lag — the app handles background requests gracefully.  
- 🪶 **Lightweight:** no server-side nonsense. It’s all local logic with API calls to the model host.  

---

## 🧩 The Interface
The UI is simple on purpose:
- placeholder for image soon to arrive...

Each message bubble adapts to its text length and supports scrolling inside long replies.  
The layout is fully dynamic — it feels natural, not boxed-in.

---

## ⚙️ How to Run It
You’ll need **Python 3.10+** and a Hugging Face API key.

```bash
git clone https://github.com/FibonacciSpiral/WildGPT.git
cd WildGPT
pip install -r requirements.txt
python wildgpt.py
