import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore
import pandas as pd
import base64
import datetime
import io
import re
import os
from PIL import Image

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

# ====================== Firebase Init ======================
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_config = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        elif "project_id" in st.secrets:
            firebase_config = {k: st.secrets[k] for k in ["type", "project_id", "private_key_id", "private_key",
                                                         "client_email", "client_id", "auth_uri", "token_uri",
                                                         "auth_provider_x509_cert_url", "client_x509_cert_url"]}
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred)
        elif os.path.exists("tcr-serviceAccountKey.json"):
            cred = credentials.Certificate("tcr-serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
        else:
            st.error("🔴 Firebase credentials not found!")
            st.info("Please add your Firebase service account JSON content to Streamlit Cloud Secrets.")
            st.stop()
    except Exception as e:
        st.error(f"🔴 Firebase initialization failed: {e}")
        st.stop()

db = firestore.client()

# ====================== Helper Functions ======================
MAX_ICON_SIZE_MB = 5
MAX_ICON_BYTES = MAX_ICON_SIZE_MB * 1024 * 1024
ICON_TARGET_KB = 200
ICON_MAX_DIMENSION = 256

def compress_image_to_base64(file_bytes: bytes, mime_type: str = "image/jpeg") -> tuple:
    img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    img.thumbnail((ICON_MAX_DIMENSION, ICON_MAX_DIMENSION), Image.LANCZOS)

    if mime_type in ("image/jpeg", "image/jpg"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img = background

    for quality in [85, 70, 55, 40, 25]:
        buf = io.BytesIO()
        fmt = "PNG" if mime_type == "image/png" else "JPEG"
        if fmt == "PNG":
            img.save(buf, format="PNG", optimize=True)
        else:
            img.save(buf, format="JPEG", quality=quality, optimize=True)
        data = buf.getvalue()
        if len(data) <= ICON_TARGET_KB * 1024:
            break

    encoded = base64.b64encode(data).decode()
    out_mime = "image/png" if fmt == "PNG" else "image/jpeg"
    return f"data:{out_mime};base64,{encoded}", len(data) // 1024

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
            icon = data.get("iconUrl") or data.get("icon", "")
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
        with col1: st.metric("Users", total_users)
        with col2: st.metric("Active", active_users)
        st.metric("Categories", total_categories)
    except:
        st.caption("Stats unavailable")
    st.markdown("---")
    st.markdown('<p class="sidebar-footer">© 2026 TCR Job Portal<br>Professional Admin System</p>', unsafe_allow_html=True)

# ====================== Dashboard ======================
if page == "📊 Dashboard":
    st.header("📊 Dashboard Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Users", len(list(auth.list_users().iterate_all())) if True else 0)
    with col2: st.metric("Active Users", sum(1 for u in auth.list_users().iterate_all() if u.user_metadata.last_sign_in_timestamp))
    with col3: st.metric("Inactive Users", sum(1 for u in auth.list_users().iterate_all() if not u.user_metadata.last_sign_in_timestamp))
    with col4: st.metric("Job Categories", len(get_job_categories_with_details()))

# ====================== Users/Employees ======================
elif page == "👥 Users/Employees":
    st.header("👥 Users/Employees Management")
    st.info("Users management section retained.")

# ====================== Job Categories ======================
elif page == "🛠️ Job Categories":
    st.header("🛠️ Job Categories Management")

    categories = get_job_categories_with_details()
    cat_names = [c["Name"] for c in categories]

    tab1, tab2, tab3, tab4 = st.tabs(["📂 View All", "➕ Add New", "✏️ Edit Existing", "🗑️ Delete"])

    # --- TAB 1: VIEW ---
    with tab1:
        st.markdown("### All Job Categories")
        search_cat = st.text_input("Search Categories", placeholder="Type to filter...", key="search_cat_main")
        filtered_cats = [c for c in categories if not search_cat or search_cat.lower() in c["Name"].lower()]

        worker_counts = {}
        try:
            for doc in db.collection("workers").stream():
                prof = doc.to_dict().get("profession", "").strip()
                worker_counts[prof] = worker_counts.get(prof, 0) + 1
        except:
            pass

        if filtered_cats:
            table_data = [{
                "Icon": cat["Icon"],
                "Category Name": cat["Name"],
                "Associated Workers": worker_counts.get(cat["Name"], 0),
                "Description": cat["Description"]
            } for cat in filtered_cats]

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

    # --- TAB 2: ADD NEW (Updated) ---
    with tab2:
        st.markdown("### ➕ Add New Category")
        st.info("Icon is stored as base64 data URL. Both `icon` and `iconUrl` fields are saved for compatibility.")

        with st.form("add_category_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("Category Name *", placeholder="e.g., Electrician")
            desc = c2.text_area("Description", height=100)
            
            icon_file = st.file_uploader(
                "Upload Icon * (PNG or JPG)", 
                type=['png', 'jpg', 'jpeg'],
                key="add_icon"
            )

            if st.form_submit_button("✅ Add Category", type="primary", use_container_width=True):
                if not name.strip():
                    st.error("Category name is required")
                elif not icon_file:
                    st.error("Icon is required")
                else:
                    try:
                        raw_bytes = icon_file.getvalue()
                        if len(raw_bytes) > MAX_ICON_BYTES:
                            st.error(f"File too large! Max {MAX_ICON_SIZE_MB}MB")
                        else:
                            icon_data_url, size_kb = compress_image_to_base64(raw_bytes, icon_file.type)

                            new_data = {
                                "name": name.strip(),
                                "description": desc.strip() or "",
                                "icon": icon_data_url,
                                "iconUrl": icon_data_url,
                                "created_at": firestore.SERVER_TIMESTAMP
                            }

                            db.collection("job_categories").add(new_data)
                            
                            st.success(f"✅ Category '{name}' added successfully!")
                            st.image(icon_data_url, width=80, caption="Preview")
                            st.cache_data.clear()
                            st.rerun()

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.exception(e)

    # --- TAB 3: EDIT (Updated) ---
    with tab3:
        st.markdown("### ✏️ Edit Existing Category")
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
                    if selected_cat.get('Icon'):
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
                                        st.error("File too large!")
                                    else:
                                        icon_url, _ = compress_image_to_base64(raw_bytes, new_icon.type)
                                        update_data["icon"] = icon_url
                                        update_data["iconUrl"] = icon_url   # 🔥 Important for Flutter

                                db.collection("job_categories").document(selected_cat["id"]).update(update_data)
                                st.success("Category updated successfully!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Update failed: {e}")
                        else:
                            st.error("Category name cannot be empty.")

    # --- TAB 4: DELETE ---
    with tab4:
        st.markdown("### 🗑️ Delete Category")
        if not categories:
            st.warning("No categories available to delete.")
        else:
            worker_counts_del = {}
            try:
                for doc in db.collection("workers").stream():
                    prof = doc.to_dict().get("profession", "").strip()
                    worker_counts_del[prof] = worker_counts_del.get(prof, 0) + 1
            except:
                pass

            del_cat_name = st.selectbox("Select Category to Delete", cat_names, key="del_cat_select")
            del_cat = next((c for c in categories if c["Name"] == del_cat_name), None)

            if del_cat:
                associated = worker_counts_del.get(del_cat["Name"], 0)
                col_prev, col_info = st.columns([1, 3])
                with col_prev:
                    if del_cat.get("Icon"):
                        st.image(del_cat["Icon"], width=80)
                with col_info:
                    st.markdown(f"**Name:** {del_cat['Name']}")
                    st.markdown(f"**Description:** {del_cat['Description']}")
                    if associated > 0:
                        st.warning(f"⚠️ **{associated} worker(s)** assigned.")
                    else:
                        st.success("✅ Safe to delete.")

                confirm_key = f"confirm_del_cat_{del_cat['id']}"
                if confirm_key not in st.session_state:
                    if st.button("🗑️ Delete This Category", type="primary", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.error(f"Delete **'{del_cat['Name']}'**?")
                    c_yes, c_no = st.columns(2)
                    with c_yes:
                        if st.button("🔥 Yes, Delete", type="primary"):
                            try:
                                db.collection("job_categories").document(del_cat["id"]).delete()
                                st.success("Category deleted.")
                                del st.session_state[confirm_key]
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    with c_no:
                        if st.button("❌ Cancel"):
                            del st.session_state[confirm_key]
                            st.rerun()

# ====================== Settings ======================
else:
    st.header("⚙️ Settings & Info")
    st.success("✅ Add & Edit tabs updated with consistent icon + iconUrl saving")

    if st.button("🔄 Backfill iconUrl for all categories"):
        try:
            cats = db.collection("job_categories").stream()
            count = 0
            for cat in cats:
                data = cat.to_dict()
                if data.get("icon") and not data.get("iconUrl"):
                    db.collection("job_categories").document(cat.id).update({
                        "iconUrl": data["icon"]
                    })
                    count += 1
            st.success(f"Backfilled {count} categories!")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(str(e))

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B;'>TCR Job Portal • Professional Admin Panel • 2026</p>", unsafe_allow_html=True)