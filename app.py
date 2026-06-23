"""
IUE Gameplay — Online Soccer Scoreboard Portal
================================================
A single Streamlit app with two views:

  1. Coach View    — password protected. Controls the live match, the squad,
                     goal scorers, the season's match history, and what the
                     audience is allowed to see.
  2. Audience View — read-only. Shows the live scoreboard and (when the coach
                     enables them) the squad, past-match results table, and
                     the season's top scorers.

Football features
-----------------
  * Live scoreboard with team names, logos, location, kickoff time, status.
  * Squad list per team: player name, field position, leadership role
    (Captain / Vice-Captain), and photo.
  * Record a goal against a specific player — the score goes up and the
    scorer is logged for both the match and the season.
  * Completed matches are saved to a history table showing both logos, the
    score, the Win/Loss/Draw result, and league points (Win 3, Draw 1, Loss 0).
  * Season top-scorers table built automatically from logged goals.
  * Per-section audience visibility toggles.

State is shared between views (and across browsers) through a JSON file on
disk, so the audience screens follow the coach automatically.

Run locally (e.g. in PyCharm):
    streamlit run app.py

Author: Dr Vijesh Krishnamoorthy
"""

import base64
import json
import os
from datetime import datetime, time as dtime

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(APP_DIR, "match_state.json")

# Change this to whatever you want the coach password to be.
COACH_PASSWORD = "coach123"

# Football field positions (soccer).
POSITIONS = [
    "Goalkeeper (GK)",
    "Right Back (RB)",
    "Left Back (LB)",
    "Centre Back (CB)",
    "Defensive Midfield (CDM)",
    "Central Midfield (CM)",
    "Attacking Midfield (CAM)",
    "Right Winger (RW)",
    "Left Winger (LW)",
    "Striker (ST)",
    "Centre Forward (CF)",
    "Substitute",
]

# Leadership roles.
ROLES = ["Player", "Captain (C)", "Vice-Captain (VC)"]

# Default state used the very first time the app runs.
DEFAULT_STATE = {
    # --- live match ---
    "team_a_name": "Team A",
    "team_b_name": "Team B",
    "team_a_logo": "",
    "team_b_logo": "",
    "score_a": 0,
    "score_b": 0,
    "location": "Main Stadium",
    "kickoff": "16:00",
    "status": "Upcoming",          # Upcoming | Live | Finished
    "last_updated": "",
    # --- football data ---
    "players": [],                 # [{id, name, team, position, role, photo}]
    "current_goals": [],           # [{name, team, minute}] for the live match
    "match_history": [],           # [{id, date, ...scores..., result, points, scorers}]
    # --- audience visibility toggles ---
    "show_history_to_audience": True,
    "show_scorers_to_audience": True,
    "show_squad_to_audience": False,
}


# --------------------------------------------------------------------------- #
# State persistence helpers
# --------------------------------------------------------------------------- #
def load_state():
    """Read shared match state from disk, creating/healing it if needed."""
    if not os.path.exists(STATE_FILE):
        save_state(dict(DEFAULT_STATE))
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_STATE)
        merged.update(data)            # keep saved values, add any new keys
        return merged
    except (json.JSONDecodeError, OSError):
        save_state(dict(DEFAULT_STATE))
        return dict(DEFAULT_STATE)


def save_state(state):
    """Write shared match state to disk."""
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def image_to_base64(uploaded_file):
    """Convert an uploaded image into a base64 data-URI string for storage."""
    raw = uploaded_file.read()
    encoded = base64.b64encode(raw).decode("utf-8")
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64,{encoded}"


def new_id():
    """A simple unique id based on the current timestamp."""
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


# --------------------------------------------------------------------------- #
# Football logic helpers
# --------------------------------------------------------------------------- #
def points_for(score_a, score_b):
    """League points: win 3, draw 1, loss 0. Returns (points_a, points_b)."""
    if score_a > score_b:
        return 3, 0
    if score_b > score_a:
        return 0, 3
    return 1, 1


