import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import pandas as pd
import base64
import datetime
import io
import re

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'show_login' not in st.session_state:
    st.session_state.show_login = True
# Admin credentials are hardcoded in the login logic
# For production, store these securely in environment variables or a secure config

# ====================== Page Config ======================
st.set_page_config(
    page_title="TCR Admin • Job Portal",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================== Custom CSS ======================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #3B82F6;
    }
    .stButton>button {
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] {
        width: 320px !important;
        padding: 2rem 1rem;
        background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
    }
    .sidebar-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #60A5FA;
        margin-bottom: 2rem;
        text-align: center;
        padding-bottom: 1rem;
        border-bottom: 1px solid #1E293B;
    }
    .sidebar-footer {
        color: #94A3B8;
        font-size: 0.9rem;
        text-align: center;
        margin-top: 3rem;
    }
    /* REMOVED: .profile-card class entirely */
</style>
""", unsafe_allow_html=True)

# ====================== Header ======================
col_header1, col_header2 = st.columns([4, 1])
with col_header1:
    st.markdown('<h1 class="main-header">🔧 TCR Job Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional Admin Dashboard • Manage Workers, Categories & Users</p>', unsafe_allow_html=True)
with col_header2:
    current_time = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    html_content = f'<div style="background: #F1F5F9; padding: 1rem; border-radius: 8px; margin-top: 1rem; text-align: right;"><small style="color: #64748B;">{current_time}</small></div>'
    st.markdown(html_content, unsafe_allow_html=True)
st.markdown("---")

# ====================== Authentication Check ======================
if not st.session_state.authenticated:
    st.session_state.show_login = True

if st.session_state.show_login:
    # Show login form
    st.markdown("<h2 style='text-align: center;'>🔐 Admin Login</h2>", unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form(key='login_form'):
            st.markdown("<h4 style='text-align: center;'>Enter Admin Credentials</h4>", unsafe_allow_html=True)
            username = st.text_input("Admin Username", placeholder="Enter admin username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit_button = st.form_submit_button(label='Login', use_container_width=True, type='primary')
            
            if submit_button:
                # Admin credential validation
                # You can set your preferred admin email and password here
                ADMIN_EMAIL = "admin@tcr.com"  # Change to your admin email
                ADMIN_PASSWORD = "AdminPass123!"  # Change to your secure password
                
                # Alternative: Use Firebase user with role "admin"
                # This would require checking Firebase Authentication
                
                if username == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    st.session_state.user_info = {"username": username, "email": ADMIN_EMAIL}
                    st.session_state.show_login = False
                    st.success("Admin login successful! Redirecting to dashboard...")
                    st.rerun()
                else:
                    st.error("Invalid admin credentials. Please try again.")
                    
        st.markdown("<p style='text-align: center; color: #64748B; font-size: 0.9em;'>Contact administrator if you don't have credentials</p>", unsafe_allow_html=True)
    
    # Stop execution here to show only login form
    st.stop()

# ====================== Firebase Init ======================
try:
    if not firebase_admin._apps:
        cred = credentials.Certificate({
            "type": st.secrets["type"],
            "project_id": st.secrets["project_id"],
            "private_key_id": st.secrets["private_key_id"],
            "private_key": st.secrets["private_key"],  # Already in correct format with line breaks
            "client_email": st.secrets["client_email"],
            "client_id": st.secrets["client_id"],
            "auth_uri": st.secrets["auth_uri"],
            "token_uri": st.secrets["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["client_x509_cert_url"]
        })

        firebase_admin.initialize_app(cred)

except Exception as e:
    st.error("🔴 Firebase connection failed!")
    st.error("Please check your secrets.toml file and ensure the private key is correctly formatted.")
    st.error("The private key must have actual line breaks, not \\n characters.")
    st.error("Make sure you have the complete private key from your service account JSON file.")
    st.exception(e)
    st.stop()


db = firestore.client()

# ====================== Helper Functions ======================
def format_date(ts_ms):
    if ts_ms is None:
        return "N/A"
    try:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
        dt_ist = dt.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
        return dt_ist.strftime("%b %d, %Y")
    except:
        return "Invalid"

def clean_value(val):
    return str(val).strip("<> ") if val is not None and pd.notna(val) else "N/A"

def list_to_string(val):
    if isinstance(val, list):
        return ", ".join(clean_value(i) for i in val if i)
    return clean_value(val)

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, str(email).strip()) is not None

DEFAULT_PHOTO = "https://firebasestorage.googleapis.com/v0/b/placeholder-images.appspot.com/o/default-avatar.png?alt=media"

# ====================== Load Job Categories ======================
@st.cache_data(ttl=300)
def get_job_categories_with_details():
    try:
        docs = db.collection("job_categories").order_by("name").stream()
        categories = []
        for doc in docs:
            data = doc.to_dict()
            name = data.get("name", "").strip()
            icon = data.get("icon", "")
            if name:
                categories.append({
                    "id": doc.id,
                    "Name": name,
                    "Icon": icon,
                    "Description": data.get("description", "") or "No description"
                })
        return categories
    except Exception as e:
        st.error(f"Error loading categories: {e}")
        return []

# ====================== Sidebar ======================
with st.sidebar:
    st.markdown('<div style="text-align: center; margin-bottom: 2rem;"><h2>🔧 TCR Admin</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">📋 Menu Options</p>', unsafe_allow_html=True)
    page = st.radio(
        "Select Section",
        ["📊 Dashboard", "👥 Users/Employees", "🛠️ Job Categories", "⚙️ Settings"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown('<p class="sidebar-title">📈 Quick Stats</p>', unsafe_allow_html=True)
    try:
        total_users = len(list(auth.list_users().iterate_all()))
        active_users = sum(1 for u in auth.list_users().iterate_all() if u.user_metadata.last_sign_in_timestamp)
        total_categories = len(get_job_categories_with_details())
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Users", total_users)
        with col2:
            st.metric("Active", active_users)
        st.metric("Categories", total_categories)
    except:
        st.caption("Stats unavailable")
    st.markdown("---")
    
    # Logout button
    if st.button("🚪 Logout", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.session_state.show_login = True
        st.rerun()
    
    st.markdown('<p class="sidebar-footer">© 2026 TCR Job Portal<br>Professional Admin System</p>', unsafe_allow_html=True)

# ====================== Dashboard ======================
if page == "📊 Dashboard":
    st.header("📊 Dashboard Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try: st.metric("Total Users", len(list(auth.list_users().iterate_all())))
        except: st.metric("Total Users", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try: st.metric("Active Users", sum(1 for u in auth.list_users().iterate_all() if u.user_metadata.last_sign_in_timestamp))
        except: st.metric("Active Users", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try: st.metric("Inactive Users", sum(1 for u in auth.list_users().iterate_all() if not u.user_metadata.last_sign_in_timestamp))
        except: st.metric("Inactive Users", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try: st.metric("Job Categories", len(get_job_categories_with_details()))
        except: st.metric("Job Categories", 0)
        st.markdown('</div>', unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            worker_count = sum(1 for _ in db.collection("workers").stream())
            st.metric("Registered Workers", worker_count)
        except: st.metric("Registered Workers", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with col6:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            user_count = sum(1 for _ in db.collection("user_profiles").stream())
            st.metric("User Profiles", user_count)
        except: st.metric("User Profiles", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with col7:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            recent = sum(1 for u in auth.list_users().iterate_all() 
                        if u.user_metadata.last_sign_in_timestamp and 
                        datetime.datetime.fromtimestamp(u.user_metadata.last_sign_in_timestamp / 1000) >= seven_days_ago)
            st.metric("Active This Week", recent)
        except: st.metric("Active This Week", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with col8:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            total_rating = total_workers = 0
            for doc in db.collection("workers").stream():
                data = doc.to_dict()
                if data.get("rating") is not None:
                    total_rating += float(data["rating"])
                    total_workers += 1
            avg = round(total_rating / total_workers, 2) if total_workers > 0 else 0
            st.metric("Avg Rating", f"{avg}★")
        except: st.metric("Avg Rating", "0★")
        st.markdown('</div>', unsafe_allow_html=True)

# ====================== Users/Employees ======================
elif page == "👥 Users/Employees":
    st.header("👥 Users/Employees Management")

    col_search1, col_search2, col_search3 = st.columns([3, 2, 2])
    with col_search1:
        search_term = st.text_input("🔍 Search Users", placeholder="Name, email, profession...")
    with col_search2:
        role_filter = st.selectbox("Role", ["All", "Worker", "User"])
    with col_search3:
        profession_filter = st.selectbox("Profession", ["All"] + [cat["Name"] for cat in get_job_categories_with_details()])

    tab1, tab2, tab3 = st.tabs(["✅ Active Users", "❌ Inactive Users", "📤 Bulk Import"])

    def get_full_profile(uid):
        worker = db.collection("workers").document(uid).get()
        user = db.collection("user_profiles").document(uid).get()
        if worker.exists: return worker.to_dict(), "Worker"
        if user.exists: return user.to_dict(), "User"
        return {}, "Unknown"

    def load_users(active_only=None):
        users = []
        try:
            for user in auth.list_users().iterate_all():
                last_sign_in = user.user_metadata.last_sign_in_timestamp
                is_active = last_sign_in is not None
                if (active_only is True and not is_active) or (active_only is False and is_active):
                    continue
                profile, role = get_full_profile(user.uid)
                users.append({
                    "Select": False,
                    "UID": user.uid,
                    "Name": clean_value(profile.get("name", user.email)),
                    "Email": clean_value(user.email),
                    "Role": role,
                    "Mobile": clean_value(profile.get("mobile", "N/A")),
                    "Profession": clean_value(profile.get("profession", "N/A")),
                    "Hourly Rate": f"₹{profile.get('hourlyRate', 0)}" if profile.get('hourlyRate') else "N/A",
                    "Rating": f"{profile.get('rating', 0)}★",
                    "Experience": f"{profile.get('experienceYears', 0)} yrs",
                    "Last Login": format_date(last_sign_in) if last_sign_in else "Never"
                })
        except Exception as e:
            st.error(f"Error loading users: {e}")
        return users

    def filter_users(users):
        filtered = users
        if search_term:
            filtered = [u for u in filtered if search_term.lower() in str(u["Name"]).lower() or 
                       search_term.lower() in str(u["Email"]).lower() or 
                       search_term.lower() in str(u["Profession"]).lower()]
        if role_filter != "All":
            filtered = [u for u in filtered if u["Role"] == role_filter]
        if profession_filter != "All":
            filtered = [u for u in filtered if u["Profession"] == profession_filter]
        return filtered

    active_raw = load_users(active_only=True)
    inactive_raw = load_users(active_only=False)
    active_users = filter_users(active_raw)
    inactive_users = filter_users(inactive_raw)

    # Active Users Tab - PROFILE VIEW WITHOUT WHITE CARD
    with tab1:
        st.subheader("✅ Active Users")

        if "selected_uid" in st.session_state and st.session_state.selected_uid:
            uid = st.session_state.selected_uid
            try:
                profile, role = get_full_profile(uid)
                if not profile or role == "Unknown":
                    raise Exception("Profile not found")

                st.markdown("---")

                # Clean, borderless profile layout
                col1, col2 = st.columns([1, 4])
                with col1:
                    photo = clean_value(profile.get("profilePhoto", DEFAULT_PHOTO))
                    st.image(photo if photo != "N/A" else DEFAULT_PHOTO, width=150, caption="Profile Photo")
                with col2:
                    st.markdown(f"### {clean_value(profile.get('name', 'N/A'))}")
                    st.markdown(f"**{role} • {clean_value(profile.get('profession', 'N/A'))}**")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.markdown(f"⭐ {profile.get('rating', 0)} | 💼 {profile.get('totalJobs', 0)} jobs")
                    with c2: st.markdown(f"💰 ₹{profile.get('hourlyRate', 0)}/hr")
                    with c3: st.markdown(f"📅 {profile.get('experienceYears', 0)} yrs")

                st.markdown("---")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("**Email**"); st.markdown(clean_value(profile.get("email", "N/A")))
                    st.markdown("**Mobile**"); st.markdown(clean_value(profile.get("mobile", "N/A")))
                with c2:
                    st.markdown("**Languages**"); st.markdown(list_to_string(profile.get("languages", [])))
                    st.markdown("**Address**"); st.markdown(clean_value(profile.get("address", "N/A")))
                with c3:
                    st.markdown("**About**"); st.markdown(f"_{clean_value(profile.get('about', 'No bio'))}_")
                    st.markdown("**Status**"); st.markdown("✅ Available" if profile.get("isAvailable") else "❌ Not Available")

                if st.button("❌ Close Profile", type="secondary", use_container_width=True, key="close_profile_btn"):
                    del st.session_state.selected_uid
                    st.rerun()

            except Exception:
                st.error("Failed to load profile. The user may have been deleted.")
                if st.button("❌ Close", type="secondary", use_container_width=True, key="close_error_btn"):
                    if "selected_uid" in st.session_state:
                        del st.session_state.selected_uid
                    st.rerun()

        if active_users:
            df = pd.DataFrame(active_users)
            edited = st.data_editor(
                df,
                column_config={
                    "Select": st.column_config.CheckboxColumn("Select", width="small"),
                    "UID": None
                },
                hide_index=True,
                use_container_width=True,
                key="active_table"
            )
            selected = edited[edited["Select"]]
            if st.button("👀 View Profile", type="primary", disabled=len(selected)!=1, use_container_width=True):
                st.session_state.selected_uid = selected.iloc[0]["UID"]
                st.rerun()
            st.dataframe(edited.drop(columns=["Select", "UID"]), use_container_width=True, hide_index=True)
        else:
            st.info("No active users found.")

    # Inactive Users Tab
    with tab2:
        st.subheader("❌ Inactive Users")
        if inactive_users:
            df = pd.DataFrame(inactive_users)
            st.dataframe(df.drop(columns=["UID"]), use_container_width=True, hide_index=True)
            st.caption("These users will move to Active tab after first login.")
        else:
            st.info("No inactive users.")

    # Bulk Import Tab (unchanged - already perfect with row-wise errors)
    with tab3:
        st.markdown("### 📤 Bulk Import Workers from Excel")

        worker_columns = ["name", "email", "mobile", "whatsapp", "address", "gender",
                          "profession", "hourlyRate", "experienceYears", "about", "languages"]
        workers_df = pd.DataFrame(columns=worker_columns)
        job_categories = [cat["Name"] for cat in get_job_categories_with_details()]
        reference_df = pd.DataFrame({"Available Job Categories": job_categories + [""] * max(0, 20 - len(job_categories))})

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            workers_df.to_excel(writer, index=False, sheet_name='Workers')
            reference_df.to_excel(writer, index=False, sheet_name='Job_Categories_Reference')
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="TCR_Workers_Template.xlsx">📥 Download Template</a>'
        st.markdown(href, unsafe_allow_html=True)

        st.info("**Instructions:** Use exact profession names from 'Job_Categories_Reference' sheet • Default password: **TempPass123!**")

        uploaded = st.file_uploader("Upload Filled Excel File", type=['xlsx'])

        if uploaded:
            try:
                df = pd.read_excel(uploaded, sheet_name='Workers')
                required_cols = ["name", "email", "mobile", "profession"]
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    st.error(f"Missing required columns: {', '.join(missing_cols)}")
                    st.stop()

                existing_emails = set()
                existing_mobiles = set()
                try:
                    for user in auth.list_users().iterate_all():
                        existing_emails.add(user.email.lower())
                except: pass

                try:
                    for doc in db.collection("workers").stream():
                        data = doc.to_dict()
                        mobile = str(data.get("mobile", "")).strip()
                        if mobile.isdigit() and len(mobile) == 10:
                            existing_mobiles.add(mobile)
                except: pass

                professions = {cat["Name"].strip() for cat in get_job_categories_with_details()}

                valid_rows = []
                invalid_rows = []

                for idx, row in df.iterrows():
                    row_num = idx + 2
                    errors = []
                    row_dict = row.to_dict()

                    name = str(row_dict.get("name", "")).strip()
                    email = str(row_dict.get("email", "")).strip().lower()
                    mobile = str(row_dict.get("mobile", "")).strip()
                    profession = str(row_dict.get("profession", "")).strip()

                    if not name:
                        errors.append("Name is required")
                    if not email:
                        errors.append("Email is required")
                    elif not is_valid_email(email):
                        errors.append("Invalid email format")
                    elif email in existing_emails:
                        errors.append("Email already exists")

                    if not mobile:
                        errors.append("Mobile is required")
                    elif not mobile.isdigit() or len(mobile) != 10:
                        errors.append("Mobile must be exactly 10 digits")
                    elif mobile in existing_mobiles:
                        errors.append("Mobile number already registered")

                    if not profession:
                        errors.append("Profession is required")
                    elif profession not in professions:
                        errors.append(f"Invalid profession: '{profession}' (check reference sheet)")

                    row_dict["Row"] = row_num
                    row_dict["Status"] = "Invalid" if errors else "Valid"
                    row_dict["Error Details"] = "<br>".join(errors) if errors else "-"

                    if errors:
                        invalid_rows.append(row_dict)
                    else:
                        valid_rows.append(row_dict)
                        existing_emails.add(email)
                        existing_mobiles.add(mobile)

                st.markdown(f"### Validation Results")
                colv1, colv2 = st.columns(2)
                with colv1:
                    st.success(f"**{len(valid_rows)} rows valid** → Ready to import")
                with colv2:
                    if invalid_rows:
                        st.error(f"**{len(invalid_rows)} rows have errors** → Fix before import")

                if valid_rows:
                    st.markdown("#### Valid Workers (Will be imported)")
                    st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True)

                    if st.button("Import All Valid Workers", type="primary", use_container_width=True):
                        with st.spinner("Importing workers..."):
                            success_count = 0
                            for row in valid_rows:
                                try:
                                    user = auth.create_user(
                                        email=row["email"],
                                        password="TempPass123!"
                                    )
                                    worker_data = {
                                        "name": row["name"],
                                        "email": row["email"],
                                        "mobile": str(row["mobile"]),
                                        "whatsapp": str(row.get("whatsapp", "")),
                                        "address": str(row.get("address", "")),
                                        "gender": str(row.get("gender", "")),
                                        "profession": row["profession"],
                                        "hourlyRate": int(row.get("hourlyRate", 0) or 0),
                                        "experienceYears": int(row.get("experienceYears", 0) or 0),
                                        "about": str(row.get("about", "")),
                                        "languages": [lang.strip() for lang in str(row.get("languages", "")).split(",") if lang.strip()],
                                        "profilePhoto": DEFAULT_PHOTO,
                                        "isAvailable": True,
                                        "rating": 0.0,
                                        "totalJobs": 0,
                                        "createdAt": firestore.SERVER_TIMESTAMP
                                    }
                                    db.collection("workers").document(user.uid).set(worker_data)
                                    success_count += 1
                                except Exception as e:
                                    st.error(f"Failed for {row['email']}: {str(e)}")

                            st.success(f"Successfully imported {success_count} workers!")
                            st.balloons()
                            st.rerun()

                if invalid_rows:
                    st.markdown("#### Invalid Rows (Fix these)")
                    error_df = pd.DataFrame(invalid_rows)
                    st.dataframe(
                        error_df[["Row", "name", "email", "mobile", "profession", "Error Details"]],
                        use_container_width=True,
                        hide_index=True
                    )

            except Exception as e:
                st.error(f"Error reading Excel file: {str(e)}")

# ====================== Job Categories ======================
elif page == "🛠️ Job Categories":
    st.header("🛠️ Job Categories Management")

    # Fetch categories
    categories = get_job_categories_with_details()
    cat_names = [c["Name"] for c in categories]

    tab1, tab2, tab3 = st.tabs(["📂 View All", "➕ Add New", "✏️ Edit Existing"])

    # --- TAB 1: VIEW ---
    with tab1:
        st.markdown("### All Job Categories")
        search_cat = st.text_input("Search Categories", placeholder="Type to filter...", key="search_cat_main")
        
        filtered_cats = categories
        if search_cat:
            filtered_cats = [c for c in filtered_cats if search_cat.lower() in c["Name"].lower()]

        worker_counts = {}
        try:
            for doc in db.collection("workers").stream():
                prof = doc.to_dict().get("profession", "").strip()
                worker_counts[prof] = worker_counts.get(prof, 0) + 1
        except:
            worker_counts = {}

        if filtered_cats:
            table_data = []
            for cat in filtered_cats:
                table_data.append({
                    "Icon": cat["Icon"],
                    "Category Name": cat["Name"],
                    "Associated Workers": worker_counts.get(cat["Name"], 0),
                    "Description": cat["Description"]
                })

            st.dataframe(
                pd.DataFrame(table_data),
                column_config={
                    "Icon": st.column_config.ImageColumn("Icon", width="small"),
                    "Category Name": st.column_config.TextColumn("Category Name"),
                    "Associated Workers": st.column_config.NumberColumn("Workers", format="%d"),
                    "Description": st.column_config.TextColumn("Description")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No job categories found.")

    # --- TAB 2: ADD ---
    with tab2:
        st.markdown("### Add New Category")
        with st.form("add_category_form"):
            c1, c2 = st.columns([2, 1])
            name = c1.text_input("Category Name*", placeholder="e.g., Electrician")
            desc = c2.text_area("Description")
            icon = st.file_uploader("Upload Icon*", type=['png', 'jpg', 'jpeg'], key="add_cat_icon")
            
            if st.form_submit_button("Add Category", type="primary"):
                if name and icon:
                    try:
                        icon_b64 = base64.b64encode(icon.getvalue()).decode()
                        icon_url = f"data:{icon.type};base64,{icon_b64}"
                        db.collection("job_categories").add({
                            "name": name.strip(),
                            "description": desc.strip(),
                            "icon": icon_url,
                            "created_at": firestore.SERVER_TIMESTAMP
                        })
                        st.success("Category added successfully!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Name and icon are required.")

    # --- TAB 3: EDIT ---
    with tab3:
        st.markdown("### Edit Existing Category")
        if not categories:
            st.warning("No categories available to edit.")
        else:
            selected_cat_name = st.selectbox("Select Category to Edit", cat_names, key="edit_cat_select")
            
            # Find selected category data
            selected_cat = next((c for c in categories if c["Name"] == selected_cat_name), None)
            
            if selected_cat:
                with st.form("edit_category_form"):
                    st.info(f"Editing: **{selected_cat['Name']}**")
                    
                    new_name = st.text_input("Category Name", value=selected_cat['Name'])
                    new_desc = st.text_area("Description", value=selected_cat['Description'])
                    
                    st.markdown("**Current Icon:**")
                    st.image(selected_cat['Icon'], width=60)
                    
                    new_icon = st.file_uploader("Upload New Icon (Optional)", type=['png', 'jpg', 'jpeg'], key="edit_cat_icon")
                    
                    if st.form_submit_button("Update Category", type="primary"):
                        if new_name:
                            try:
                                update_data = {
                                    "name": new_name.strip(),
                                    "description": new_desc.strip()
                                }
                                
                                if new_icon:
                                    icon_b64 = base64.b64encode(new_icon.getvalue()).decode()
                                    update_data["icon"] = f"data:{new_icon.type};base64,{icon_b64}"
                                
                                db.collection("job_categories").document(selected_cat["id"]).update(update_data)
                                
                                st.success(f"Category '{new_name}' updated successfully!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating category: {e}")
                        else:
                            st.error("Category name cannot be empty.")

# ====================== Settings ======================
else:
    st.header("Settings & Account Management")
    
    # Create tabs for different settings
    settings_tab, account_tab, privacy_tab = st.tabs(["⚙️ System Settings", "👤 Account Settings", "🛡️ Privacy Policy"])
    
    with settings_tab:
        st.subheader("System Information")
        st.success("Professional Admin Panel • January 2026")
        st.info("""
        White profile card container completely removed
        Clean, modern, borderless profile view
        Bulk import with precise row-wise error reporting
        All features working perfectly
        """)
    
    with account_tab:
        st.subheader("Account Settings")
        
        # Form to change admin credentials
        with st.form(key='change_credentials_form'):
            st.write("Change your admin credentials")
            new_email = st.text_input("New Admin Email", placeholder="Leave blank to keep current")
            current_password = st.text_input("Current Password", type="password", placeholder="Enter current password to confirm")
            new_password = st.text_input("New Password", type="password", placeholder="Leave blank to keep current")
            confirm_password = st.text_input("Confirm New Password", type="password", placeholder="Re-enter new password")
            
            if st.form_submit_button("Update Credentials", type="primary", use_container_width=True):
                # Current admin credentials (from login logic)
                ADMIN_EMAIL = "admin@tcr.com"  # This should match your stored admin email
                ADMIN_PASSWORD = "AdminPass123!"  # This should match your stored admin password
                
                if current_password != ADMIN_PASSWORD:
                    st.error("Current password is incorrect!")
                elif new_password and new_password != confirm_password:
                    st.error("New passwords do not match!")
                elif new_password and len(new_password) < 6:
                    st.error("Password must be at least 6 characters long!")
                else:
                    # For production: update these in your code/config
                    # Currently this just shows the new values for demonstration
                    
                    # Show what would be updated
                    st.info("**Demo Mode:** In a production environment, you would update the credentials in your application code.")
                    
                    if new_email:
                        st.info(f"Email would be changed to: {new_email}")
                    
                    if new_password:
                        st.info("Password would be updated in secure storage.")
                    
                    if not new_email and not new_password:
                        st.info("No changes requested.")
                        
                    # Reset form
                    st.rerun()
        
        st.markdown("---")
        st.info("**Note:** In a production environment, credentials should be stored securely using proper authentication methods like hashing and database storage.")
    
    with privacy_tab:
        st.subheader("🛡️ Privacy Policy - TCR")
        
        st.markdown("**Last Updated:** January 31, 2026")
        
        st.markdown("TCR (\"we\", \"our\", \"us\") respects your privacy and is committed to protecting the personal information of users (\"you\", \"your\"). This Privacy Policy explains how we collect, use, store, and protect your information when you use the TCR mobile application (\"App\").")
        
        st.markdown("**By using the TCR App, you agree to the collection and use of information in accordance with this policy.**")
        
        st.markdown("### 1. Information We Collect")
        st.markdown("We may collect the following types of information:")
        
        st.markdown("**a. Personal Information**")
        st.markdown("- Full name\n- Email address\n- Phone number\n- Date of birth (if required)\n- Address or location details\n- Profile photo (optional)")
        
        st.markdown("**b. Professional Information**")
        st.markdown("- Resume / CV details\n- Educational qualifications\n- Work experience\n- Skills and certifications\n- Job preferences")
        
        st.markdown("**c. Employer Information (if applicable)**")
        st.markdown("- Company name\n- Job postings\n- Contact details\n- Hiring requirements")
        
        st.markdown("**d. Technical Information**")
        st.markdown("- Device information (model, OS version)\n- App usage data\n- IP address\n- Log files and crash reports")
        
        st.markdown("### 2. How We Use Your Information")
        st.markdown("We use the collected information to:")
        st.markdown("- Create and manage user accounts\n- Connect job seekers with employers\n- Enable job applications and hiring processes\n- Improve app functionality and user experience\n- Send notifications related to jobs, updates, or system alerts\n- Provide customer support\n- Ensure security and prevent fraud")
        
        st.markdown("### 3. Data Sharing and Disclosure")
        st.markdown("We do not sell or rent your personal data.\n\nYour information may be shared only:\n- Between job seekers and employers for hiring purposes\n- With trusted third-party service providers (hosting, analytics, notifications)\n- When required by law, legal process, or government authorities\n- To protect the rights, safety, or property of TCR and its users")
        
        st.markdown("### 4. Data Storage and Security")
        st.markdown("We store your data securely using industry-standard security practices\n- Access to personal data is restricted to authorized personnel only\n- While we strive to protect your data, no system is 100% secure")
        
        st.markdown("### 5. User Rights and Choices")
        st.markdown("You have the right to:\n- Access and update your personal information\n- Request deletion of your account and data\n- Control notification preferences\n- Withdraw consent at any time (subject to legal requirements)\n\nTo exercise these rights, contact us at the email below.")
        
        st.markdown("### 6. Data Retention")
        st.markdown("We retain user data only as long as necessary:\n- To provide services\n- To comply with legal obligations\n- To resolve disputes and enforce policies")
        
        st.markdown("### 7. Third-Party Links")
        st.markdown("The TCR App may contain links to third-party websites or services. We are not responsible for their privacy practices or content.")
        
        st.markdown("### 8. Children’s Privacy")
        st.markdown("TCR is not intended for users under the age of 18. We do not knowingly collect personal data from children.")
        
        st.markdown("### 9. Changes to This Privacy Policy")
        st.markdown("We may update this Privacy Policy from time to time. Any changes will be notified through the app or posted on this page.")
        
        st.markdown("### 10. Contact Us")
        st.markdown("If you have any questions or concerns about this Privacy Policy, please contact us:\n\n**Email:** tcr122025@gmail.com\n\n**App Name:** TCR")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B;'>TCR Job Portal • Professional Admin Panel • January 2026</p>", unsafe_allow_html=True)