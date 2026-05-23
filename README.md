# Diet Recommendation System - Streamlit Ready

This package is prepared for **Streamlit Community Cloud** deployment.

## What was changed
- Kept only the files needed for Streamlit hosting.
- Removed the extra fallback dataset to make the repo lighter.
- Added a lightweight `requirements.txt` for Streamlit Cloud.
- Switched the chatbot to a deployment-safe fallback by default.
- Added proper `.streamlit/config.toml` inside the app folder.

## Folder structure
- `Streamlit_Frontend/Hello.py` → main Streamlit entrypoint
- `Data/dataset_enhanced.csv` → compressed recipe dataset
- `requirements.txt` → Python dependencies

## Deploy steps
1. Create a new GitHub repository.
2. Upload everything from this folder to that repository.
3. Go to Streamlit Community Cloud.
4. Click **Create app**.
5. Choose your GitHub repo.
6. Set **Main file path** to:
   `Streamlit_Frontend/Hello.py`
7. Deploy.

## Local run
From the project root:

```bash
pip install -r requirements.txt
streamlit run Streamlit_Frontend/Hello.py
```

## Notes
- First load can take time because the dataset is large.
- The deployed version uses the lightweight FAQ chatbot.
- If you want the local TinyLlama chatbot, set `USE_LOCAL_LLM=1` and install `torch` + `transformers` yourself.
