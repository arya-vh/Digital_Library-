import streamlit as st
import sqlite3
import pandas as pd
import ollama
from datetime import datetime
import threading

# Thread-local database connection
thread_local = threading.local()

def get_db_connection():
    """Get SQLite connection for current thread"""
    if not hasattr(thread_local, 'conn'):
        thread_local.conn = sqlite3.connect('library.db', check_same_thread=False)
    return thread_local.conn

def init_db():
    """Initialize database schema"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, author TEXT, isbn TEXT,
            category TEXT, status TEXT DEFAULT 'available',
            added_date TEXT
        )
    ''')
    conn.commit()

# Ollama AI
@st.cache_data(ttl=300)
def ai_recommendation(query):
    try:
        response = ollama.chat(model='llama3.2', messages=[
            {'role': 'system', 'content': 'You are a helpful library assistant. Recommend books based on user preferences.'},
            {'role': 'user', 'content': query}
        ])
        return response['message']['content']
    except:
        return "AI recommendation: Try 'To Kill a Mockingbird' for classics!"

# Initialize app
st.set_page_config(page_title="AI Library", layout="wide")
init_db()

st.title("🤖 AI-Powered Library Management")

# Sidebar admin
st.sidebar.title("👨‍💼 Admin Panel")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 Books", "➕ Add Book", "🔍 Search", "🤖 AI Assistant", "📊 Dashboard"])

# Tab 1: View Books
with tab1:
    conn = get_db_connection()
    books = pd.read_sql("SELECT * FROM books ORDER BY added_date DESC", conn)
    st.dataframe(books, use_container_width=True)

# Tab 2: Add Book (CRUD CREATE)
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Title")
        author = st.text_input("Author")
    with col2:
        isbn = st.text_input("ISBN")
        category = st.selectbox("Category", ["Fiction", "Non-Fiction", "Sci-Fi", "Biography", "Mystery"])
    
    if st.button("➕ Add Book", type="primary"):
        conn = get_db_connection()
        conn.execute("INSERT INTO books (title, author, isbn, category, added_date) VALUES (?, ?, ?, ?, ?)",
                    (title, author, isbn, category, datetime.now().isoformat()))
        conn.commit()
        st.success("✅ Book added!")
        st.rerun()

# Tab 3: Search & Update/Delete
with tab3:
    search = st.text_input("🔍 Search books by title/author...")
    if search:
        conn = get_db_connection()
        query = f"%{search}%"
        results = pd.read_sql("SELECT * FROM books WHERE title LIKE ? OR author LIKE ?", conn, params=(query, query))
        st.dataframe(results)
        
        if not results.empty:
            book_id = st.selectbox("Select book to manage:", results['id'])
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✅ Mark Available", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("UPDATE books SET status='available' WHERE id=?", (book_id,))
                    conn.commit()
                    st.success("Updated!")
                    st.rerun()
            with col2:
                if st.button("❌ Mark Issued", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("UPDATE books SET status='issued' WHERE id=?", (book_id,))
                    conn.commit()
                    st.success("Updated!")
                    st.rerun()
            with col3:
                if st.button("🗑️ Delete", use_container_width=True):
                    conn = get_db_connection()
                    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
                    conn.commit()
                    st.success("Deleted!")
                    st.rerun()

# Tab 4: AI Assistant
with tab4:
    st.subheader("💬 Ask Library Assistant")
    query = st.text_area("What book should I read next?", height=100, placeholder="I like sci-fi...")
    if st.button("🤖 Get AI Recommendation", type="primary"):
        with st.spinner("AI thinking..."):
            ai_response = ai_recommendation(query)
            st.markdown(f"**🎯 AI Recommendation:**\n\n{ai_response}")

# Tab 5: Dashboard
with tab5:
    conn = get_db_connection()
    col1, col2, col3, col4 = st.columns(4)
    
    total = pd.read_sql("SELECT COUNT(*) as count FROM books", conn).iloc[0]['count']
    available = pd.read_sql("SELECT COUNT(*) as count FROM books WHERE status='available'", conn).iloc[0]['count']
    issued = pd.read_sql("SELECT COUNT(*) as count FROM books WHERE status='issued'", conn).iloc[0]['count']
    
    col1.metric("📚 Total Books", total)
    col2.metric("✅ Available", available)
    col3.metric("📖 Issued", issued)
    
    col4.metric("🚀 Fill Rate", f"{(available/total)*100:.1f}%")
    
    st.subheader("Recently Issued")
    issued_books = pd.read_sql("SELECT * FROM books WHERE status='issued' ORDER BY added_date DESC LIMIT 5", conn)
    st.dataframe(issued_books)

# Footer
st.markdown("---")
st.markdown("**Made with ❤️ using Streamlit + Ollama** | No login required!")
