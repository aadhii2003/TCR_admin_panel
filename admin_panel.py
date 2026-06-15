import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
import pandas as pd
import datetime
import io
import re
import os
from PIL import Image
import uuid

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
    st.markdown('<h1 class="main-header">🔧 TCR Job Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Professional Admin Dashboard • Manage Workers, Categories & Users</p>', unsafe_allow_html=True)
with col_header2:
    current_time = datetime.datetime.now().strftime("%B %d, %Y • %I:%M %p")
    st.markdown(f'<div style="background: #F1F5F9; padding: 1rem; border-radius: 8px; margin-top: 1rem; text-align: right;"><small style="color: #64748B;">{current_time}</small></div>', unsafe_allow_html=True)
st.markdown("---")

# ====================== Firebase Init ======================
if not firebase_admin._apps:
    try:
        if "firebase" in st.secrets:
            firebase_config = dict(st.secrets["firebase"])
            cred = credentials.Certificate(firebase_config)
            firebase_admin.initialize_app(cred, {'storageBucket': firebase_config.get('storageBucket')})
        elif os.path.exists("tcr-serviceAccountKey.json"):
            cred = credentials.Certificate("tcr-serviceAccountKey.json")
            firebase_admin.initialize_app(cred, {'storageBucket': 'your-project-id.appspot.com'})  # Change if needed
        else:
            st.error("🔴 Firebase credentials not found!")
            st.stop()
    except Exception as e:
        st.error(f"🔴 Firebase initialization failed: {e}")
        st.stop()

db = firestore.client()
bucket = storage.bucket()

# ====================== Helper Functions ======================
MAX_ICON_SIZE_MB = 5
MAX_ICON_BYTES = MAX_ICON_SIZE_MB * 1024 * 1024
ICON_MAX_DIMENSION = 256

def upload_icon_to_storage(file_bytes: bytes, filename: str) -> str:
    """Upload image to Firebase Storage and return public URL"""
    ext = filename.split('.')[-1].lower()
    unique_filename = f"job_categories_icons/{uuid.uuid4()}.{ext}"
    
    blob = bucket.blob(unique_filename)
    blob.upload_from_string(file_bytes, content_type=f"image/{ext}")
    blob.make_public()
    return blob.public_url

def compress_image(file_bytes: bytes, mime_type: str) -> bytes:
    """Compress image before upload"""
    img = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    img.thumbnail((ICON_MAX_DIMENSION, ICON_MAX_DIMENSION), Image.LANCZOS)

    if mime_type in ("image/jpeg", "image/jpg"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        img = background

    buf = io.BytesIO()
    fmt = "PNG" if mime_type == "image/png" else "JPEG"
    if fmt == "PNG":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=75, optimize=True)
    return buf.getvalue()

def clean_value(val):
    return str(val).strip("<> ") if val is not None and pd.notna(val) else "N/A"

def format_date(ts_ms):
    if ts_ms is None: return "N/A"
    try:
        dt = datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc)
        return dt.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime("%b %d, %Y")
    except:
        return "Invalid"

DEFAULT_PHOTO = "https://firebasestorage.googleapis.com/v0/b/placeholder-images.appspot.com/o/default-avatar.png?alt=media"

