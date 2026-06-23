<<<<<<< HEAD
# ⚽ IUE Gameplay — Online Soccer Scoreboard Portal

A free, web-based soccer scoreboard built with **Python + Streamlit**.
It has two views that share a live scoreboard:

| View | Who it's for | What it does |
|------|--------------|--------------|
| **Coach View** | Match official (password protected) | Update scores, team names & logos, location, kickoff time, and match status (Upcoming / Live / Finished). |
| **Audience View** | Public spectators | Read-only live scoreboard that auto-refreshes every few seconds and shows the Win / Draw announcement. |

The coach's updates are written to a small `match_state.json` file, so every
audience screen sees the same live score.

---

## 1. Run & test in PyCharm

1. Open this folder in **PyCharm** (`File → Open` → select the `IUEGameplay` folder).
2. Let PyCharm create a virtual environment, or use your existing one.
3. Open the **Terminal** tab at the bottom of PyCharm and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   streamlit run app.py
   ```
5. Your browser opens at `http://localhost:8501`.
   - Use the **sidebar** to switch between Audience View and Coach View.
   - Coach password is **`coach123`** (change it near the top of `app.py`).

> Tip: to test both views together, open the app in two browser tabs — set one
> to Coach View and one to Audience View, then update the score and watch the
> audience tab refresh.

---

## 2. Host free online with Streamlit Community Cloud

1. Push this folder to a **GitHub repository** (see below).
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and sign in with GitHub.
3. Click **New app**, choose your repo, set the main file to **`app.py`**, and click **Deploy**.
4. You get a public URL you can share with the audience. It's free for public repos.

### Pushing the code to GitHub (manual)
From this folder, in Git Bash or PyCharm's terminal:
```bash
git init
git add .
git commit -m "Add IUE Gameplay soccer scoreboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```
If the folder is already a clone of your repo, you only need the last four lines
(`add`, `commit`, and `push`).

---

## 3. Change the coach password

Open `app.py` and edit this line near the top:
```python
COACH_PASSWORD = "coach123"
```

---

## Files

```
IUEGameplay/
├── app.py                 # the whole application
├── requirements.txt       # Python dependencies
├── README.md              # this file
└── .streamlit/
    └── config.toml        # dark theme + server settings
```

`match_state.json` is created automatically the first time you run the app.

---

*Built for the Innovative University of Enga (IUE).*
=======
# IUEGameplay
This is an online gameplay score board personalized for Innovation University of Enga, Department of Sports.
>>>>>>> 4fa319c83cbb8d61997f5ae2e44c8c05a829e92f
