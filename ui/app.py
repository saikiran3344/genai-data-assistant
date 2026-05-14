import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="GenAI Data Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  .token-bar-wrap { background: var(--background-color); border: 0.5px solid #ddd;
                    border-radius: 8px; height: 10px; width: 100%; margin: 6px 0 12px; }
  .token-bar-fill { height: 10px; border-radius: 8px; background: #1D9E75;
                    transition: width 0.4s; }
  .token-bar-low  { background: #E24B4A; }
  .admin-badge { background: #EEEDFE; color: #3C3489; font-size: 11px;
                 padding: 2px 8px; border-radius: 12px; font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ────────────────────────────────────

def api(method, path, **kwargs):
    headers = {}
    if "token" in st.session_state and st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    try:
        fn  = getattr(requests, method)
        res = fn(f"{API_URL}{path}", headers=headers,
                 timeout=120, **kwargs)
        print(f"Response status: {res.status_code}")  # add this
        print(f"Response body: {res.text[:200]}")
        return res.json()
    except Exception as e:
        return {"error": str(e)}


def is_logged_in():
    return bool(st.session_state.get("token"))


def is_admin():
    return st.session_state.get("role") == "admin"


# ── Init session state ──────────────────────────────────

for key, default in {
    "token":            None,
    "role":             None,
    "email":            None,
    "tokens_remaining": 0,
    "messages":         [],
    "page":             "chat"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Auth page ───────────────────────────────────────────

def show_auth_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## GenAI Data Assistant")
        st.markdown("---")
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            email    = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password",
                                      key="login_password")
            if st.button("Login", type="primary",
                         use_container_width=True):
                if email and password:
                    res = api("post", "/login",
                              json={"email": email,
                                    "password": password})
                    if "access_token" in res:
                        st.session_state.token            = res["access_token"]
                        st.session_state.role             = res["role"]
                        st.session_state.email            = email
                        st.session_state.tokens_remaining = res["tokens_remaining"]
                        st.rerun()
                    else:
                        st.error(res.get("detail",
                                         "Login failed"))
                else:
                    st.warning("Enter email and password")

        with tab2:
            new_email    = st.text_input("Email", key="reg_email")
            new_password = st.text_input("Password (min 6 chars)",
                                          type="password",
                                          key="reg_password")
            if st.button("Create account", use_container_width=True):
                if new_email and new_password:
                    res = api("post", "/register",
                              json={"email":    new_email,
                                    "password": new_password})
                    if "message" in res and "error" not in res:
                        st.success(
                            f"Account created. You get "
                            f"{res.get('tokens_remaining', 100)} "
                            f"free tokens. Please login."
                        )
                    else:
                        st.error(res.get("detail", "Registration failed"))
                else:
                    st.warning("Fill in all fields")


# ── Sidebar ─────────────────────────────────────────────

def show_sidebar():
    with st.sidebar:
        st.markdown(f"**{st.session_state.email}**")
        if is_admin():
            st.markdown('<span class="admin-badge">Admin</span>',
                        unsafe_allow_html=True)

        st.markdown("---")

        # Token meter
        remaining = st.session_state.tokens_remaining
        pct       = min(100, max(0, remaining))
        bar_class = "token-bar-low" if remaining < 20 else ""
        st.markdown(
            f"**Tokens remaining: {remaining}**"
            f'<div class="token-bar-wrap">'
            f'<div class="token-bar-fill {bar_class}" '
            f'style="width:{pct}%"></div></div>',
            unsafe_allow_html=True
        )

        if remaining < 20:
            st.warning("Running low on tokens")
            if st.button("Request more tokens",
                         use_container_width=True):
                st.session_state.page = "request_tokens"
                st.rerun()

        st.markdown("---")

        # Navigation
        if st.button("Chat", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()

        if is_admin():
            if st.button("Admin dashboard",
                         use_container_width=True):
                st.session_state.page = "admin"
                st.rerun()

        st.markdown("---")

        # File upload
        st.markdown("**Upload file**")
        uploaded = st.file_uploader(
            "CSV, Excel, or PDF",
            type=["csv", "xlsx", "pdf"],
            label_visibility="collapsed"
        )
        if uploaded:
            if st.button("Process file", type="primary",
                         use_container_width=True):
                with st.spinner("Processing..."):
                    res = api(
                        "post", "/upload",
                        files={"file": (uploaded.name,
                                        uploaded.getvalue(),
                                        uploaded.type)}
                    )
                if "error" in res:
                    st.error(res["error"])
                else:
                    st.success(res.get("message", "Done"))

        st.markdown("---")

        if st.button("Clear conversation",
                     use_container_width=True):
            api("post", "/clear-history")
            st.session_state.messages = []
            st.rerun()

        if st.button("Logout", use_container_width=True):
            for key in ["token", "role", "email",
                        "tokens_remaining", "messages"]:
                st.session_state[key] = None \
                    if key != "messages" else []
            st.session_state.page = "chat"
            st.rerun()


# ── Chat page ────────────────────────────────────────────

def show_chat_page():
    st.markdown("## GenAI Data Assistant")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                with st.expander("View sources"):
                    for src in msg["sources"]:
                        st.caption(
                            f"File: {src.get('source','?')} | "
                            f"Score: {src.get('score', 0):.4f}"
                        )

    if prompt := st.chat_input("Ask a question about your data..."):
        if st.session_state.tokens_remaining <= 0:
            st.error(
                "You have no tokens remaining. "
                "Request more from admin."
            )
            st.stop()

        st.session_state.messages.append({
            "role": "user", "content": prompt
        })
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                res = api("post", "/ask",
                          json={"question": prompt})

            if "error" in res:
                st.error(res["error"])
                answer  = res["error"]
                sources = []
            elif "detail" in res:
                st.error(res["detail"])
                answer  = res["detail"]
                sources = []
            else:
                answer  = res.get("answer", "")
                sources = res.get("sources", [])
                st.session_state.tokens_remaining = \
                    res.get("tokens_remaining",
                            st.session_state.tokens_remaining - 1)
                st.write(answer)
                if sources:
                    with st.expander("View sources"):
                        for src in sources:
                            st.caption(
                                f"File: {src.get('source','?')} | "
                                f"Score: {src.get('score', 0):.4f}"
                            )

        st.session_state.messages.append({
            "role":    "assistant",
            "content": answer,
            "sources": sources
        })
        st.rerun()


# ── Request tokens page ──────────────────────────────────

def show_request_tokens_page():
    st.markdown("## Request more tokens")
    st.info(
        f"You have {st.session_state.tokens_remaining} tokens "
        f"remaining. Describe why you need more."
    )
    message  = st.text_area("Why do you need more tokens?",
                             placeholder="I need more tokens to...")
    amount   = st.slider("Tokens requested", 50, 500, 100, step=50)

    if st.button("Submit request", type="primary"):
        if message.strip():
            res = api("post", "/request-tokens",
                      json={"message":          message,
                            "tokens_requested":  amount})
            if "message" in res:
                st.success(res["message"])
                st.session_state.page = "chat"
                st.rerun()
            else:
                st.error(res.get("detail", "Failed to submit"))
        else:
            st.warning("Please explain why you need more tokens")

    if st.button("Back to chat"):
        st.session_state.page = "chat"
        st.rerun()


# ── Admin dashboard ──────────────────────────────────────

def show_admin_page():
    st.markdown("## Admin dashboard")

    tab1, tab2, tab3 = st.tabs([
        "Token requests", "All users", "Allocate tokens"
    ])

    # ── Pending requests ──
    with tab1:
        st.markdown("### Pending token requests")
        res = api("get", "/admin/requests")
        requests_list = res.get("requests", [])

        if not requests_list:
            st.info("No pending requests.")
        else:
            for req in requests_list:
                with st.container():
                    st.markdown(
                        f"**{req['email']}** — "
                        f"Requesting {req['tokens_requested']} tokens"
                    )
                    st.caption(f"Message: {req['message']}")
                    st.caption(f"Submitted: {req['requested_at']}")

                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        tokens_to_add = st.number_input(
                            "Tokens to approve",
                            min_value=10,
                            max_value=1000,
                            value=req["tokens_requested"],
                            key=f"approve_{req['id']}"
                        )
                    with col2:
                        if st.button("Approve",
                                     key=f"approve_btn_{req['id']}",
                                     type="primary"):
                            r = api(
                                "post",
                                f"/admin/requests/{req['id']}/approve",
                                json={"tokens_to_add": tokens_to_add}
                            )
                            st.success(r.get("message", "Approved"))
                            st.rerun()
                    with col3:
                        if st.button("Reject",
                                     key=f"reject_btn_{req['id']}"):
                            r = api(
                                "post",
                                f"/admin/requests/{req['id']}/reject"
                            )
                            st.warning(r.get("message", "Rejected"))
                            st.rerun()
                    st.markdown("---")

    # ── All users ──
    with tab2:
        st.markdown("### All users")
        res   = api("get", "/admin/users")
        users = res.get("users", [])

        if users:
            for u in users:
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.write(u["email"])
                with col2:
                    st.write(f"{u['tokens_remaining']} tokens")
                with col3:
                    st.write(f"{u['questions_asked']} questions")
                with col4:
                    badge = "active" if u["is_active"] else "inactive"
                    st.write(badge)

    # ── Direct allocation ──
    with tab3:
        st.markdown("### Allocate tokens directly")
        res   = api("get", "/admin/users")
        users = res.get("users", [])

        if users:
            user_options = {
                f"{u['email']} (ID: {u['id']})": u["id"]
                for u in users if u["role"] != "admin"
            }
            selected  = st.selectbox("Select user", user_options.keys())
            tokens    = st.slider("Tokens to add", 10, 1000, 100, step=10)

            if st.button("Allocate tokens", type="primary"):
                user_id = user_options[selected]
                r = api("post", "/admin/allocate",
                        json={"user_id": user_id, "tokens": tokens})
                st.success(r.get("message", "Done"))


# ── Main router ──────────────────────────────────────────

if not is_logged_in():
    show_auth_page()
else:
    show_sidebar()
    page = st.session_state.get("page", "chat")

    if page == "chat":
        show_chat_page()
    elif page == "request_tokens":
        show_request_tokens_page()
    elif page == "admin":
        if is_admin():
            show_admin_page()
        else:
            st.error("Access denied.")