# Step-by-step: Deploy Climbing Tracker to Render

Do these steps in order.

---

## Step 1: Put your project on GitHub

1. Open a browser and go to **https://github.com**. Log in or create an account.

2. Create a new repository:
   - Click the **+** (top right) → **New repository**.
   - Repository name: e.g. `climbing-tracker`.
   - Leave “Add a README” **unchecked** (you already have files).
   - Click **Create repository**.

3. In Terminal, run these commands (replace `YOUR_USERNAME` and `climbing-tracker` with your GitHub username and repo name if different):

   ```bash
   cd "/Users/beni/Desktop/Climbing Technique Tracker 2/Climbing_Tracker"
   git add .
   git status
   git commit -m "Add Render deployment"   # if you have uncommitted changes
   git remote add origin https://github.com/YOUR_USERNAME/climbing-tracker.git
   git branch -M main
   git push -u origin main
   ```

   If `git remote add origin` says “remote origin already exists”, run only:

   ```bash
   git push -u origin main
   ```

4. Refresh the repo page on GitHub. You should see all your project files.

---

## Step 2: Sign up / log in on Render

1. Go to **https://render.com**.
2. Click **Get Started** (or **Log in** if you have an account).
3. Choose **Sign up with GitHub** and authorize Render to access your GitHub account.

---

## Step 3: Create the app from the Blueprint

1. In the Render dashboard, click **New +** → **Blueprint**.

2. Connect the repo:
   - If asked, click **Connect account** or **Configure account** and select your GitHub account.
   - Find **Climbing_Tracker** (or your repo name) in the list and click **Connect** next to it.

3. Render will show a screen that detected `render.yaml` and list two services:
   - **climbing-tracker-api**
   - **climbing-tracker-frontend**

4. For **VITE_API_URL** (under the frontend service), it will say “Sync” or “Add value”. You’ll set this in the next section after the first deploy, so you can leave it for now or skip.

5. Click **Apply** (bottom of the page).

6. Wait for both services to build and deploy (several minutes). The backend installs Python deps and downloads the pose model, so it takes longer. Status will change from “Building” to “Live” when done.

---

## Step 4: Get your backend URL

1. On the Render dashboard, click the service **climbing-tracker-api**.
2. At the top you’ll see a URL like:  
   **https://climbing-tracker-api.onrender.com**  
   Copy that URL (you’ll use it in the next step).

---

## Step 5: Point the frontend at the backend

1. In the Render dashboard, click the service **climbing-tracker-frontend**.

2. Open **Environment** in the left sidebar.

3. Add an environment variable:
   - Click **Add Environment Variable**.
   - **Key:** `VITE_API_URL`
   - **Value:** paste the backend URL you copied (e.g. `https://climbing-tracker-api.onrender.com`) — **no slash at the end**.

4. Click **Save Changes**.

5. Trigger a new deploy so the frontend is built with this URL:
   - Go to **Manual Deploy** (left sidebar).
   - Click **Deploy latest commit**.
   - Wait until the deploy status is **Live**.

---

## Step 6: Fix CORS (if the app can’t reach the API)

1. On the dashboard, click **climbing-tracker-frontend** and copy its URL (e.g. **https://climbing-tracker-frontend.onrender.com**).

2. Click **climbing-tracker-api** → **Environment** → **Add Environment Variable**:
   - **Key:** `CORS_ORIGINS`
   - **Value:** the frontend URL (e.g. `https://climbing-tracker-frontend.onrender.com`).

3. **Save Changes**. Render will redeploy the API automatically.

You only need this if the site loads but “Analyze video” fails with a CORS or network error in the browser.

---

## Step 7: Use your live app

1. Open the **climbing-tracker-frontend** URL in your browser (from the Render dashboard).
2. Upload a video and click **Analyze video**.
3. Backend API docs (for testing the API directly): open the **climbing-tracker-api** URL and add `/docs`, e.g.  
   **https://climbing-tracker-api.onrender.com/docs**

---

## Quick reference

| What              | Where |
|-------------------|--------|
| Your live app     | Render dashboard → climbing-tracker-frontend → copy URL |
| API docs          | `https://<your-api-url>.onrender.com/docs` |
| Change env vars   | Service → Environment → edit / add → Save (frontend needs Manual Deploy after changing `VITE_API_URL`) |

**Free tier:** The backend may sleep after ~15 minutes of no use. The first request after that can take 30–60 seconds to respond.