# ====================== Load Categories ======================
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
    page = st.radio("Select Section", ["📊 Dashboard", "👥 Users/Employees", "🛠️ Job Categories", "⚙️ Settings"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown('<p class="sidebar-title">📈 Quick Stats</p>', unsafe_allow_html=True)
    try:
        total_users = len(list(auth.list_users().iterate_all()))
        active_users = sum(1 for u in auth.list_users().iterate_all() if u.user_metadata.last_sign_in_timestamp)
        st.metric("Users", total_users)
        st.metric("Active", active_users)
        st.metric("Categories", len(get_job_categories_with_details()))
    except:
        st.caption("Stats unavailable")
    st.markdown("---")
    st.markdown('<p class="sidebar-footer">© 2026 TCR Job Portal</p>', unsafe_allow_html=True)

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

        if filtered_cats:
            table_data = [{"Icon": cat["Icon"], "Category Name": cat["Name"], "Description": cat["Description"]} for cat in filtered_cats]
            st.dataframe(pd.DataFrame(table_data), column_config={"Icon": st.column_config.ImageColumn("Icon", width="small")}, use_container_width=True, hide_index=True)

    # --- TAB 2: ADD NEW (Storage Upload) ---
    with tab2:
        st.markdown("### Add New Category")
        st.info(f"Icon upload limit: **{MAX_ICON_SIZE_MB}MB**. Will be stored in Firebase Storage.")

        with st.form("add_category_form", clear_on_submit=True):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("Category Name *", placeholder="e.g., Plumber")
            desc = c2.text_area("Description", height=100)

            icon_file = st.file_uploader("Upload Icon * (PNG or JPG)", type=['png', 'jpg', 'jpeg'], key="add_icon_uploader")

            if st.form_submit_button(" Add Category", type="primary", use_container_width=True):
                if not name.strip():
                    st.error("Category name is required")
                elif not icon_file:
                    st.error("Icon image is required")
                else:
                    raw_bytes = icon_file.getvalue()
                    if len(raw_bytes) > MAX_ICON_BYTES:
                        st.error(f"File too large! Max {MAX_ICON_SIZE_MB}MB")
                    else:
                        try:
                            compressed_bytes = compress_image(raw_bytes, icon_file.type)
                            icon_url = upload_icon_to_storage(compressed_bytes, icon_file.name)

                            new_doc = {
                                "name": name.strip(),
                                "description": desc.strip() or "",
                                "icon": icon_url,
                                "iconUrl": icon_url,
                                "created_at": firestore.SERVER_TIMESTAMP
                            }

                            db.collection("job_categories").add(new_doc)
                            st.success(f"✅ Category '{name}' added successfully!")
                            st.cache_data.clear()
                            st.balloons()
                            st.image(icon_url, width=80)

                        except Exception as e:
                            st.error(f"Failed to save category: {str(e)}")
                            st.exception(e)

    # --- TAB 3: EDIT ---
    with tab3:
        st.markdown("### Edit Existing Category")
        if categories:
            selected_cat_name = st.selectbox("Select Category to Edit", cat_names, key="edit_cat_select")
            selected_cat = next((c for c in categories if c["Name"] == selected_cat_name), None)

            if selected_cat:
                with st.form("edit_category_form"):
                    new_name = st.text_input("Category Name", value=selected_cat['Name'])
                    new_desc = st.text_area("Description", value=selected_cat['Description'])
                    if selected_cat['Icon']:
                        st.image(selected_cat['Icon'], width=60)
                    new_icon = st.file_uploader("Upload New Icon (Optional)", type=['png', 'jpg', 'jpeg'], key="edit_cat_icon")

                    if st.form_submit_button("Update Category", type="primary"):
                        if new_name:
                            update_data = {"name": new_name.strip(), "description": new_desc.strip()}
                            if new_icon:
                                compressed = compress_image(new_icon.getvalue(), new_icon.type)
                                icon_url = upload_icon_to_storage(compressed, new_icon.name)
                                update_data["icon"] = icon_url
                                update_data["iconUrl"] = icon_url

                            db.collection("job_categories").document(selected_cat["id"]).update(update_data)
                            st.success("Category updated!")
                            st.cache_data.clear()
                            st.rerun()

    # --- TAB 4: DELETE ---
    with tab4:
        st.markdown("### Delete Category")
        if categories:
            del_cat_name = st.selectbox("Select Category to Delete", cat_names, key="del_cat_select")
            del_cat = next((c for c in categories if c["Name"] == del_cat_name), None)
            if del_cat:
                if st.button("Delete Category", type="primary"):
                    db.collection("job_categories").document(del_cat["id"]).delete()
                    st.success("Category deleted!")
                    st.cache_data.clear()
                    st.rerun()

# ====================== Other Pages (Dashboard, Users, Settings) ======================
else:
    if page == "📊 Dashboard":
        st.header("📊 Dashboard Overview")
        st.info("Dashboard content here...")
    elif page == "👥 Users/Employees":
        st.header("👥 Users/Employees")
        st.info("Users management section...")
    else:
        st.header("⚙️ Settings")
        st.success("✅ Icons are now uploaded to Firebase Storage and saved as URLs.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #64748B;'>TCR Job Portal • Professional Admin Panel • 2026</p>", unsafe_allow_html=True)