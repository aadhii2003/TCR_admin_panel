import streamlit as st
from datetime import datetime

# ====================== Page Config ======================
st.set_page_config(
    page_title="Privacy Policy - TCR Job Portal",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ====================== Custom CSS ======================
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
        padding: 2rem 0 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 3rem;
    }
    .section-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #1E40AF;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 3px solid #3B82F6;
        padding-bottom: 0.5rem;
    }
    .content-box {
        background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #3B82F6;
        margin-bottom: 1.5rem;
    }
    .highlight {
        background-color: #FEF3C7;
        padding: 0.2rem 0.5rem;
        border-radius: 4px;
        font-weight: 600;
    }
    .footer {
        text-align: center;
        color: #64748B;
        margin-top: 4rem;
        padding: 2rem 0;
        border-top: 2px solid #E2E8F0;
    }
    ul {
        line-height: 1.8;
    }
    p {
        line-height: 1.8;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# ====================== Header ======================
st.markdown('<h1 class="main-header">🔒 Privacy Policy</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">TCR Job Portal - Your Privacy Matters to Us</p>', unsafe_allow_html=True)

# ====================== Last Updated ======================
current_date = datetime.now().strftime("%B %d, %Y")
st.markdown(f'<div class="content-box"><strong>Last Updated:</strong> {current_date}</div>', unsafe_allow_html=True)

# ====================== Introduction ======================
st.markdown('<h2 class="section-header">📋 Introduction</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>Welcome to <span class="highlight">TCR Job Portal</span>. We are committed to protecting your personal information and your right to privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our mobile application and services.</p>

<p>By using TCR Job Portal, you agree to the collection and use of information in accordance with this policy. If you do not agree with our policies and practices, please do not use our services.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Information We Collect ======================
st.markdown('<h2 class="section-header">📊 Information We Collect</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<h3>Personal Information</h3>
<p>When you register and use our services, we may collect the following personal information:</p>
<ul>
    <li><strong>Account Information:</strong> Name, email address, phone number, password</li>
    <li><strong>Profile Information:</strong> Profile photo, profession/job category, experience years, hourly rate</li>
    <li><strong>Contact Information:</strong> Address, WhatsApp number, mobile number</li>
    <li><strong>Professional Details:</strong> Skills, languages, work history, ratings, and reviews</li>
    <li><strong>Identity Information:</strong> Gender and other demographic information</li>
</ul>

<h3>Automatically Collected Information</h3>
<ul>
    <li><strong>Usage Data:</strong> Login timestamps, app interactions, features used</li>
    <li><strong>Device Information:</strong> Device type, operating system, unique device identifiers</li>
    <li><strong>Location Data:</strong> Approximate location based on IP address (if permitted)</li>
</ul>
</div>
""", unsafe_allow_html=True)

# ====================== How We Use Your Information ======================
st.markdown('<h2 class="section-header">🎯 How We Use Your Information</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>We use the collected information for the following purposes:</p>
<ul>
    <li><strong>Account Management:</strong> Create and manage your user account</li>
    <li><strong>Service Delivery:</strong> Connect workers with job opportunities and users with service providers</li>
    <li><strong>Communication:</strong> Send notifications, updates, and important service announcements</li>
    <li><strong>Improvement:</strong> Analyze usage patterns to improve our app and services</li>
    <li><strong>Security:</strong> Detect and prevent fraud, abuse, and security incidents</li>
    <li><strong>Compliance:</strong> Comply with legal obligations and enforce our terms of service</li>
    <li><strong>Personalization:</strong> Customize your experience based on your preferences and activity</li>
</ul>
</div>
""", unsafe_allow_html=True)

# ====================== Information Sharing ======================
st.markdown('<h2 class="section-header">🤝 Information Sharing and Disclosure</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>We may share your information in the following circumstances:</p>
<ul>
    <li><strong>With Other Users:</strong> Your profile information (name, photo, profession, ratings) is visible to other users to facilitate job matching</li>
    <li><strong>Service Providers:</strong> Third-party vendors who help us operate our services (e.g., Firebase, cloud hosting)</li>
    <li><strong>Legal Requirements:</strong> When required by law, court order, or government regulations</li>
    <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
    <li><strong>With Your Consent:</strong> When you explicitly authorize us to share your information</li>
</ul>

<p><strong>We do NOT sell your personal information to third parties.</strong></p>
</div>
""", unsafe_allow_html=True)

# ====================== Data Security ======================
st.markdown('<h2 class="section-header">🔐 Data Security</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>We implement industry-standard security measures to protect your personal information:</p>
<ul>
    <li><strong>Encryption:</strong> Data transmission is encrypted using SSL/TLS protocols</li>
    <li><strong>Firebase Authentication:</strong> Secure user authentication and authorization</li>
    <li><strong>Access Controls:</strong> Limited access to personal data on a need-to-know basis</li>
    <li><strong>Regular Monitoring:</strong> Continuous monitoring for security vulnerabilities</li>
</ul>

<p>However, no method of transmission over the internet is 100% secure. While we strive to protect your information, we cannot guarantee absolute security.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Your Rights ======================
st.markdown('<h2 class="section-header">⚖️ Your Privacy Rights</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>You have the following rights regarding your personal information:</p>
<ul>
    <li><strong>Access:</strong> Request a copy of the personal information we hold about you</li>
    <li><strong>Correction:</strong> Update or correct inaccurate information through your profile settings</li>
    <li><strong>Deletion:</strong> Request deletion of your account and associated data</li>
    <li><strong>Objection:</strong> Object to certain processing of your personal information</li>
    <li><strong>Data Portability:</strong> Request a copy of your data in a structured, machine-readable format</li>
    <li><strong>Withdraw Consent:</strong> Withdraw consent for data processing where consent was the legal basis</li>
</ul>

<p>To exercise these rights, please contact us at <strong>support@tcrjobportal.com</strong></p>
</div>
""", unsafe_allow_html=True)

# ====================== Data Retention ======================
st.markdown('<h2 class="section-header">📅 Data Retention</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>We retain your personal information for as long as necessary to:</p>
<ul>
    <li>Provide our services to you</li>
    <li>Comply with legal obligations</li>
    <li>Resolve disputes and enforce our agreements</li>
</ul>

<p>When you delete your account, we will delete or anonymize your personal information within 30 days, except where we are required to retain it for legal purposes.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Third-Party Services ======================
st.markdown('<h2 class="section-header">🔗 Third-Party Services</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>Our app uses the following third-party services:</p>
<ul>
    <li><strong>Firebase (Google):</strong> Authentication, database, and cloud storage</li>
    <li><strong>Cloud Hosting Services:</strong> For app deployment and data storage</li>
</ul>

<p>These third parties have their own privacy policies. We encourage you to review them:</p>
<ul>
    <li>Google Firebase Privacy Policy: <a href="https://firebase.google.com/support/privacy" target="_blank">https://firebase.google.com/support/privacy</a></li>
</ul>
</div>
""", unsafe_allow_html=True)

# ====================== Children's Privacy ======================
st.markdown('<h2 class="section-header">👶 Children\'s Privacy</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>Our services are not intended for individuals under the age of 18. We do not knowingly collect personal information from children. If you believe we have collected information from a child, please contact us immediately, and we will take steps to delete such information.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Changes to Privacy Policy ======================
st.markdown('<h2 class="section-header">📝 Changes to This Privacy Policy</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>We may update this Privacy Policy from time to time. We will notify you of any changes by:</p>
<ul>
    <li>Posting the new Privacy Policy on this page</li>
    <li>Updating the "Last Updated" date at the top of this policy</li>
    <li>Sending you an email notification (for significant changes)</li>
</ul>

<p>We encourage you to review this Privacy Policy periodically for any changes.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Contact Us ======================
st.markdown('<h2 class="section-header">📧 Contact Us</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>If you have any questions, concerns, or requests regarding this Privacy Policy or our data practices, please contact us:</p>

<p><strong>TCR Job Portal</strong><br>
Email: <a href="mailto:support@tcrjobportal.com">support@tcrjobportal.com</a><br>
Phone: +91 XXXXXXXXXX<br>
Address: [Your Business Address]</p>

<p>We will respond to your inquiry within 7 business days.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Consent ======================
st.markdown('<h2 class="section-header">✅ Your Consent</h2>', unsafe_allow_html=True)
st.markdown("""
<div class="content-box">
<p>By using TCR Job Portal, you acknowledge that you have read and understood this Privacy Policy and agree to its terms and conditions.</p>
</div>
""", unsafe_allow_html=True)

# ====================== Footer ======================
st.markdown("""
<div class="footer">
    <p><strong>© 2026 TCR Job Portal</strong></p>
    <p>Professional Job Matching Platform • Connecting Workers with Opportunities</p>
    <p style="margin-top: 1rem; font-size: 0.9rem;">
        This privacy policy is effective as of January 2026 and will remain in effect except with respect to any changes in its provisions in the future.
    </p>
</div>
""", unsafe_allow_html=True)
