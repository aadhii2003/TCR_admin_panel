import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import pandas as pd
import base64
import datetime
import io
import re
import os
from PIL import Image
import uuid

# ====================== Page Config ======================
st.set_page_config(
    page_title="TCR Admin • Job Portal",
    page_icon=":wrench:",
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
</style>
""", unsafe_allow_html=True)

# ====================== Header ======================
col_header1, col_header2 = st.columns([4, 1])
with col_header1:
    st.markdown('<h1 class="main-header">:wrench: TCR Job Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional Admin Dashboard • Manage Workers, Categories & Users</p>', unsafe_allow_html=True)
with col_header2:
    current_time = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    html_content = f'<div style="background: #F1F5F9; padding: 1rem; border-radius: 8px; margin-top: 1rem; text-align: right;"><small style="color: #64748B;">{current_time}</small></div>'
    st.markdown(html_content, unsafe_allow_html=True)
st.markdown("---")

# ====================== Firebase Init ======================
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_config = dict(st.secrets["firebase"])
            # storageBucket must be in secrets too, e.g. "tcr-app-3ca2e.appspot.com"
            bucket_name = firebase_config.pop("storageBucket", None) or st.secrets.get("storageBucket", "")
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        elif "project_id" in st.secrets:
            firebase_config = {k: st.secrets[k] for k in ["type", "project_id", "private_key_id", "private_key",
                                                         "client_email", "client_id", "auth_uri", "token_uri",
                                                         "auth_provider_x509_cert_url", "client_x509_cert_url"]}
            bucket_name = st.secrets.get("storageBucket", f"{st.secrets['project_id']}.appspot.com")
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        elif os.path.exists("tcr-serviceAccountKey.json"):
            import json
            with open("tcr-serviceAccountKey.json") as f:
                sa = json.load(f)
            bucket_name = sa.get("storageBucket", f"{sa['project_id']}.appspot.com")
            cred = credentials.Certificate("tcr-serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        else:
            st.error(":red_circle: Firebase credentials not found!")
            st.info("Please add your Firebase service account JSON content to Streamlit Cloud Secrets.")
            st.stop()
    except Exception as e:
        st.error(f":red_circle: Firebase initialization failed: {e}")
        st.stop()

db = firestore.client()

# ====================== Storage Upload Helper ======================
# ─────────────────────────────────────────────────────────────────
# FIX: Upload icon to Firebase Storage → get a public https:// URL
# Flutter's CachedNetworkImage needs an https:// URL, NOT base64.
# Old approach (base64 in Firestore) caused icons to never show in app.
# ─────────────────────────────────────────────────────────────────

MAX_ICON_SIZE_MB = 5
MAX_ICON_BYTES = MAX_ICON_SIZE_MB * 1024 * 1024
ICON_MAX_DIMENSION = 256  # px — icons are small, 256px is plenty


def resize_image_bytes(file_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    """
    Resize image to max 256×256 and return (bytes, final_mime_type).
    PNG stays PNG (preserves transparency). JPG stays JPG.
    """
    img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    img.thumbnail((ICON_MAX_DIMENSION, ICON_MAX_DIMENSION), Image.LANCZOS)

    buf = io.BytesIO()
    if mime_type == "image/png":
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "image/png"
    else:
        # JPEG doesn't support alpha — flatten onto white background
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        bg.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue(), "image/jpeg"


def upload_icon_to_storage(file_bytes: bytes, mime_type: str, category_name: str) -> str:
    """
    Upload a category icon to Firebase Storage under category_icons/<uuid>.<ext>
    Returns the public https:// download URL that Flutter can use directly.
    """
    resized_bytes, final_mime = resize_image_bytes(file_bytes, mime_type)
    ext = "png" if final_mime == "image/png" else "jpg"

    # Unique filename so re-uploads don't collide
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', category_name.strip().lower())
    filename = f"category_icons/{safe_name}_{uuid.uuid4().hex[:8]}.{ext}"

    bucket = storage.bucket()
    blob = bucket.blob(filename)
    blob.upload_from_string(resized_bytes, content_type=final_mime)

    # Make the file publicly readable so Flutter can fetch it without auth
    blob.make_public()

    return blob.public_url  # "https://storage.googleapis.com/..."


def delete_old_icon_from_storage(icon_url: str):
    """
    If the existing iconUrl is a Firebase Storage URL, delete the old file
    to avoid orphaned objects piling up in Storage.
    """
    try:
        if "storage.googleapis.com" not in icon_url:
            return  # not a Storage URL (could be old base64 or placeholder), skip
        # Extract blob path from URL: .../o/<encoded_path>?alt=...
        # For public URLs the format is:
        # https://storage.googleapis.com/<bucket>/<path>
        bucket_name = storage.bucket().name
        prefix = f"https://storage.googleapis.com/{bucket_name}/"
        if icon_url.startswith(prefix):
            blob_path = icon_url[len(prefix)].split("?")[0]
            bucket = storage.bucket()
            blob = bucket.blob(blob_path)
            blob.delete()
    except Exception:
        pass  # non-critical, don't break the UI


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

def parse_coordinate(val):
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    s = str(val).strip()
    try: return float(s)
    except: pass
    dms_match = re.search(r"(\d+)\D+(\d+)\D+(\d+(?:\.\d+)?)\D*([NSEW])", s, re.IGNORECASE)
    if dms_match:
        d, m, sv, direction = dms_match.groups()
        dec = float(d) + float(m)/60 + float(sv)/3600
        if direction.upper() in ['S', 'W']: dec = -dec
        return dec
    dir_match = re.search(r"(\d+(?:\.\d+)?)\D*([NSEW])", s, re.IGNORECASE)
    if dir_match:
        v, direction = dir_match.groups()
        dec = float(v)
        if direction.upper() in ['S', 'W']: dec = -dec
        return dec
    return None

DEFAULT_PHOTO = "https://firebasestorage.googleapis.com/v0/b/placeholder-images.appspot.com/o/default-avatar.png?alt=media"

# ====================== User Management Helpers ======================
def delete_user_account(uid):
    try:
        db.collection("workers").document(uid).delete()
        db.collection("user_profiles").document(uid).delete()
        auth.delete_user(uid)
        return True, "User successfully deleted from Authentication and Database."
    except Exception as e:
        return False, f"Error deleting user: {str(e)}"

# ====================== Load Job Categories ======================
@st.cache_data(ttl=300)
def get_job_categories_with_details():
    try:
        docs = db.collection("job_categories").order_by("name").stream()
        categories = []
        for doc in docs:
            data = doc.to_dict()
            name = data.get("name", "").strip()
            icon = data.get("iconUrl") or data.get("icon")
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
    st.markdown('<div style="text-align: center; margin-bottom: 2rem;"><h2>:wrench: TCR Admin</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">:clipboard: Menu Options</p>', unsafe_allow_html=True)
    page = st.radio(
        "Select Section",
        [":bar_chart: Dashboard", ":busts_in_silhouette: Users/Employees", ":hammer_and_wrench: Job Categories", ":gear: Settings"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown('<p class="sidebar-title">:chart_with_upwards_trend: Quick Stats</p>', unsafe_allow_html=True)
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
    st.markdown('<p class="sidebar-footer">© 2026 TCR Job Portal<br>Professional Admin System</p>', unsafe_allow_html=True)

# ====================== Dashboard ======================
if page == ":bar_chart: Dashboard":
    st.header(":bar_chart: Dashboard Overview")
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
elif page == ":busts_in_silhouette: Users/Employees":
    st.header(":busts_in_silhouette: Users/Employees Management")

    col_search1, col_search2, col_search3 = st.columns([3, 2, 2])
    with col_search1:
        search_term = st.text_input(":mag: Search Users", placeholder="Name, email, profession...")
    with col_search2:
        role_filter = st.selectbox("Role", ["All", "Worker", "User"])
    with col_search3:
        profession_filter = st.selectbox("Profession", ["All"] + [cat["Name"] for cat in get_job_categories_with_details()])

    tab1, tab2, tab3 = st.tabs([":white_check_mark: Active Users", ":x: Inactive Users", ":outbox_tray: Bulk Import"])

    def get_full_profile(uid):
        worker = db.collection("workers").document(uid).get()
        user = db.collection("user_profiles").document(uid).get()
        if worker.exists: return worker.to_dict(), "Worker"
        if user.exists: return user.to_dict(), "User"
        return {}, "Unknown"

    @st.cache_data(ttl=60)
    def load_users_optimized():
        users_data = []
        try:
            workers_ref = {doc.id: doc.to_dict() for doc in db.collection("workers").stream()}
            profiles_ref = {doc.id: doc.to_dict() for doc in db.collection("user_profiles").stream()}

            for auth_user in auth.list_users().iterate_all():
                uid = auth_user.uid
                profile = {}
                role = "Unknown"

                if uid in workers_ref:
                    profile = workers_ref[uid]
                    role = "Worker"
                elif uid in profiles_ref:
                    profile = profiles_ref[uid]
                    role = "User"
                else:
                    role = ":warning: Orphaned (No Profile)"

                last_sign_in = auth_user.user_metadata.last_sign_in_timestamp
                users_data.append({
                    "UID": uid,
                    "IsActive": last_sign_in is not None,
                    "Name": clean_value(profile.get("name", auth_user.email)),
                    "Email": clean_value(auth_user.email),
                    "Role": role,
                    "Mobile": clean_value(profile.get("mobile", "N/A")),
                    "Profession": clean_value(profile.get("profession", "N/A")),
                    "Hourly Rate": f"₹{profile.get('hourlyRate', 0)}" if profile.get('hourlyRate') else "N/A",
                    "Rating": f"{profile.get('rating', 0)}★",
                    "Experience": f"{profile.get('experienceYears', 0)} yrs",
                    "Last Login": format_date(last_sign_in) if last_sign_in else "Never",
                    "Last Login TS": last_sign_in or 0
                })
        except Exception as e:
            st.error(f"Error loading users: {e}")
        return users_data

    all_users_raw = load_users_optimized()

    def filter_and_split_users(users):
        active = []
        inactive = []
        for u in users:
            if search_term:
                s = search_term.lower()
                if s not in str(u["Name"]).lower() and s not in str(u["Email"]).lower() and s not in str(u["Profession"]).lower():
                    continue
            if role_filter != "All" and u["Role"] != role_filter:
                continue
            if profession_filter != "All" and u["Profession"] != profession_filter:
                continue
            user_row = {**u, "Select": False}
            if u["IsActive"]:
                active.append(user_row)
            else:
                inactive.append(user_row)
        return active, inactive

    active_users, inactive_users = filter_and_split_users(all_users_raw)

    with tab1:
        st.subheader(":white_check_mark: Active Users")

        if "selected_uid" in st.session_state and st.session_state.selected_uid:
            uid = st.session_state.selected_uid
            try:
                profile, role = get_full_profile(uid)
                if not profile or role == "Unknown":
                    raise Exception("Profile not found")

                st.markdown("---")
                col1, col2 = st.columns([1, 4])
                with col1:
                    photo = clean_value(profile.get("profilePhoto", DEFAULT_PHOTO))
                    st.image(photo if photo != "N/A" else DEFAULT_PHOTO, width=150, caption="Profile Photo")
                with col2:
                    st.markdown(f"### {clean_value(profile.get('name', 'N/A'))}")
                    st.markdown(f"{role} • {clean_value(profile.get('profession', 'N/A'))}")
                    c1, c2, c3 = st.columns(3)
                    with c1: st.markdown(f":star: {profile.get('rating', 0)} | :briefcase: {profile.get('totalJobs', 0)} jobs")
                    with c2: st.markdown(f":moneybag: ₹{profile.get('hourlyRate', 0)}/hr")
                    with c3: st.markdown(f":date: {profile.get('experienceYears', 0)} yrs")

                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown("Email"); st.markdown(clean_value(profile.get("email", "N/A")))
                    st.markdown("Mobile"); st.markdown(clean_value(profile.get("mobile", "N/A")))
                    st.markdown("Location"); st.markdown(clean_value(profile.get("location", "N/A")))
                with c2:
                    st.markdown("Languages"); st.markdown(list_to_string(profile.get("languages", [])))
                    addr_parts = [str(profile.get(k, "")).strip() for k in ["address", "city", "state"]]
                    address_full = ", ".join([p for p in addr_parts if p and p.lower() != "n/a" and p != "None"])
                    st.markdown("Address"); st.markdown(address_full if address_full else "N/A")
                with c3:
                    st.markdown("About"); st.markdown(f"_{clean_value(profile.get('about', 'No bio'))}_")
                    st.markdown("Status"); st.markdown(":white_check_mark: Available" if profile.get("isAvailable") else ":x: Not Available")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if f"confirm_delete_{uid}" not in st.session_state:
                        if st.button(":wastebasket: Delete User Account", type="primary", use_container_width=True):
                            st.session_state[f"confirm_delete_{uid}"] = True
                            st.rerun()
                    else:
                        st.warning(":warning: Are you sure? This will delete the user from Auth and Database.")
                        c_del1, c_del2 = st.columns(2)
                        with c_del1:
                            if st.button(":fire: Confirm", type="primary", use_container_width=True):
                                success, msg = delete_user_account(uid)
                                if success:
                                    st.success(msg)
                                    del st.session_state.selected_uid
                                    del st.session_state[f"confirm_delete_{uid}"]
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(msg)
                        with c_del2:
                            if st.button(":x: Cancel", use_container_width=True):
                                del st.session_state[f"confirm_delete_{uid}"]
                                st.rerun()

                with col_btn2:
                    if st.button(":x: Close Profile", type="secondary", use_container_width=True, key="close_profile_btn"):
                        del st.session_state.selected_uid
                        st.rerun()

            except Exception:
                st.error(":warning: Profile data missing from database. This user might have been partially deleted.")
                col_err1, col_err2 = st.columns(2)
                with col_err1:
                    if st.button(":wastebasket: Force Delete from Auth", type="primary", use_container_width=True):
                        success, msg = delete_user_account(uid)
                        if success:
                            st.success(msg)
                            del st.session_state.selected_uid
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(msg)
                with col_err2:
                    if st.button(":x: Close", type="secondary", use_container_width=True, key="close_error_btn"):
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
            if st.button(":eyes: View Profile", type="primary", disabled=len(selected)!=1, use_container_width=True):
                st.session_state.selected_uid = selected.iloc[0]["UID"]
                st.rerun()
            st.dataframe(edited.drop(columns=["Select", "UID"]), use_container_width=True, hide_index=True)
        else:
            st.info("No active users found.")

    with tab2:
        st.subheader(":x: Inactive Users")
        if inactive_users:
            df = pd.DataFrame(inactive_users)
            st.dataframe(df.drop(columns=["UID"]), use_container_width=True, hide_index=True)
            st.caption("These users will move to Active tab after first login.")
        else:
            st.info("No inactive users.")

    with tab3:
        st.markdown("### :outbox_tray: Bulk Import Workers from Excel")
        worker_columns = ["name", "email", "mobile", "whatsapp", "address", "city", "state", "gender",
                          "profession", "hourlyRate", "experienceYears", "about", "languages", "latitude", "longitude"]
        workers_df = pd.DataFrame(columns=worker_columns)
        job_categories = [cat["Name"] for cat in get_job_categories_with_details()]
        reference_df = pd.DataFrame({"Available Job Categories": job_categories + [""] * max(0, 20 - len(job_categories))})

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            workers_df.to_excel(writer, index=False, sheet_name='Workers')
            reference_df.to_excel(writer, index=False, sheet_name='Job_Categories_Reference')
        output.seek(0)
        b64 = base64.b64encode(output.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="TCR_Workers_Template.xlsx">:inbox_tray: Download Template</a>'
        st.markdown(href, unsafe_allow_html=True)

        st.info("Instructions: Use exact profession names from 'Job_Categories_Reference' sheet • Default password: TempPass123!")

        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded = st.file_uploader("Upload Filled Excel File", type=['xlsx'], key=f"uploader_{st.session_state.uploader_key}")

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
                        errors.append("Email already exists in Authentication.")

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

                    lat_val = row_dict.get("latitude")
                    lon_val = row_dict.get("longitude")
                    if pd.notna(lat_val) and parse_coordinate(lat_val) is None:
                        errors.append("Invalid Latitude")
                    if pd.notna(lon_val) and parse_coordinate(lon_val) is None:
                        errors.append("Invalid Longitude")

                    row_dict["Row"] = row_num
                    row_dict["Status"] = "Invalid" if errors else "Valid"
                    row_dict["Error Details"] = "<br>".join(errors) if errors else "-"

                    if errors:
                        invalid_rows.append(row_dict)
                    else:
                        valid_rows.append(row_dict)
                        existing_emails.add(email)
                        existing_mobiles.add(mobile)

                st.markdown("### Validation Results")
                colv1, colv2 = st.columns(2)
                with colv1:
                    st.success(f"{len(valid_rows)} rows valid → Ready to import")
                with colv2:
                    if invalid_rows:
                        st.error(f"{len(invalid_rows)} rows have errors → Fix before import")

                if valid_rows:
                    st.markdown("#### Valid Workers (Will be imported)")
                    st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True)

                    if st.button("Import All Valid Workers", type="primary", use_container_width=True):
                        with st.spinner("Importing workers..."):
                            success_count = 0
                            for row in valid_rows:
                                try:
                                    user = auth.create_user(email=row["email"], password="TempPass123!")
                                    def safe_int(v):
                                        try: return int(float(v)) if pd.notna(v) else 0
                                        except: return 0
                                    def safe_float(v):
                                        res = parse_coordinate(v)
                                        return res if res is not None else 0.0

                                    lat = safe_float(row.get("latitude"))
                                    lon = safe_float(row.get("longitude"))
                                    location_obj = {"latitude": lat, "longitude": lon}
                                    location_updated_at = datetime.datetime.now(
                                        datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                                    ).isoformat()

                                    worker_data = {
                                        "name": row["name"],
                                        "email": row["email"],
                                        "mobile": str(row["mobile"]),
                                        "whatsapp": str(row.get("whatsapp", "")),
                                        "address": str(row.get("address", "")),
                                        "city": str(row.get("city", "")),
                                        "state": str(row.get("state", "")),
                                        "gender": str(row.get("gender", "")),
                                        "profession": row["profession"],
                                        "hourlyRate": safe_int(row.get("hourlyRate")),
                                        "experienceYears": safe_int(row.get("experienceYears")),
                                        "latitude": lat,
                                        "longitude": lon,
                                        "location": location_obj,
                                        "locationUpdatedAt": location_updated_at,
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
                            st.session_state.uploader_key += 1
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
elif page == ":hammer_and_wrench: Job Categories":
    st.header(":hammer_and_wrench: Job Categories Management")

    categories = get_job_categories_with_details()
    cat_names = [c["Name"] for c in categories]

    tab1, tab2, tab3, tab4 = st.tabs([":open_file_folder: View All", ":heavy_plus_sign: Add New", ":pencil2: Edit Existing", ":wastebasket: Delete"])

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
        st.info(
            ":pushpin: Icon is uploaded to **Firebase Storage** and stored as an `https://` URL. "
            "This is what your Flutter app reads — no base64 involved."
        )

        with st.form("add_category_form"):
            c1, c2 = st.columns([2, 1])
            name = c1.text_input("Category Name*", placeholder="e.g., Electrician")
            desc = c2.text_area("Description")
            icon = st.file_uploader(
                f"Upload Icon* (max {MAX_ICON_SIZE_MB}MB • PNG/JPG)",
                type=['png', 'jpg', 'jpeg'],
                key="add_cat_icon"
            )

            if st.form_submit_button("Add Category", type="primary"):
                if name and icon:
                    raw_bytes = icon.getvalue()
                    if len(raw_bytes) > MAX_ICON_BYTES:
                        st.error(f":x: File too large ({len(raw_bytes)/1024/1024:.1f}MB). Maximum allowed is {MAX_ICON_SIZE_MB}MB.")
                    else:
                        try:
                            with st.spinner("Uploading icon to Firebase Storage..."):
                                # ✅ FIX: upload to Storage → get https:// URL
                                icon_url = upload_icon_to_storage(raw_bytes, icon.type, name)

                            db.collection("job_categories").add({
                                "name": name.strip(),
                                "description": desc.strip(),
                                "iconUrl": icon_url,   # https:// URL — Flutter reads this
                                "icon": icon_url,      # same URL in both fields for compatibility
                                "created_at": firestore.SERVER_TIMESTAMP
                            })
                            st.success(f":white_check_mark: Category '{name}' added! Icon stored at Storage URL — will display in Flutter app immediately.")
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
            selected_cat = next((c for c in categories if c["Name"] == selected_cat_name), None)

            if selected_cat:
                with st.form("edit_category_form"):
                    st.info(f"Editing: **{selected_cat['Name']}**")
                    new_name = st.text_input("Category Name", value=selected_cat['Name'])
                    new_desc = st.text_area("Description", value=selected_cat['Description'])
                    st.markdown("**Current Icon:**")
                    if selected_cat['Icon']:
                        st.image(selected_cat['Icon'], width=60)
                    new_icon = st.file_uploader(
                        f"Upload New Icon (Optional • max {MAX_ICON_SIZE_MB}MB)",
                        type=['png', 'jpg', 'jpeg'],
                        key="edit_cat_icon"
                    )

                    if st.form_submit_button("Update Category", type="primary"):
                        if new_name:
                            try:
                                update_data = {
                                    "name": new_name.strip(),
                                    "description": new_desc.strip()
                                }
                                if new_icon:
                                    raw_bytes = new_icon.getvalue()
                                    if len(raw_bytes) > MAX_ICON_BYTES:
                                        st.error(f":x: File too large ({len(raw_bytes)/1024/1024:.1f}MB). Maximum is {MAX_ICON_SIZE_MB}MB.")
                                        st.stop()

                                    with st.spinner("Uploading new icon to Firebase Storage..."):
                                        # ✅ FIX: upload to Storage → get https:// URL
                                        icon_url = upload_icon_to_storage(raw_bytes, new_icon.type, new_name)
                                        # Clean up the old Storage file if it was one
                                        if selected_cat['Icon']:
                                            delete_old_icon_from_storage(selected_cat['Icon'])

                                    update_data["iconUrl"] = icon_url
                                    update_data["icon"] = icon_url

                                db.collection("job_categories").document(selected_cat["id"]).update(update_data)
                                st.success(f":white_check_mark: Category '{new_name}' updated successfully!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating category: {e}")
                        else:
                            st.error("Category name cannot be empty.")

    # --- TAB 4: DELETE ---
    with tab4:
        st.markdown("### :wastebasket: Delete Category")
        if not categories:
            st.warning("No categories available to delete.")
        else:
            worker_counts_del = {}
            try:
                for doc in db.collection("workers").stream():
                    prof = doc.to_dict().get("profession", "").strip()
                    worker_counts_del[prof] = worker_counts_del.get(prof, 0) + 1
            except:
                worker_counts_del = {}

            del_cat_name = st.selectbox("Select Category to Delete", cat_names, key="del_cat_select")
            del_cat = next((c for c in categories if c["Name"] == del_cat_name), None)

            if del_cat:
                associated = worker_counts_del.get(del_cat["Name"], 0)

                col_prev, col_info = st.columns([1, 3])
                with col_prev:
                    if del_cat["Icon"]:
                        st.image(del_cat["Icon"], width=80)
                with col_info:
                    st.markdown(f"Name: {del_cat['Name']}")
                    st.markdown(f"Description: {del_cat['Description']}")
                    if associated > 0:
                        st.warning(f":warning: {associated} worker(s) are currently assigned to this category. "
                                   f"Deleting the category will NOT delete those workers, but their profession field "
                                   f"will become invalid.")
                    else:
                        st.success(":white_check_mark: No workers are assigned to this category. Safe to delete.")

                st.markdown("---")

                confirm_key = f"confirm_del_cat_{del_cat['id']}"
                if confirm_key not in st.session_state:
                    if st.button(":wastebasket: Delete This Category", type="primary", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.error(f":warning: Are you absolutely sure you want to delete '{del_cat['Name']}'? This cannot be undone.")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button(":fire: Yes, Delete It", type="primary", use_container_width=True):
                            try:
                                # Also delete the icon from Storage
                                if del_cat["Icon"]:
                                    delete_old_icon_from_storage(del_cat["Icon"])
                                db.collection("job_categories").document(del_cat["id"]).delete()
                                st.success(f":white_check_mark: Category '{del_cat['Name']}' deleted successfully.")
                                del st.session_state[confirm_key]
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting category: {e}")
                    with c_no:
                        if st.button(":x: Cancel", use_container_width=True):
                            del st.session_state[confirm_key]
                            st.rerun()

# ====================== Settings ======================
else:
    st.header(":gear: Settings & Info")
    st.success("Professional Admin Panel • 2026")
    st.info("""
    :white_check_mark: Icons uploaded to **Firebase Storage** → stored as `https://` URLs in Firestore
    :white_check_mark: Flutter's `CachedNetworkImage` works directly with these URLs — no changes needed in app
    :white_check_mark: Old base64 categories still display in admin (via `icon` fallback field)
    :white_check_mark: Delete category also cleans up the Storage file
    :white_check_mark: All features working
    """)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B;'>TCR Job Portal • Professional Admin Panel • 2026</p>", unsafe_allow_html=True)