def result_text(state):
    """Human-readable Win/Loss/Draw line for the live match (if finished)."""
    a, b = state["score_a"], state["score_b"]
    ta, tb = state["team_a_name"], state["team_b_name"]
    if state["status"] != "Finished":
        return None
    if a > b:
        return f"🏆 {ta} WIN — {ta} {a} : {b} {tb}"
    if b > a:
        return f"🏆 {tb} WIN — {ta} {a} : {b} {tb}"
    return f"🤝 DRAW — {ta} {a} : {b} {tb}"


def players_for_team(state, team_key):
    """Return players assigned to 'A' or 'B'."""
    return [p for p in state["players"] if p.get("team") == team_key]


def compute_season_scorers(state):
    """Tally goals per player across saved history plus the live match."""
    events = []
    for m in state["match_history"]:
        events += m.get("scorers", [])
    events += state.get("current_goals", [])
    tally = {}
    for g in events:
        name = g.get("name")
        if name and name != "Unknown":
            tally[name] = tally.get(name, 0) + 1
    return dict(sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])))


def save_match_to_history(state):
    """Snapshot the current live match into the history table, then reset it."""
    pa, pb = points_for(state["score_a"], state["score_b"])
    if state["score_a"] > state["score_b"]:
        res = f"{state['team_a_name']} Win"
    elif state["score_b"] > state["score_a"]:
        res = f"{state['team_b_name']} Win"
    else:
        res = "Draw"
    entry = {
        "id": new_id(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "team_a_name": state["team_a_name"],
        "team_b_name": state["team_b_name"],
        "team_a_logo": state["team_a_logo"],
        "team_b_logo": state["team_b_logo"],
        "score_a": state["score_a"],
        "score_b": state["score_b"],
        "result": res,
        "points_a": pa,
        "points_b": pb,
        "scorers": list(state.get("current_goals", [])),
    }
    state["match_history"].insert(0, entry)
    state["current_goals"] = []
    state["score_a"] = 0
    state["score_b"] = 0
    state["status"] = "Upcoming"
    save_state(state)


# --------------------------------------------------------------------------- #
# Presentation helpers
# --------------------------------------------------------------------------- #
def logo_img(logo_data, size=90):
    """HTML for a logo/photo, or a ball emoji placeholder."""
    if logo_data:
        return (f"<img src='{logo_data}' style='height:{size}px;width:{size}px;"
                f"object-fit:contain;border-radius:8px'>")
    return (f"<div style='height:{size}px;line-height:{size}px;"
            f"font-size:{int(size * 0.4)}px;text-align:center'>⚽</div>")


def status_badge(status):
    colours = {"Upcoming": "#888", "Live": "#e53935", "Finished": "#1e88e5"}
    dot = "🔴 " if status == "Live" else ""
    colour = colours.get(status, "#888")
    return (f"<span style='background:{colour};color:white;padding:4px 14px;"
            f"border-radius:14px;font-size:14px;font-weight:600'>"
            f"{dot}{status.upper()}</span>")


def render_scoreboard(state):
    st.markdown(
        f"<div style='text-align:center;margin-bottom:6px'>"
        f"{status_badge(state['status'])}</div>",
        unsafe_allow_html=True,
    )
    col_a, col_mid, col_b = st.columns([3, 2, 3])
    with col_a:
        st.markdown(f"<div style='text-align:center'>{logo_img(state['team_a_logo'])}</div>",
                    unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;margin:6px 0'>{state['team_a_name']}</h3>",
                    unsafe_allow_html=True)
    with col_mid:
        st.markdown(
            f"<div style='text-align:center;font-size:54px;font-weight:800;"
            f"line-height:1.1'>{state['score_a']} : {state['score_b']}</div>",
            unsafe_allow_html=True,
        )
    with col_b:
        st.markdown(f"<div style='text-align:center'>{logo_img(state['team_b_logo'])}</div>",
                    unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;margin:6px 0'>{state['team_b_name']}</h3>",
                    unsafe_allow_html=True)

    st.markdown("---")
    info_l, info_r = st.columns(2)
    info_l.markdown(f"📍 **Location:** {state['location']}")
    info_r.markdown(f"⏰ **Kickoff:** {state['kickoff']}")

    res = result_text(state)
    if res:
        st.success(res)

    goals = state.get("current_goals", [])
    if goals:
        lines = []
        for g in goals:
            team = state["team_a_name"] if g["team"] == "A" else state["team_b_name"]
            minute = f" {g['minute']}'" if g.get("minute") else ""
            lines.append(f"⚽ {g['name']} ({team}){minute}")
        st.markdown("**Goal scorers:** " + "  •  ".join(lines))

    if state["last_updated"]:
        st.caption(f"Last updated: {state['last_updated']}")


def render_squad(state):
    """Show the squad grouped by team as cards."""
    any_shown = False
    for team_key, team_name in (("A", state["team_a_name"]), ("B", state["team_b_name"])):
        squad = players_for_team(state, team_key)
        if not squad:
            continue
        any_shown = True
        st.markdown(f"#### {team_name}")
        cols = st.columns(3)
        for i, p in enumerate(squad):
            with cols[i % 3]:
                photo = p.get("photo", "")
                badge = ""
                if p["role"] == "Captain (C)":
                    badge = " 🅒"
                elif p["role"] == "Vice-Captain (VC)":
                    badge = " (VC)"
                st.markdown(
                    f"<div style='text-align:center;border:1px solid #333;"
                    f"border-radius:10px;padding:8px;margin-bottom:8px'>"
                    f"{logo_img(photo, size=70)}"
                    f"<div style='font-weight:700;margin-top:4px'>{p['name']}{badge}</div>"
                    f"<div style='font-size:12px;color:#aaa'>{p['position']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
    if not any_shown:
        st.caption("No players added yet.")


def render_history_table(state):
    """An HTML results table with logos, score, result and points."""
    history = state["match_history"]
    if not history:
        st.caption("No completed matches yet.")
        return
    rows = ""
    for m in history:
        la = logo_img(m.get("team_a_logo", ""), size=34)
        lb = logo_img(m.get("team_b_logo", ""), size=34)
        rows += (
            "<tr style='border-bottom:1px solid #2a2a2a'>"
            f"<td style='padding:8px;white-space:nowrap'>{m.get('date', '')}</td>"
            f"<td style='padding:8px;text-align:right'>{m['team_a_name']}</td>"
            f"<td style='padding:8px'>{la}</td>"
            f"<td style='padding:8px;text-align:center;font-weight:800'>"
            f"{m['score_a']} : {m['score_b']}</td>"
            f"<td style='padding:8px'>{lb}</td>"
            f"<td style='padding:8px'>{m['team_b_name']}</td>"
            f"<td style='padding:8px;text-align:center'>{m['result']}</td>"
            f"<td style='padding:8px;text-align:center'>{m['points_a']}–{m['points_b']}</td>"
            "</tr>"
        )
    table = (
        "<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse'>"
        "<tr style='text-align:left;color:#aaa;border-bottom:2px solid #444'>"
        "<th style='padding:8px'>Date</th>"
        "<th style='padding:8px;text-align:right'>Home</th><th></th>"
        "<th style='padding:8px;text-align:center'>Score</th><th></th>"
        "<th style='padding:8px'>Away</th>"
        "<th style='padding:8px;text-align:center'>Result</th>"
        "<th style='padding:8px;text-align:center'>Pts</th></tr>"
        f"{rows}</table></div>"
    )
    st.markdown(table, unsafe_allow_html=True)


def render_top_scorers(state):
    tally = compute_season_scorers(state)
    if not tally:
        st.caption("No goals recorded yet this season.")
        return
    rank = 1
    rows = ""
    for name, goals in tally.items():
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
        rows += (
            "<tr style='border-bottom:1px solid #2a2a2a'>"
            f"<td style='padding:6px 10px'>{medal}</td>"
            f"<td style='padding:6px 10px'>{name}</td>"
            f"<td style='padding:6px 10px;text-align:center;font-weight:700'>{goals}</td>"
            "</tr>"
        )
        rank += 1
    st.markdown(
        "<table style='width:100%;border-collapse:collapse'>"
        "<tr style='color:#aaa;border-bottom:2px solid #444'>"
        "<th style='padding:6px 10px;text-align:left'>#</th>"
        "<th style='padding:6px 10px;text-align:left'>Player</th>"
        "<th style='padding:6px 10px;text-align:center'>Goals</th></tr>"
        f"{rows}</table>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Coach view
# --------------------------------------------------------------------------- #
def coach_view():
    st.subheader("🎽 Coach Control Panel")

    if not st.session_state.get("coach_authed", False):
        pwd = st.text_input("Enter coach password", type="password")
        if st.button("Unlock"):
            if pwd == COACH_PASSWORD:
                st.session_state["coach_authed"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.info("Coach Login — password protected.")
        return

    state = load_state()

    tabs = st.tabs([
        "🎮 Live Match",
        "⚽ Record Goal",
        "👥 Squad",
        "📋 Match History",
        "🏆 Top Scorers",
        "👁️ Audience Settings",
    ])

    # ===================== TAB 1: LIVE MATCH ============================== #
    with tabs[0]:
        render_scoreboard(state)
        st.markdown("## ")

        with st.expander("⚙️ Team setup (names & logos)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                state["team_a_name"] = st.text_input("Home team name",
                                                     value=state["team_a_name"])
                la = st.file_uploader("Home logo", type=["png", "jpg", "jpeg"], key="logo_a")
                if la is not None:
                    state["team_a_logo"] = image_to_base64(la)
            with c2:
                state["team_b_name"] = st.text_input("Away team name",
                                                     value=state["team_b_name"])
                lb = st.file_uploader("Away logo", type=["png", "jpg", "jpeg"], key="logo_b")
                if lb is not None:
                    state["team_b_logo"] = image_to_base64(lb)

        with st.expander("📍 Match details (location, time, status)", expanded=True):
            state["location"] = st.text_input("Game location", value=state["location"])
            try:
                hh, mm = map(int, state["kickoff"].split(":"))
                default_time = dtime(hh, mm)
            except (ValueError, AttributeError):
                default_time = dtime(16, 0)
            kickoff = st.time_input("Kickoff (starting) time", value=default_time)
            state["kickoff"] = kickoff.strftime("%H:%M")
            state["status"] = st.selectbox(
                "Match status", ["Upcoming", "Live", "Finished"],
                index=["Upcoming", "Live", "Finished"].index(state["status"]),
            )

        st.markdown("### Quick score adjust")
        st.caption("Use the **Record Goal** tab to also log who scored. "
                   "These buttons only change the number.")
        sc1, sc2 = st.columns(2)
        for col, key, team in ((sc1, "score_a", "A"), (sc2, "score_b", "B")):
            with col:
                tname = state["team_a_name"] if team == "A" else state["team_b_name"]
                st.markdown(f"**{tname}**")
                b1, b2, b3 = st.columns(3)
                if b1.button("➖", key=f"{key}_minus"):
                    state[key] = max(0, state[key] - 1)
                    save_state(state)
                    st.rerun()
                b2.markdown(
                    f"<div style='text-align:center;font-size:30px;font-weight:700'>"
                    f"{state[key]}</div>", unsafe_allow_html=True)
                if b3.button("➕", key=f"{key}_plus"):
                    state[key] += 1
                    save_state(state)
                    st.rerun()

        st.markdown("---")
        a1, a2, a3 = st.columns(3)
        if a1.button("💾 Save changes", type="primary"):
            save_state(state)
            st.success("Saved. Audience screens will update.")
        if a2.button("🏁 Finish & save to history"):
            save_match_to_history(state)
            st.success("Match saved to history and reset for the next game.")
            st.rerun()
        if a3.button("🔒 Lock panel"):
            st.session_state["coach_authed"] = False
            st.rerun()

    # ===================== TAB 2: RECORD GOAL ============================ #
    with tabs[1]:
        st.markdown("### ⚽ Record a goal")
        st.caption("Pick the team and the player who scored. The score goes up "
                   "and the goal is added to the season tally.")
        team_label = st.radio(
            "Which team scored?",
            [state["team_a_name"], state["team_b_name"]],
            horizontal=True,
        )
        team_key = "A" if team_label == state["team_a_name"] else "B"

        squad = players_for_team(state, team_key)
        names = [p["name"] for p in squad]
        options = names + ["Other / not in squad", "Unknown (own goal etc.)"]
        choice = st.selectbox("Who scored?", options)

        manual_name = ""
        if choice == "Other / not in squad":
            manual_name = st.text_input("Enter scorer's name")
        minute = st.number_input("Minute (optional)", min_value=0, max_value=130, value=0)

        if st.button("⚽ Add goal", type="primary"):
            if choice == "Unknown (own goal etc.)":
                scorer = "Unknown"
            elif choice == "Other / not in squad":
                scorer = manual_name.strip() or "Unknown"
            else:
                scorer = choice
            state.setdefault("current_goals", []).append(
                {"name": scorer, "team": team_key,
                 "minute": int(minute) if minute else None})
            state["score_a" if team_key == "A" else "score_b"] += 1
            if state["status"] == "Upcoming":
                state["status"] = "Live"
            save_state(state)
            st.success(f"Goal recorded for {scorer}.")
            st.rerun()

        st.markdown("#### Goals so far this match")
        goals = state.get("current_goals", [])
        if not goals:
            st.caption("No goals yet.")
        else:
            for idx, g in enumerate(goals):
                tname = state["team_a_name"] if g["team"] == "A" else state["team_b_name"]
                mins = f" {g['minute']}'" if g.get("minute") else ""
                gc1, gc2 = st.columns([5, 1])
                gc1.markdown(f"⚽ **{g['name']}** — {tname}{mins}")
                if gc2.button("🗑️", key=f"delgoal_{idx}"):
                    skey = "score_a" if g["team"] == "A" else "score_b"
                    state[skey] = max(0, state[skey] - 1)
                    goals.pop(idx)
                    save_state(state)
                    st.rerun()

    # ===================== TAB 3: SQUAD ================================= #
    with tabs[2]:
        st.markdown("### 👥 Squad management")
        st.caption("Add players before the match: name, position, leadership "
                   "role and photo. Players appear in the Record Goal list.")

        with st.expander("➕ Add a player", expanded=True):
            ac1, ac2 = st.columns(2)
            with ac1:
                p_name = st.text_input("Player name", key="add_pname")
                p_team = st.selectbox(
                    "Team", [state["team_a_name"], state["team_b_name"]], key="add_pteam")
                p_role = st.selectbox("Leadership role", ROLES, key="add_prole")
            with ac2:
                p_pos = st.selectbox("Field position", POSITIONS, key="add_ppos")
                p_photo = st.file_uploader(
                    "Photo (optional)", type=["png", "jpg", "jpeg"], key="add_pphoto")
            if st.button("Add player", type="primary"):
                if p_name.strip():
                    tkey = "A" if p_team == state["team_a_name"] else "B"
                    state["players"].append({
                        "id": new_id(),
                        "name": p_name.strip(),
                        "team": tkey,
                        "position": p_pos,
                        "role": p_role,
                        "photo": image_to_base64(p_photo) if p_photo else "",
                    })
                    save_state(state)
                    st.success(f"Added {p_name}.")
                    st.rerun()
                else:
                    st.error("Please enter a player name.")

        st.markdown("#### Current squad")
        render_squad(state)

        if state["players"]:
            with st.expander("✏️ Edit or delete a player"):
                labels = {
                    f"{p['name']} — "
                    f"{state['team_a_name'] if p['team'] == 'A' else state['team_b_name']}"
                    f" ({p['position']})": p["id"]
                    for p in state["players"]
                }
                pick = st.selectbox("Select player", list(labels.keys()))
                pid = labels[pick]
                player = next(p for p in state["players"] if p["id"] == pid)

                e1, e2 = st.columns(2)
                with e1:
                    player["name"] = st.text_input(
                        "Name", value=player["name"], key="edit_name")
                    player["role"] = st.selectbox(
                        "Role", ROLES, index=ROLES.index(player["role"]), key="edit_role")
                with e2:
                    player["position"] = st.selectbox(
                        "Position", POSITIONS,
                        index=POSITIONS.index(player["position"]), key="edit_pos")
                    new_photo = st.file_uploader(
                        "Replace photo", type=["png", "jpg", "jpeg"], key="edit_photo")
                    if new_photo is not None:
                        player["photo"] = image_to_base64(new_photo)

                ec1, ec2 = st.columns(2)
                if ec1.button("💾 Save player"):
                    save_state(state)
                    st.success("Player updated.")
                    st.rerun()
                if ec2.button("🗑️ Delete player"):
                    state["players"] = [p for p in state["players"] if p["id"] != pid]
                    save_state(state)
                    st.success("Player deleted.")
                    st.rerun()

    # ===================== TAB 4: MATCH HISTORY ========================= #
    with tabs[3]:
        st.markdown("### 📋 Match history")
        st.caption("Completed matches with logos, score, result and points "
                   "(Win 3 · Draw 1 · Loss 0).")
        render_history_table(state)

        with st.expander("➕ Add a past match manually"):
            hc1, hc2 = st.columns(2)
            with hc1:
                h_a = st.text_input("Home team", value=state["team_a_name"], key="h_a")
                h_sa = st.number_input("Home score", min_value=0, value=0, key="h_sa")
                h_logo_a = st.file_uploader("Home logo", type=["png", "jpg", "jpeg"], key="h_la")
            with hc2:
                h_b = st.text_input("Away team", value=state["team_b_name"], key="h_b")
                h_sb = st.number_input("Away score", min_value=0, value=0, key="h_sb")
                h_logo_b = st.file_uploader("Away logo", type=["png", "jpg", "jpeg"], key="h_lb")
            h_date = st.date_input("Match date", key="h_date")
            if st.button("Add to history"):
                pa, pb = points_for(h_sa, h_sb)
                res = (f"{h_a} Win" if h_sa > h_sb else
                       f"{h_b} Win" if h_sb > h_sa else "Draw")
                state["match_history"].insert(0, {
                    "id": new_id(),
                    "date": h_date.strftime("%Y-%m-%d"),
                    "team_a_name": h_a, "team_b_name": h_b,
                    "team_a_logo": image_to_base64(h_logo_a) if h_logo_a else "",
                    "team_b_logo": image_to_base64(h_logo_b) if h_logo_b else "",
                    "score_a": int(h_sa), "score_b": int(h_sb),
                    "result": res, "points_a": pa, "points_b": pb, "scorers": [],
                })
                save_state(state)
                st.success("Match added to history.")
                st.rerun()

        if state["match_history"]:
            with st.expander("✏️ Edit or delete a past match"):
                hlabels = {
                    f"{m['date']}: {m['team_a_name']} {m['score_a']}-{m['score_b']} "
                    f"{m['team_b_name']}": m["id"]
                    for m in state["match_history"]
                }
                hpick = st.selectbox("Select match", list(hlabels.keys()))
                mid = hlabels[hpick]
                match = next(m for m in state["match_history"] if m["id"] == mid)

                m1, m2 = st.columns(2)
                with m1:
                    match["score_a"] = st.number_input(
                        f"{match['team_a_name']} score", min_value=0,
                        value=int(match["score_a"]), key="edit_sa")
                with m2:
                    match["score_b"] = st.number_input(
                        f"{match['team_b_name']} score", min_value=0,
                        value=int(match["score_b"]), key="edit_sb")

                mc1, mc2 = st.columns(2)
                if mc1.button("💾 Save match"):
                    pa, pb = points_for(match["score_a"], match["score_b"])
                    match["points_a"], match["points_b"] = pa, pb
                    match["result"] = (
                        f"{match['team_a_name']} Win" if match["score_a"] > match["score_b"]
                        else f"{match['team_b_name']} Win" if match["score_b"] > match["score_a"]
                        else "Draw")
                    save_state(state)
                    st.success("Match updated.")
                    st.rerun()
                if mc2.button("🗑️ Delete match"):
                    state["match_history"] = [
                        m for m in state["match_history"] if m["id"] != mid]
                    save_state(state)
                    st.success("Match deleted.")
                    st.rerun()

    # ===================== TAB 5: TOP SCORERS =========================== #
    with tabs[4]:
        st.markdown("### 🏆 Season top scorers")
        st.caption("Built automatically from every goal you log "
                   "(live match + saved history).")
        render_top_scorers(state)

    # ===================== TAB 6: AUDIENCE SETTINGS ===================== #
    with tabs[5]:
        st.markdown("### 👁️ What can the audience see?")
        st.caption("The live scoreboard is always visible. Toggle the extras below.")
        state["show_history_to_audience"] = st.toggle(
            "Show past matches table", value=state["show_history_to_audience"])
        state["show_scorers_to_audience"] = st.toggle(
            "Show season top scorers", value=state["show_scorers_to_audience"])
        state["show_squad_to_audience"] = st.toggle(
            "Show squad / line-up", value=state["show_squad_to_audience"])
        if st.button("💾 Save audience settings", type="primary"):
            save_state(state)
            st.success("Audience settings saved.")


# --------------------------------------------------------------------------- #
# Audience view
# --------------------------------------------------------------------------- #
def audience_view():
    st_autorefresh(interval=5000, key="audience_refresh")
    state = load_state()

    tab_names = ["📺 Live"]
    if state.get("show_squad_to_audience"):
        tab_names.append("👥 Squad")
    if state.get("show_history_to_audience"):
        tab_names.append("📋 Past Matches")
    if state.get("show_scorers_to_audience"):
        tab_names.append("🏆 Top Scorers")

    tabs = st.tabs(tab_names)
    idx = 0

    with tabs[idx]:
        st.subheader("📺 Live Scoreboard")
        render_scoreboard(state)
        st.caption("This page refreshes automatically every few seconds.")
    idx += 1

    if state.get("show_squad_to_audience"):
        with tabs[idx]:
            st.subheader("👥 Squad")
            render_squad(state)
        idx += 1

    if state.get("show_history_to_audience"):
        with tabs[idx]:
            st.subheader("📋 Past Matches")
            render_history_table(state)
        idx += 1

    if state.get("show_scorers_to_audience"):
        with tabs[idx]:
            st.subheader("🏆 Season Top Scorers")
            render_top_scorers(state)
        idx += 1


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    st.set_page_config(page_title="IUE Gameplay — Soccer Scoreboard",
                       page_icon="⚽", layout="centered")
    st.markdown(
        "<h1 style='text-align:center'>⚽ IUE Gameplay</h1>"
        "<p style='text-align:center;color:#888'>Online Soccer Scoreboard Portal</p>",
        unsafe_allow_html=True,
    )
    view = st.sidebar.radio("Select view", ["Audience View", "Coach View"])
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Audience View is public and read-only.\n\n"
        "Coach View is password protected and controls the scoreboard, "
        "squad, goals and match history.")
    if view == "Coach View":
        coach_view()
    else:
        audience_view()


if __name__ == "__main__":
    main()
