
# Deploy Fully Online — No Local Python Required

Recommended V1 hosting: **Streamlit Community Cloud**.

After deployment, the application runs in Streamlit's cloud environment. Your own computer
only opens the web page.

## Browser-only deployment

### Step 1 — Put the project in GitHub

1. Sign in to GitHub.
2. Create a new repository, for example:
   `crypto-synthetic-simulator`
3. Upload the contents of this project folder to the repository.
4. Confirm that `streamlit_app.py` and `requirements.txt` are at the repository root.

You do not need to run Python locally.

### Step 2 — Open Streamlit Community Cloud

1. Go to `share.streamlit.io`.
2. Sign in / continue with GitHub.
3. Connect the GitHub repository if requested.
4. Click **Create app**.
5. Choose **Yup, I have an app**.
6. Select:
   - Repository: your new GitHub repository
   - Branch: `main`
   - App file / entrypoint: `streamlit_app.py`
7. In Advanced settings, Python 3.11 is a safe choice for this V1 dependency set.
8. Click **Deploy**.

Streamlit reads `requirements.txt` and installs the Python dependencies in the cloud.

## What runs online?

- Synthetic dataset generation
- Transaction/wallet/scenario tables
- Network graph generation
- EDA charts
- Logistic Regression / Random Forest / XGBoost training
- Dataset ZIP creation

None of those tasks require your laptop CPU after deployment.

## V1 storage behaviour

Generated data is held in the app session. It may disappear when the cloud instance restarts
or the session expires. Use **Download Data** to save a run.

For a later version, add managed persistent services such as:

- Memgraph Cloud for a persistent graph database
- A managed SQL database for transactions/metadata
- Cloud object storage for generated CSV/Parquet files

## Updating the online app

Push a change to the connected GitHub repository. Streamlit Community Cloud detects the
repository update and refreshes the deployed app.

## If deployment fails

Open the Streamlit app logs. Most first-deploy errors come from dependency installation.
Keep `requirements.txt` at the repository root next to `streamlit_app.py`.
