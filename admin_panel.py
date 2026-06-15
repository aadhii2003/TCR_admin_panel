import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import pandas as pd
import base64
import base64 as b64lib
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
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1E3A8A; text-align: center; margin-bottom: 0.5rem; padding: 1rem 0; }
    .sub-header { font-size: 1.2rem; color: #64748B; text-align: center; margin-bottom: 2rem; }
    .metric-card { background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%); padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #3B82F6; }
    .stButton>button { border-radius: 8px; height: 3em; font-weight: 600; }
    section[data-testid="stSidebar"] { width: 320px !important; padding: 2rem 1rem; background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%); }
    .sidebar-title { font-size: 1.6rem; font-weight: 700; color: #60A5FA; margin-bottom: 2rem; text-align: center; padding-bottom: 1rem; border-bottom: 1px solid #1E293B; }
    .sidebar-footer { color: #94A3B8; font-size: 0.9rem; text-align: center; margin-top: 3rem; }
</style>
""", unsafe_allow_html=True)

# ====================== Header ======================
col_header1, col_header2 = st.columns([4, 1])
with col_header1:
    st.markdown('<h1 class="main-header">:wrench: TCR Job Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional Admin Dashboard • Manage Workers, Categories & Users</p>', unsafe_allow_html=True)
with col_header2:
    current_time = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    st.markdown(f'<div style="background:#F1F5F9;padding:1rem;border-radius:8px;margin-top:1rem;text-align:right;"><small style="color:#64748B;">{current_time}</small></div>', unsafe_allow_html=True)
st.markdown("---")

# ====================== Firebase Init ======================
# _BUCKET_NAME is set once here and passed explicitly to every storage.bucket() call.
# This avoids the "Storage bucket name not specified" error on Streamlit reruns.
_BUCKET_NAME = "tcr-app-3ca2e.firebasestorage.app"

if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            cfg = dict(st.secrets["firebase"])
            bn = cfg.pop("storageBucket", None) or st.secrets.get("storageBucket", "")
            if not bn:
                bn = f"{cfg.get('project_id', '')}.appspot.com"
            cred = credentials.Certificate(cfg)
            firebase_admin.initialize_app(cred, {"storageBucket": bn})
            _BUCKET_NAME = bn

        elif "project_id" in st.secrets:
            cfg = {k: st.secrets[k] for k in [
                "type","project_id","private_key_id","private_key",
                "client_email","client_id","auth_uri","token_uri",
                "auth_provider_x509_cert_url","client_x509_cert_url"
            ]}
            bn = st.secrets.get("storageBucket", f"{st.secrets['project_id']}.appspot.com")
            cred = credentials.Certificate(cfg)
            firebase_admin.initialize_app(cred, {"storageBucket": bn})
            _BUCKET_NAME = bn

        elif os.path.exists("tcr-serviceAccountKey.json"):
            import json
            with open("tcr-serviceAccountKey.json") as f:
                sa = json.load(f)
            bn = sa.get("storageBucket", f"{sa['project_id']}.appspot.com")
            cred = credentials.Certificate("tcr-serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {"storageBucket": bn})
            _BUCKET_NAME = bn

        else:
            st.error(":red_circle: Firebase credentials not found!")
            st.info("Add your Firebase service account JSON to Streamlit Cloud Secrets.")
            st.stop()

    except Exception as e:
        st.error(f":red_circle: Firebase initialization failed: {e}")
        st.stop()

else:
    # App already initialised on a Streamlit rerun — recover the bucket name
    _BUCKET_NAME = firebase_admin.get_app().options.get("storageBucket", "")

if not _BUCKET_NAME:
    st.error(":red_circle: storageBucket is blank. Add it to your Streamlit secrets as `storageBucket = \"your-project.appspot.com\"`")
    st.stop()

db = firestore.client()


# ====================== Storage helpers ======================
MAX_ICON_SIZE_MB  = 5
MAX_ICON_BYTES    = MAX_ICON_SIZE_MB * 1024 * 1024
ICON_MAX_DIMENSION = 256


def _get_bucket():
    """Always pass the explicit bucket name — never rely on SDK default."""
    return storage.bucket(_BUCKET_NAME)


def resize_image_bytes(file_bytes: bytes, mime_type: str) -> tuple[bytes, str]:
    img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    img.thumbnail((ICON_MAX_DIMENSION, ICON_MAX_DIMENSION), Image.LANCZOS)
    buf = io.BytesIO()
    if mime_type == "image/png":
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "image/png"
    else:
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        bg.save(buf, format="JPEG", quality=85, optimize=True)
        return buf.getvalue(), "image/jpeg"


def upload_icon_to_storage(file_bytes: bytes, mime_type: str, category_name: str) -> str:
    resized_bytes, final_mime = resize_image_bytes(file_bytes, mime_type)
    ext = "png" if final_mime == "image/png" else "jpg"
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', category_name.strip().lower())
    filename = f"category_icons/{safe_name}_{uuid.uuid4().hex[:8]}.{ext}"

    bucket = _get_bucket()
    blob = bucket.blob(filename)
    blob.upload_from_string(resized_bytes, content_type=final_mime)
    blob.make_public()
    return blob.public_url


def delete_old_icon_from_storage(icon_url: str):
    """Delete an old Storage icon. Fixed slice bug: was [n] (one char), now [n:] (full path)."""
    try:
        if "storage.googleapis.com" not in icon_url:
            return
        prefix = f"https://storage.googleapis.com/{_BUCKET_NAME}/"
        if icon_url.startswith(prefix):
            blob_path = icon_url[len(prefix):].split("?")[0]   # ✅ fixed
            _get_bucket().blob(blob_path).delete()
    except Exception:
        pass


# ====================== General helpers ======================
DEFAULT_PHOTO = "https://firebasestorage.googleapis.com/v0/b/placeholder-images.appspot.com/o/default-avatar.png?alt=media"


def format_date(ts_ms):
    if ts_ms is None:
        return "N/A"
    try:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
        dt_ist = dt.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
        return dt_ist.strftime("%b %d, %Y")
    except Exception:
        return "Invalid"


def clean_value(val):
    return str(val).strip("<> ") if val is not None and pd.notna(val) else "N/A"


def list_to_string(val):
    if isinstance(val, list):
        return ", ".join(clean_value(i) for i in val if i)
    return clean_value(val)


def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(email).strip()) is not None


def parse_coordinate(val):
    if pd.isna(val) or str(val).strip() == "":
        return 0.0
    s = str(val).strip()
    try:
        return float(s)
    except Exception:
        pass
    m = re.search(r"(\d+)\D+(\d+)\D+(\d+(?:\.\d+)?)\D*([NSEW])", s, re.IGNORECASE)
    if m:
        d, mn, sv, direction = m.groups()
        dec = float(d) + float(mn) / 60 + float(sv) / 3600
        if direction.upper() in ("S", "W"):
            dec = -dec
        return dec
    m2 = re.search(r"(\d+(?:\.\d+)?)\D*([NSEW])", s, re.IGNORECASE)
    if m2:
        v, direction = m2.groups()
        dec = float(v)
        if direction.upper() in ("S", "W"):
            dec = -dec
        return dec
    return None


# ====================== User helpers ======================
def delete_user_account(uid):
    try:
        db.collection("workers").document(uid).delete()
        db.collection("user_profiles").document(uid).delete()
        auth.delete_user(uid)
        return True, "User successfully deleted from Authentication and Database."
    except Exception as e:
        return False, f"Error deleting user: {str(e)}"


# ====================== Category helpers ======================
@st.cache_data(ttl=300)
def get_job_categories_with_details():
    try:
        categories = []
        for doc in db.collection("job_categories").order_by("name").stream():
            data = doc.to_dict()
            name = data.get("name", "").strip()
            icon_url = (data.get("iconUrl") or "").strip()
            icon_fallback = (data.get("icon") or "").strip()
            icon = icon_url if icon_url.startswith("https://") else (icon_fallback if icon_fallback.startswith("https://") else None)
            if name:
                categories.append({
                    "id": doc.id,
                    "Name": name,
                    "Icon": icon,
                    "Description": data.get("description", "") or "No description",
                    "_iconUrl_raw": icon_url,
                    "_icon_raw": icon_fallback,
                })
        return categories
    except Exception as e:
        st.error(f"Error loading categories: {e}")
        return []


# ====================== Sidebar ======================
with st.sidebar:
    st.markdown('<div style="text-align:center;margin-bottom:2rem;"><h2>:wrench: TCR Admin</h2></div>', unsafe_allow_html=True)
    st.markdown('<p class="sidebar-title">:clipboard: Menu Options</p>', unsafe_allow_html=True)
    page = st.radio(
        "Select Section",
        [":bar_chart: Dashboard", ":busts_in_silhouette: Users/Employees", ":hammer_and_wrench: Job Categories", ":gear: Settings"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown('<p class="sidebar-title">:chart_with_upwards_trend: Quick Stats</p>', unsafe_allow_html=True)
    try:
        total_users    = len(list(auth.list_users().iterate_all()))
        active_users_n = sum(1 for u in auth.list_users().iterate_all() if u.user_metadata.last_sign_in_timestamp)
        total_cats     = len(get_job_categories_with_details())
        c1, c2 = st.columns(2)
        c1.metric("Users", total_users)
        c2.metric("Active", active_users_n)
        st.metric("Categories", total_cats)
    except Exception:
        st.caption("Stats unavailable")
    st.markdown("---")
    st.markdown('<p class="sidebar-footer">© 2026 TCR Job Portal<br>Professional Admin System</p>', unsafe_allow_html=True)


# ====================== Dashboard ======================
if page == ":bar_chart: Dashboard":
    st.header(":bar_chart: Dashboard Overview")
    c1, c2, c3, c4 = st.columns(4)
    for col, label, fn in [
        (c1, "Total Users",    lambda: len(list(auth.list_users().iterate_all()))),
        (c2, "Active Users",   lambda: sum(1 for u in auth.list_users().iterate_all() if u.user_metadata.last_sign_in_timestamp)),
        (c3, "Inactive Users", lambda: sum(1 for u in auth.list_users().iterate_all() if not u.user_metadata.last_sign_in_timestamp)),
        (c4, "Job Categories", lambda: len(get_job_categories_with_details())),
    ]:
        with col:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            try: st.metric(label, fn())
            except: st.metric(label, 0)
            st.markdown('</div>', unsafe_allow_html=True)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try: st.metric("Registered Workers", sum(1 for _ in db.collection("workers").stream()))
        except: st.metric("Registered Workers", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with c6:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try: st.metric("User Profiles", sum(1 for _ in db.collection("user_profiles").stream()))
        except: st.metric("User Profiles", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with c7:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            recent = sum(
                1 for u in auth.list_users().iterate_all()
                if u.user_metadata.last_sign_in_timestamp and
                datetime.datetime.fromtimestamp(u.user_metadata.last_sign_in_timestamp / 1000) >= seven_days_ago
            )
            st.metric("Active This Week", recent)
        except: st.metric("Active This Week", 0)
        st.markdown('</div>', unsafe_allow_html=True)
    with c8:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        try:
            total_r = total_w = 0
            for doc in db.collection("workers").stream():
                d = doc.to_dict()
                if d.get("rating") is not None:
                    total_r += float(d["rating"]); total_w += 1
            st.metric("Avg Rating", f"{round(total_r/total_w,2) if total_w else 0}★")
        except: st.metric("Avg Rating", "0★")
        st.markdown('</div>', unsafe_allow_html=True)


# ====================== Users / Employees ======================
elif page == ":busts_in_silhouette: Users/Employees":
    st.header(":busts_in_silhouette: Users/Employees Management")

    cs1, cs2, cs3 = st.columns([3, 2, 2])
    search_term      = cs1.text_input(":mag: Search Users", placeholder="Name, email, profession...")
    role_filter      = cs2.selectbox("Role", ["All", "Worker", "User"])
    profession_filter = cs3.selectbox("Profession", ["All"] + [c["Name"] for c in get_job_categories_with_details()])

    tab1, tab2, tab3 = st.tabs([":white_check_mark: Active Users", ":x: Inactive Users", ":outbox_tray: Bulk Import"])

    def get_full_profile(uid):
        w = db.collection("workers").document(uid).get()
        u = db.collection("user_profiles").document(uid).get()
        if w.exists: return w.to_dict(), "Worker"
        if u.exists: return u.to_dict(), "User"
        return {}, "Unknown"

    @st.cache_data(ttl=60)
    def load_users_optimized():
        rows = []
        try:
            workers_ref  = {d.id: d.to_dict() for d in db.collection("workers").stream()}
            profiles_ref = {d.id: d.to_dict() for d in db.collection("user_profiles").stream()}
            for au in auth.list_users().iterate_all():
                uid = au.uid
                profile, role = {}, "Unknown"
                if uid in workers_ref:   profile, role = workers_ref[uid],  "Worker"
                elif uid in profiles_ref: profile, role = profiles_ref[uid], "User"
                else:                    role = ":warning: Orphaned (No Profile)"
                lsi = au.user_metadata.last_sign_in_timestamp
                rows.append({
                    "UID": uid, "IsActive": lsi is not None,
                    "Name": clean_value(profile.get("name", au.email)),
                    "Email": clean_value(au.email), "Role": role,
                    "Mobile": clean_value(profile.get("mobile", "N/A")),
                    "Profession": clean_value(profile.get("profession", "N/A")),
                    "Hourly Rate": f"₹{profile.get('hourlyRate',0)}" if profile.get('hourlyRate') else "N/A",
                    "Rating": f"{profile.get('rating',0)}★",
                    "Experience": f"{profile.get('experienceYears',0)} yrs",
                    "Last Login": format_date(lsi) if lsi else "Never",
                    "Last Login TS": lsi or 0,
                })
        except Exception as e:
            st.error(f"Error loading users: {e}")
        return rows

    all_users_raw = load_users_optimized()

    def filter_and_split(users):
        active, inactive = [], []
        for u in users:
            if search_term:
                s = search_term.lower()
                if s not in str(u["Name"]).lower() and s not in str(u["Email"]).lower() and s not in str(u["Profession"]).lower():
                    continue
            if role_filter != "All" and u["Role"] != role_filter: continue
            if profession_filter != "All" and u["Profession"] != profession_filter: continue
            row = {**u, "Select": False}
            (active if u["IsActive"] else inactive).append(row)
        return active, inactive

    active_users, inactive_users = filter_and_split(all_users_raw)

    with tab1:
        st.subheader(":white_check_mark: Active Users")
        if "selected_uid" in st.session_state and st.session_state.selected_uid:
            uid = st.session_state.selected_uid
            try:
                profile, role = get_full_profile(uid)
                if not profile or role == "Unknown": raise Exception("No profile")
                st.markdown("---")
                pc1, pc2 = st.columns([1, 4])
                with pc1:
                    photo = clean_value(profile.get("profilePhoto", DEFAULT_PHOTO))
                    st.image(photo if photo != "N/A" else DEFAULT_PHOTO, width=150, caption="Profile Photo")
                with pc2:
                    st.markdown(f"### {clean_value(profile.get('name','N/A'))}")
                    st.markdown(f"{role} • {clean_value(profile.get('profession','N/A'))}")
                    d1, d2, d3 = st.columns(3)
                    d1.markdown(f":star: {profile.get('rating',0)} | :briefcase: {profile.get('totalJobs',0)} jobs")
                    d2.markdown(f":moneybag: ₹{profile.get('hourlyRate',0)}/hr")
                    d3.markdown(f":date: {profile.get('experienceYears',0)} yrs")
                st.markdown("---")
                i1, i2, i3 = st.columns(3)
                with i1:
                    st.markdown("Email");    st.markdown(clean_value(profile.get("email","N/A")))
                    st.markdown("Mobile");   st.markdown(clean_value(profile.get("mobile","N/A")))
                    st.markdown("Location"); st.markdown(clean_value(profile.get("location","N/A")))
                with i2:
                    st.markdown("Languages"); st.markdown(list_to_string(profile.get("languages",[])))
                    addr = ", ".join(p for p in [str(profile.get(k,"")).strip() for k in ["address","city","state"]] if p and p.lower() not in ("n/a","none",""))
                    st.markdown("Address"); st.markdown(addr or "N/A")
                with i3:
                    st.markdown("About");  st.markdown(f"_{clean_value(profile.get('about','No bio'))}_")
                    st.markdown("Status"); st.markdown(":white_check_mark: Available" if profile.get("isAvailable") else ":x: Not Available")

                b1, b2 = st.columns(2)
                with b1:
                    ck = f"confirm_delete_{uid}"
                    if ck not in st.session_state:
                        if st.button(":wastebasket: Delete User Account", type="primary", use_container_width=True):
                            st.session_state[ck] = True; st.rerun()
                    else:
                        st.warning(":warning: Are you sure? This will delete the user from Auth and Database.")
                        y, n = st.columns(2)
                        with y:
                            if st.button(":fire: Confirm", type="primary", use_container_width=True):
                                ok, msg = delete_user_account(uid)
                                if ok:
                                    st.success(msg); del st.session_state.selected_uid; del st.session_state[ck]
                                    st.cache_data.clear(); st.rerun()
                                else: st.error(msg)
                        with n:
                            if st.button(":x: Cancel", use_container_width=True):
                                del st.session_state[ck]; st.rerun()
                with b2:
                    if st.button(":x: Close Profile", type="secondary", use_container_width=True, key="close_profile_btn"):
                        del st.session_state.selected_uid; st.rerun()
            except Exception:
                st.error(":warning: Profile data missing. User may have been partially deleted.")
                e1, e2 = st.columns(2)
                with e1:
                    if st.button(":wastebasket: Force Delete from Auth", type="primary", use_container_width=True):
                        ok, msg = delete_user_account(uid)
                        if ok:
                            st.success(msg); del st.session_state.selected_uid
                            st.cache_data.clear(); st.rerun()
                        else: st.error(msg)
                with e2:
                    if st.button(":x: Close", type="secondary", use_container_width=True, key="close_error_btn"):
                        if "selected_uid" in st.session_state: del st.session_state.selected_uid
                        st.rerun()

        if active_users:
            df = pd.DataFrame(active_users)
            edited = st.data_editor(df,
                column_config={"Select": st.column_config.CheckboxColumn("Select", width="small"), "UID": None},
                hide_index=True, use_container_width=True, key="active_table")
            sel = edited[edited["Select"]]
            if st.button(":eyes: View Profile", type="primary", disabled=len(sel) != 1, use_container_width=True):
                st.session_state.selected_uid = sel.iloc[0]["UID"]; st.rerun()
            st.dataframe(edited.drop(columns=["Select","UID"]), use_container_width=True, hide_index=True)
        else:
            st.info("No active users found.")

    with tab2:
        st.subheader(":x: Inactive Users")
        if inactive_users:
            st.dataframe(pd.DataFrame(inactive_users).drop(columns=["UID"]), use_container_width=True, hide_index=True)
            st.caption("These users will move to Active tab after first login.")
        else:
            st.info("No inactive users.")

    with tab3:
        st.markdown("### :outbox_tray: Bulk Import Workers from Excel")
        worker_columns = ["name","email","mobile","whatsapp","address","city","state","gender",
                          "profession","hourlyRate","experienceYears","about","languages","latitude","longitude"]
        job_categories = [c["Name"] for c in get_job_categories_with_details()]
        ref_df = pd.DataFrame({"Available Job Categories": job_categories + [""]*max(0, 20-len(job_categories))})
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as w:
            pd.DataFrame(columns=worker_columns).to_excel(w, index=False, sheet_name="Workers")
            ref_df.to_excel(w, index=False, sheet_name="Job_Categories_Reference")
        out.seek(0)
        b64e = base64.b64encode(out.read()).decode()
        st.markdown(f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64e}" download="TCR_Workers_Template.xlsx">:inbox_tray: Download Template</a>', unsafe_allow_html=True)
        st.info("Use exact profession names from Job_Categories_Reference sheet • Default password: TempPass123!")
        if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0
        uploaded = st.file_uploader("Upload Filled Excel", type=["xlsx"], key=f"uploader_{st.session_state.uploader_key}")
        if uploaded:
            try:
                df = pd.read_excel(uploaded, sheet_name="Workers")
                req = ["name","email","mobile","profession"]
                miss = [c for c in req if c not in df.columns]
                if miss: st.error(f"Missing columns: {', '.join(miss)}"); st.stop()
                existing_emails, existing_mobiles = set(), set()
                try:
                    for u in auth.list_users().iterate_all(): existing_emails.add(u.email.lower())
                except: pass
                try:
                    for doc in db.collection("workers").stream():
                        mob = str(doc.to_dict().get("mobile","")).strip()
                        if mob.isdigit() and len(mob)==10: existing_mobiles.add(mob)
                except: pass
                professions = {c["Name"].strip() for c in get_job_categories_with_details()}
                valid_rows, invalid_rows = [], []
                for idx, row in df.iterrows():
                    rd = row.to_dict()
                    errors = []
                    name   = str(rd.get("name","")).strip()
                    email  = str(rd.get("email","")).strip().lower()
                    mobile = str(rd.get("mobile","")).strip()
                    prof   = str(rd.get("profession","")).strip()
                    if not name:  errors.append("Name required")
                    if not email: errors.append("Email required")
                    elif not is_valid_email(email): errors.append("Invalid email")
                    elif email in existing_emails:  errors.append("Email already exists")
                    if not mobile: errors.append("Mobile required")
                    elif not mobile.isdigit() or len(mobile)!=10: errors.append("Mobile must be 10 digits")
                    elif mobile in existing_mobiles: errors.append("Mobile already registered")
                    if not prof: errors.append("Profession required")
                    elif prof not in professions: errors.append(f"Invalid profession: '{prof}'")
                    if pd.notna(rd.get("latitude"))  and parse_coordinate(rd.get("latitude"))  is None: errors.append("Invalid Latitude")
                    if pd.notna(rd.get("longitude")) and parse_coordinate(rd.get("longitude")) is None: errors.append("Invalid Longitude")
                    rd["Row"] = idx+2; rd["Status"] = "Invalid" if errors else "Valid"
                    rd["Error Details"] = " | ".join(errors) if errors else "-"
                    (invalid_rows if errors else valid_rows).append(rd)
                    if not errors: existing_emails.add(email); existing_mobiles.add(mobile)
                v1, v2 = st.columns(2)
                v1.success(f"{len(valid_rows)} valid"); v2.error(f"{len(invalid_rows)} errors") if invalid_rows else None
                if valid_rows:
                    st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True)
                    if st.button("Import All Valid Workers", type="primary", use_container_width=True):
                        with st.spinner("Importing..."):
                            ok_count = 0
                            for r in valid_rows:
                                try:
                                    u = auth.create_user(email=r["email"], password="TempPass123!")
                                    si = lambda v: int(float(v)) if pd.notna(v) else 0
                                    sf = lambda v: (parse_coordinate(v) or 0.0)
                                    lat, lon = sf(r.get("latitude")), sf(r.get("longitude"))
                                    db.collection("workers").document(u.uid).set({
                                        "name": r["name"], "email": r["email"],
                                        "mobile": str(r["mobile"]), "whatsapp": str(r.get("whatsapp","")),
                                        "address": str(r.get("address","")), "city": str(r.get("city","")),
                                        "state": str(r.get("state","")), "gender": str(r.get("gender","")),
                                        "profession": r["profession"], "hourlyRate": si(r.get("hourlyRate")),
                                        "experienceYears": si(r.get("experienceYears")),
                                        "latitude": lat, "longitude": lon,
                                        "location": {"latitude": lat, "longitude": lon},
                                        "locationUpdatedAt": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5,minutes=30))).isoformat(),
                                        "about": str(r.get("about","")),
                                        "languages": [l.strip() for l in str(r.get("languages","")).split(",") if l.strip()],
                                        "profilePhoto": DEFAULT_PHOTO, "isAvailable": True,
                                        "rating": 0.0, "totalJobs": 0, "createdAt": firestore.SERVER_TIMESTAMP,
                                    }); ok_count += 1
                                except Exception as e: st.error(f"Failed {r['email']}: {e}")
                        st.success(f"Imported {ok_count} workers!"); st.balloons()
                        st.session_state.uploader_key += 1; st.rerun()
                if invalid_rows:
                    st.markdown("#### Invalid Rows")
                    st.dataframe(pd.DataFrame(invalid_rows)[["Row","name","email","mobile","profession","Error Details"]], use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error reading Excel: {e}")


# ====================== Job Categories ======================
elif page == ":hammer_and_wrench: Job Categories":
    st.header(":hammer_and_wrench: Job Categories Management")
    categories = get_job_categories_with_details()
    cat_names  = [c["Name"] for c in categories]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":open_file_folder: View All",
        ":heavy_plus_sign: Add New",
        ":pencil2: Edit Existing",
        ":wastebasket: Delete",
        ":wrench: Fix Old Icons",
    ])

    # ── TAB 1: VIEW ──────────────────────────────────────────────────────────
    with tab1:
        st.markdown("### All Job Categories")
        search_cat = st.text_input("Search", placeholder="Type to filter...", key="search_cat_main")
        filtered = [c for c in categories if search_cat.lower() in c["Name"].lower()] if search_cat else categories
        wc = {}
        try:
            for doc in db.collection("workers").stream():
                p = doc.to_dict().get("profession","").strip()
                wc[p] = wc.get(p,0) + 1
        except: pass
        if filtered:
            st.dataframe(
                pd.DataFrame([{"Icon": c["Icon"], "Category Name": c["Name"], "Workers": wc.get(c["Name"],0), "Description": c["Description"]} for c in filtered]),
                column_config={
                    "Icon": st.column_config.ImageColumn("Icon", width="small"),
                    "Category Name": st.column_config.TextColumn("Category Name"),
                    "Workers": st.column_config.NumberColumn("Workers", format="%d"),
                    "Description": st.column_config.TextColumn("Description"),
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No categories found.")

    # ── TAB 2: ADD ───────────────────────────────────────────────────────────
    with tab2:
        st.markdown("### Add New Category")
        st.info(":pushpin: Icon uploads to **Firebase Storage** and is stored as an `https://` URL — Flutter reads this directly.")
        with st.form("add_category_form"):
            ac1, ac2 = st.columns([2,1])
            name = ac1.text_input("Category Name*", placeholder="e.g., Electrician")
            desc = ac2.text_area("Description")
            icon_file = st.file_uploader(f"Upload Icon* (PNG/JPG • max {MAX_ICON_SIZE_MB}MB)", type=["png","jpg","jpeg"], key="add_cat_icon")
            if st.form_submit_button("Add Category", type="primary"):
                if name and icon_file:
                    raw = icon_file.getvalue()
                    if len(raw) > MAX_ICON_BYTES:
                        st.error(f":x: File too large ({len(raw)/1024/1024:.1f}MB).")
                    else:
                        try:
                            with st.spinner("Uploading to Firebase Storage..."):
                                url = upload_icon_to_storage(raw, icon_file.type, name)
                            db.collection("job_categories").add({
                                "name": name.strip(), "description": desc.strip(),
                                "iconUrl": url, "icon": url,
                                "created_at": firestore.SERVER_TIMESTAMP,
                            })
                            st.success(f":white_check_mark: '{name}' added!"); st.cache_data.clear(); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
                else:
                    st.warning("Name and icon are required.")

    # ── TAB 3: EDIT ──────────────────────────────────────────────────────────
    with tab3:
        st.markdown("### Edit Existing Category")
        if not categories:
            st.warning("No categories to edit.")
        else:
            sel_name = st.selectbox("Select Category", cat_names, key="edit_cat_select")
            sel_cat  = next((c for c in categories if c["Name"] == sel_name), None)
            if sel_cat:
                with st.form("edit_category_form"):
                    st.info(f"Editing: **{sel_cat['Name']}**")
                    new_name = st.text_input("Category Name", value=sel_cat["Name"])
                    new_desc = st.text_area("Description", value=sel_cat["Description"])
                    st.markdown("**Current Icon:**")
                    if sel_cat["Icon"]:
                        st.image(sel_cat["Icon"], width=60)
                    else:
                        st.caption("⚠️ No valid icon URL — run 'Fix Old Icons' tab first.")
                    new_icon = st.file_uploader(f"Upload New Icon (optional • max {MAX_ICON_SIZE_MB}MB)", type=["png","jpg","jpeg"], key="edit_cat_icon")
                    if st.form_submit_button("Update Category", type="primary"):
                        if not new_name: st.error("Name cannot be empty.")
                        else:
                            try:
                                upd = {"name": new_name.strip(), "description": new_desc.strip()}
                                if new_icon:
                                    raw = new_icon.getvalue()
                                    if len(raw) > MAX_ICON_BYTES: st.error("File too large."); st.stop()
                                    with st.spinner("Uploading..."):
                                        url = upload_icon_to_storage(raw, new_icon.type, new_name)
                                        delete_old_icon_from_storage(sel_cat["_iconUrl_raw"] or sel_cat["_icon_raw"] or "")
                                    upd["iconUrl"] = url; upd["icon"] = url
                                db.collection("job_categories").document(sel_cat["id"]).update(upd)
                                st.success(f":white_check_mark: '{new_name}' updated!"); st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

    # ── TAB 4: DELETE ─────────────────────────────────────────────────────────
    with tab4:
        st.markdown("### :wastebasket: Delete Category")
        if not categories:
            st.warning("No categories to delete.")
        else:
            wc_del = {}
            try:
                for doc in db.collection("workers").stream():
                    p = doc.to_dict().get("profession","").strip(); wc_del[p] = wc_del.get(p,0)+1
            except: pass
            del_name = st.selectbox("Select Category to Delete", cat_names, key="del_cat_select")
            del_cat  = next((c for c in categories if c["Name"] == del_name), None)
            if del_cat:
                assoc = wc_del.get(del_cat["Name"], 0)
                dp1, dp2 = st.columns([1,3])
                with dp1:
                    if del_cat["Icon"]: st.image(del_cat["Icon"], width=80)
                with dp2:
                    st.markdown(f"**{del_cat['Name']}** — {del_cat['Description']}")
                    if assoc > 0: st.warning(f":warning: {assoc} worker(s) assigned. Profession field will become invalid.")
                    else: st.success(":white_check_mark: No workers assigned. Safe to delete.")
                st.markdown("---")
                ck = f"confirm_del_cat_{del_cat['id']}"
                if ck not in st.session_state:
                    if st.button(":wastebasket: Delete This Category", type="primary", use_container_width=True):
                        st.session_state[ck] = True; st.rerun()
                else:
                    st.error(f":warning: Permanently delete '{del_cat['Name']}'?")
                    dy, dn = st.columns(2)
                    with dy:
                        if st.button(":fire: Yes, Delete It", type="primary", use_container_width=True):
                            try:
                                delete_old_icon_from_storage(del_cat["_iconUrl_raw"] or del_cat["_icon_raw"] or "")
                                db.collection("job_categories").document(del_cat["id"]).delete()
                                st.success(f"'{del_cat['Name']}' deleted."); del st.session_state[ck]
                                st.cache_data.clear(); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    with dn:
                        if st.button(":x: Cancel", use_container_width=True):
                            del st.session_state[ck]; st.rerun()

    # ── TAB 5: FIX OLD ICONS (base64 → Storage migration) ────────────────────
    with tab5:
        st.markdown("### :wrench: Fix Old Icons — Migrate Base64 → Firebase Storage")
        st.warning(
            "**Run this once.** Finds every category still storing a base64 image, "
            "uploads it to Firebase Storage, and writes the `https://` URL back to Firestore. "
            "Your Flutter app will show icons immediately — no app update needed."
        )

        # Status table
        st.markdown("#### Current Status of All Categories")
        all_docs = list(db.collection("job_categories").stream())
        status_rows = []
        for doc in all_docs:
            d = doc.to_dict()
            iu  = (d.get("iconUrl") or "").strip()
            ib  = (d.get("icon")    or "").strip()
            has_valid_url = iu.startswith("https://")
            has_base64    = bool(ib) and not ib.startswith("https://")
            status_rows.append({
                "Category":        d.get("name", doc.id),
                "iconUrl field":   "✅ https://" if has_valid_url else "❌ Missing/invalid",
                "icon field":      "⚠️ base64"   if has_base64  else ("✅ https://" if ib.startswith("https://") else "➖ empty"),
                "Needs Migration": "YES"          if (not has_valid_url and has_base64) else "No",
                "_doc_id": doc.id, "_icon_raw": ib,
            })
        display_df = pd.DataFrame(status_rows).drop(columns=["_doc_id","_icon_raw"])
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        to_migrate = [r for r in status_rows if r["Needs Migration"] == "YES"]
        if not to_migrate:
            st.success(":white_check_mark: All categories already have valid `https://` Storage URLs. Nothing to do!")
        else:
            st.error(f"**{len(to_migrate)} categories** need migration.")

        st.markdown("---")
        if st.button(
            f"🚀 Migrate {len(to_migrate)} Categories Now" if to_migrate else "✅ Nothing to Migrate",
            type="primary", use_container_width=True, disabled=(len(to_migrate) == 0)
        ):
            prog = st.progress(0)
            results = []
            for i, row in enumerate(to_migrate):
                cat_name  = row["Category"]
                raw_value = row["_icon_raw"]
                doc_id    = row["_doc_id"]
                try:
                    # Support both  "data:image/png;base64,ABC..."  and raw base64
                    if raw_value.startswith("data:"):
                        header, b64_data = raw_value.split(",", 1)
                        mime_type = header.split(":")[1].split(";")[0]
                    else:
                        b64_data  = raw_value
                        mime_type = "image/png"

                    file_bytes = b64lib.b64decode(b64_data)

                    with st.spinner(f"Uploading '{cat_name}'..."):
                        new_url = upload_icon_to_storage(file_bytes, mime_type, cat_name)

                    db.collection("job_categories").document(doc_id).update({
                        "iconUrl": new_url,   # Flutter reads this first
                        "icon":    new_url,   # overwrite base64 so it's never used again
                    })
                    results.append({"Category": cat_name, "Result": "✅ Migrated", "URL": new_url})

                except Exception as e:
                    results.append({"Category": cat_name, "Result": f"❌ Failed: {e}", "URL": ""})

                prog.progress((i + 1) / len(to_migrate))

            migrated = sum(1 for r in results if r["Result"].startswith("✅"))
            st.success(f"Done! {migrated}/{len(to_migrate)} migrated.")
            st.cache_data.clear()

            st.markdown("#### Results")
            for r in results:
                c1, c2, c3 = st.columns([3, 4, 1])
                c1.write(r["Category"]); c2.write(r["Result"])
                if r["URL"]: c3.image(r["URL"], width=48)

            st.info(":iphone: Open your Flutter app — icons appear in seconds via the live Firestore stream. No app update needed.")


# ====================== Settings ======================
else:
    st.header(":gear: Settings & Info")
    st.success("Professional Admin Panel • 2026")
    st.info(f"""
    :white_check_mark: Connected to Storage bucket: `{_BUCKET_NAME}`
    :white_check_mark: Icons stored as `https://` URLs in Firestore — Flutter's CachedNetworkImage reads them directly
    :white_check_mark: Run **Job Categories → Fix Old Icons** once to migrate any base64 icons
    :white_check_mark: `delete_old_icon_from_storage` slice bug fixed (`[n]` → `[n:]`)
    :white_check_mark: `storageBucket` now passed explicitly to every `storage.bucket()` call — no more "bucket not specified" errors
    """)

st.markdown("---")
st.markdown("<p style='text-align:center;color:#64748B;'>TCR Job Portal • Professional Admin Panel • 2026</p>", unsafe_allow_html=True)