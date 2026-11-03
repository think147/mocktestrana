# Mock Test Flask App

Simple Flask app that loads a question bank from `questions.json` and generates a 100-question mock test randomly.

Run:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000/ in your browser and click "Start Mock Test".

Notes:
- If the question bank has fewer than 100 questions the app samples with replacement to reach 100.
